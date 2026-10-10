"""End-to-end tests of the graph, the MCP tools, the human gate and the app.

The LLM is replaced by a scripted function, so no API key and no network are needed.
"""
import asyncio
from pathlib import Path

import pytest
from langgraph.types import Command

import audit, graph, llm

ROOT = Path(__file__).resolve().parent.parent
PUROLEA_STYLE = (ROOT / "eval" / "docs" / "mbr-07.txt").read_text()     # no process validation, no QU approval


@pytest.fixture(autouse=True)
def fresh_log(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "LOG", tmp_path / "audit.jsonl")


def scripted(findings):
    return lambda doc_type, text, rule_findings, config=None: findings


def test_verifier_blocks_bad_citations_and_gate_records_the_human(monkeypatch):
    monkeypatch.setattr(llm, "review", scripted([
        {"source": "llm", "cfr_section": "211.186", "issue": "Real finding with a real quote",
         "evidence_quote": "Theoretical yield:  1000\nbottles."},                 # spacing differs: still accepted
        {"source": "llm", "cfr_section": "211.999", "issue": "Made-up section", "evidence_quote": "MISSING"},
        {"source": "llm", "cfr_section": "211.100", "issue": "Invented quote", "evidence_quote": "not in the document"},
    ]))
    r = asyncio.run(graph.run({"doc_type": "MBR", "text": PUROLEA_STYLE}, "t-verify"))
    shown = r["pending"]["findings"]
    blocked = r["pending"]["rejected_by_verifier"]

    assert {(f["source"], f["cfr_section"]) for f in shown} == {("rule", "211.100"), ("rule", "211.22"), ("llm", "211.186")}
    assert {f["why"] for f in blocked} == {"CFR section not in our Part 211 copy", "quote not found in document"}
    by_section = {f["cfr_section"]: f for f in shown}
    assert by_section["211.100"]["precedents"][0]["firm"] == "Purolea Cosmetics Lab"
    assert by_section["211.186"]["precedents"] == []
    assert "decision" not in r["state"]                                            # stopped before any decision

    r = asyncio.run(graph.run(Command(resume={"decision": "reject", "reviewer": "QA Head",
                                              "reason": "no process validation"}), "t-verify"))
    assert r["pending"] is None and r["state"]["decision"]["reviewer"] == "QA Head"
    events = [x["event"] for x in audit.records()]
    assert events == ["doc_received", "rule_check", "llm_review", "verify", "qu_decision"]
    assert audit.records()[-1]["actor"] == "QA Head"
    assert audit.verify() == (True, 0)


def test_batch_record_type_uses_its_own_checklist(monkeypatch):
    monkeypatch.setattr(llm, "review", scripted([]))
    text = (ROOT / "eval" / "docs" / "bpr-07.txt").read_text()                     # QU release review removed
    r = asyncio.run(graph.run({"doc_type": "BPR", "text": text}, "t-bpr"))
    assert [f["cfr_section"] for f in r["pending"]["findings"]] == ["211.192"]


def test_clean_document_still_stops_at_the_gate(monkeypatch):
    monkeypatch.setattr(llm, "review", scripted([]))
    text = (ROOT / "eval" / "docs" / "mbr-00.txt").read_text()
    r = asyncio.run(graph.run({"doc_type": "MBR", "text": text}, "t-clean"))
    assert r["pending"] is not None and r["pending"]["findings"] == []


def test_app_runs_a_review_and_refuses_an_unsigned_decision(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(llm, "review", scripted([
        {"source": "llm", "cfr_section": "211.999", "issue": "Made-up section", "evidence_quote": "MISSING"}]))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception

    at.selectbox(key="sample_id").set_value("mbr-07").run()
    next(b for b in at.button if b.label == "Load sample").click().run()
    assert "MASTER BATCH RECORD" in at.text_area(key="doc_text").value

    next(b for b in at.button if b.label == "Run review").click().run()
    assert not at.exception
    labels = [e.label for e in at.expander]
    assert any("211.100" in label for label in labels) and any("211.22" in label for label in labels)

    submit = lambda: next(b for b in at.button if b.label == "Sign and record")
    submit().click().run()                                                         # no name, no reason
    assert any("required" in e.value for e in at.error)
    assert "qu_decision" not in [x["event"] for x in audit.records()]

    at.text_input[0].set_value("QA Head")                                          # form fields: set, then submit
    next(t for t in at.text_area if t.label == "Reason for decision").set_value("No process validation")
    submit().click().run()
    assert not at.exception
    assert audit.records()[-1]["event"] == "qu_decision" and audit.verify() == (True, 0)

    next(b for b in at.button if b.label.startswith("Tamper test")).click().run()
    assert any("Tampering detected at line 1" in e.value for e in at.sidebar.error)


def test_a_second_sign_off_on_the_same_review_is_ignored(monkeypatch):
    monkeypatch.setattr(llm, "review", scripted([]))
    asyncio.run(graph.run({"doc_type": "MBR", "text": PUROLEA_STYLE}, "t-double"))
    signed = Command(resume={"decision": "reject", "reviewer": "QA Head", "reason": "no process validation"})
    asyncio.run(graph.run(signed, "t-double"))
    again = asyncio.run(graph.run(Command(resume={"decision": "approve", "reviewer": "Someone Else",
                                                  "reason": "second click"}), "t-double"))
    decisions = [r for r in audit.records() if r["event"] == "qu_decision"]
    assert len(decisions) == 1 and decisions[0]["actor"] == "QA Head"
    assert again["pending"] is None and again["state"]["decision"]["decision"] == "reject"
    assert audit.verify() == (True, 0)


def test_two_sign_offs_at_the_same_moment_record_one_decision(monkeypatch):
    """Two requests can arrive together (double click, browser reconnect). Only one may be recorded."""
    import threading
    monkeypatch.setattr(llm, "review", scripted([]))
    asyncio.run(graph.run({"doc_type": "MBR", "text": PUROLEA_STYLE}, "t-race"))
    signed = {"decision": "reject", "reviewer": "QA Head", "reason": "no process validation"}
    go = threading.Barrier(2)

    def sign():
        go.wait()
        asyncio.run(graph.run(Command(resume=dict(signed)), "t-race"))

    workers = [threading.Thread(target=sign) for _ in range(2)]
    [w.start() for w in workers]
    [w.join() for w in workers]
    assert [r["event"] for r in audit.records()].count("qu_decision") == 1
    assert audit.verify() == (True, 0)
