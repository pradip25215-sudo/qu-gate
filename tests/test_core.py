"""Fast tests. No API key and no network needed."""
import json
from pathlib import Path

import audit, llm
from rules import CHECKLIST, rule_check

ROOT = Path(__file__).resolve().parent.parent
CFR = json.loads((ROOT / "data" / "cfr211.json").read_text())
CASES = [json.loads(line) for line in (ROOT / "eval" / "cases.jsonl").read_text().splitlines() if line.strip()]


def test_every_checklist_row_cites_a_section_we_hold():
    for rows in CHECKLIST.values():
        for row in rows:
            assert row["cfr"] in CFR, row


def test_every_precedent_cites_a_section_we_hold_and_has_a_url():
    for p in json.loads((ROOT / "data" / "precedents.json").read_text()):
        assert p["url"].startswith("https://www.fda.gov/")
        assert all(s in CFR for s in p["cfr_sections"])


def test_rules_flag_an_empty_master_record():
    found = rule_check("MBR", "Weigh ethanol. Mix. Fill.")
    assert {f["cfr_section"] for f in found} == {"211.100", "211.22", "211.186"}
    assert len(found) == len(CHECKLIST["MBR"])


def test_clean_templates_pass_and_seeded_defects_are_found():
    for case in CASES:
        if case["kind"] not in ("clean", "seeded"):
            continue
        text = (ROOT / case["file"]).read_text()
        found = {f["cfr_section"] for f in rule_check(case["doc_type"], text)}
        assert found == set(case["gold"]), case["id"]


def test_hard_cases_are_really_hard_for_the_rules():
    hard = [c for c in CASES if c["kind"] == "hard"]
    assert len(hard) >= 4
    wrong = [c["id"] for c in hard
             if {f["cfr_section"] for f in rule_check(c["doc_type"], (ROOT / c["file"]).read_text())} != set(c["gold"])]
    assert len(wrong) == len(hard)          # the rule checker alone gets every hard case wrong


def test_section_numbers_are_normalised():
    assert llm._section_only("21 CFR 211.22(c)") == "211.22"
    assert llm._section_only("211.186(b)(7)") == "211.186"
    assert llm._section_only("nonsense") == "nonsense"


def test_audit_detects_tampering(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "LOG", tmp_path / "audit.jsonl")
    audit.append("doc_received", "system", {"x": 1})
    audit.append("qu_decision", "QA Head", {"decision": "reject"})
    assert audit.verify() == (True, 0)
    audit.LOG.write_text(audit.LOG.read_text().replace("reject", "approve"))
    assert audit.verify() == (False, 2)


def test_audit_detects_a_deleted_line(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "LOG", tmp_path / "audit.jsonl")
    for n in range(3):
        audit.append("step", "system", {"n": n})
    lines = audit.LOG.read_text().splitlines()
    audit.LOG.write_text("\n".join([lines[0], lines[2]]) + "\n")
    assert audit.verify() == (False, 2)


def test_backup_model_is_used_when_the_main_model_fails(monkeypatch):
    """The provider call is replaced by a stand-in, so this checks our wiring, not a real model."""
    import langchain.chat_models as chat_models
    from langchain_core.runnables import RunnableLambda
    tried = []

    class StandIn:
        def __init__(self, name):
            self.name = name

        def with_structured_output(self, schema):
            def answer(prompt):
                tried.append(self.name)
                if self.name == "provider:main":
                    raise RuntimeError("503 UNAVAILABLE high demand")
                return schema(findings=[{"cfr_section": "21 CFR 211.192", "issue": "Yield not investigated",
                                         "evidence_quote": "Actual yield"}])
            return RunnableLambda(answer)

    monkeypatch.setattr(chat_models, "init_chat_model", lambda name, **kw: StandIn(name))
    monkeypatch.setattr(llm, "IS_DEMO", False)
    monkeypatch.setattr(llm, "MODEL", "provider:main")
    monkeypatch.setattr(llm, "FALLBACK", "provider:backup, provider:third")
    out = llm.review("BPR", "Actual yield: 710 bottles", [], config={"callbacks": []})
    assert tried == ["provider:main", "provider:backup"] and llm.LAST_MODEL == "provider:backup"
    assert out == [{"source": "llm", "cfr_section": "211.192", "issue": "Yield not investigated",
                    "evidence_quote": "Actual yield"}]

    monkeypatch.setattr(llm, "FALLBACK", "")
    try:
        llm.review("BPR", "x", [])
        raise AssertionError("expected a failure")
    except RuntimeError as exc:
        assert "All models failed" in str(exc) and "503" in str(exc)


def test_demo_mode_is_used_when_no_key_is_set(monkeypatch):
    for key in ("QUGATE_MODEL", "GOOGLE_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    assert llm._pick_model() == "demo"
    monkeypatch.setenv("GROQ_API_KEY", "x")
    assert llm._pick_model() == "groq:openai/gpt-oss-120b"
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    assert llm._pick_model() == "google_genai:gemini-3.8-flash"
    monkeypatch.setenv("QUGATE_MODEL", "openai:some-model")
    assert llm._pick_model() == "openai:some-model"


def test_a_repeated_write_is_removed_and_the_chain_stays_intact(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "LOG", tmp_path / "audit.jsonl")
    audit.append("doc_received", "system", {"review_id": "r1"})
    real_open = type(audit.LOG).open

    def writes_twice(self, mode="r", *a, **k):          # stand-in for a file system that repeats one append
        f = real_open(self, mode, *a, **k)
        if mode == "a":
            real_write = f.write
            f.write = lambda text: (real_write(text), real_write(text))[0]
        return f

    monkeypatch.setattr(type(audit.LOG), "open", writes_twice)
    audit.append("qu_decision", "QA Head", {"review_id": "r1", "decision": "reject"})
    monkeypatch.setattr(type(audit.LOG), "open", real_open)
    assert [r["event"] for r in audit.records()] == ["doc_received", "qu_decision"]
    assert audit.verify() == (True, 0)


def test_one_decision_per_review(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "LOG", tmp_path / "audit.jsonl")
    assert audit.append("qu_decision", "QA Head", {"review_id": "r1", "decision": "reject"}, once_per_review=True)
    assert audit.append("qu_decision", "QA Head", {"review_id": "r1", "decision": "reject"}, once_per_review=True) == ""
    assert audit.append("qu_decision", "QA Head", {"review_id": "r2", "decision": "approve"}, once_per_review=True)
    assert len(audit.records()) == 2 and audit.verify() == (True, 0)


def test_every_hard_case_with_a_defect_has_an_issue_pattern_that_compiles():
    import re
    hard = [c for c in CASES if c["kind"] == "hard" and c["gold"]]
    assert len(hard) == 4
    for c in hard:
        assert c["issue_pattern"] and re.compile(c["issue_pattern"])


def test_twelve_sections_are_loaded_and_the_partial_one_is_marked():
    assert len(CFR) == 12
    assert [k for k, v in CFR.items() if v.get("partial")] == ["211.165"]
    assert all(v["text"] and v["title"] and v["source"].endswith(k) for k, v in CFR.items())
