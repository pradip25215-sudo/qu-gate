"""QU-Gate user interface. Run:  streamlit run app.py"""
import asyncio, importlib, json, os, sys, time, uuid
from pathlib import Path
import streamlit as st
from langgraph.types import Command

try:                                    # Streamlit Cloud secrets -> environment variables
    for key, value in st.secrets.items():
        os.environ[key] = str(value)
except Exception:
    pass                                # no secrets file on a local run: the .env file is used instead
import audit, graph, llm, rules

HERE = Path(__file__).parent
# If .env or a code file changed while the app was running, load the new version now (no restart needed).
_watched = [HERE / n for n in (".env", "rules.py", "audit.py", "llm.py", "mcp_server.py", "graph.py")]
_stamp = tuple(p.stat().st_mtime if p.exists() else 0 for p in _watched)
_last = getattr(sys, "_qugate_stamp", None)
if (_last is not None and _last != _stamp) or not hasattr(llm, "log_error"):
    for _module in (rules, audit, llm, graph):
        importlib.reload(_module)
sys._qugate_stamp = _stamp
DOC_TYPES = rules.DOC_TYPES
ss = st.session_state
ss.setdefault("doc_text", "")
ss.setdefault("doc_type", "MBR")


def load_cases() -> dict:
    path = HERE / "eval" / "cases.jsonl"
    if not path.exists():
        return {}
    return {c["id"]: c for c in map(json.loads, filter(None, path.read_text().splitlines()))}


CASES = load_cases()


def use_sample():
    case = CASES.get(ss.get("sample_id"))
    if case:
        ss.doc_text = (HERE / case["file"]).read_text()
        ss.doc_type = case["doc_type"]
        ss.package = None


st.set_page_config(page_title="QU-Gate", layout="wide")
st.title("QU-Gate")
st.caption("Review gate for GMP documents. Decision support only: a named human approves or rejects. "
           "Use synthetic documents only.")
if llm.IS_DEMO:
    st.warning("DEMO MODE: no API key found, so no real model is called. The reviewer step is scripted and makes "
               "two deliberate mistakes so you can see the verifier block them. Add a key to the .env file "
               "for real reviews.")
else:
    st.caption(f"Model: {llm.MODEL}" + (f" (fallback: {llm.FALLBACK})" if llm.FALLBACK else ""))

if CASES:
    left, right = st.columns([3, 1])
    left.selectbox("Sample documents (synthetic)", list(CASES), key="sample_id",
                   index=list(CASES).index("mbr-07") if "mbr-07" in CASES else 0,
                   format_func=lambda i: f"{i}  ({CASES[i]['note']})")
    right.write("")
    right.button("Load sample", on_click=use_sample)

st.selectbox("Document type", list(DOC_TYPES), key="doc_type", format_func=lambda k: f"{k}: {DOC_TYPES[k]}")
st.text_area("Paste the document", height=240, key="doc_text")

if st.button("Run review", type="primary") and ss.doc_text.strip():
    ss.thread = str(uuid.uuid4())
    ss.package = None
    with st.status("Agent working...", expanded=True) as status:
        def show(node, data):
            st.write(f"**{node}**")
            st.json(data or {}, expanded=False)
        failure = None
        try:
            result = asyncio.run(graph.run({"doc_type": ss.doc_type, "text": ss.doc_text}, ss.thread, show))
            ss.package = result["pending"]
            status.update(label="Stopped. Waiting for the Quality Unit.", state="complete")
        except Exception as exc:        # noqa: BLE001
            failure = llm.log_error(exc)
            status.update(label="The review failed.", state="error")
    if failure:
        st.error(failure)
        if "503" in failure or "UNAVAILABLE" in failure or "429" in failure:
            st.info("The model provider is busy or rate-limited right now. This is temporary. "
                    "Wait one minute and press Run review again.")
        else:
            st.info("Check the API key and the QUGATE_MODEL name in the .env file. Full details are saved in "
                    "logs/errors.log. On Windows, double-click CHECK.bat to test the key and pick a working model.")

if ss.get("package"):
    by_rule = [f for f in ss.package["findings"] if f["source"] == "rule"]
    by_ai = [f for f in ss.package["findings"] if f["source"] != "rule"]

    def show(finding):
        with st.expander(f"21 CFR {finding['cfr_section']} ({finding['cfr_title']}): {finding['issue']}"):
            st.write("Evidence in document:", finding["evidence_quote"])
            for p in finding["precedents"]:
                st.markdown(f"> {p['excerpt']}\n\n{p['firm']}, {p['date']} - [FDA warning letter]({p['url']})")

    st.subheader(f"Rule checker findings ({len(by_rule)})")
    st.caption("Fixed checklist, no AI. Each one is a required element that was not found in the document.")
    if not by_rule:
        st.write("None.")
    for f in by_rule:
        show(f)
    st.subheader(f"AI reviewer suggestions ({len(by_ai)})")
    st.caption("A second reader. The verifier confirmed that each cited section is loaded and that any quote is really "
               "in the document. It did not check that the suggestion is correct. A person must judge each one.")
    if not by_ai:
        st.write("None.")
    for f in by_ai:
        show(f)
    st.subheader(f"Blocked by the verifier ({len(ss.package['rejected_by_verifier'])})")
    if ss.package["rejected_by_verifier"]:
        st.table([{"cfr": f["cfr_section"], "issue": f["issue"], "why": f["why"]}
                  for f in ss.package["rejected_by_verifier"]])
    with st.form("qu_gate"):
        st.write("**Quality Unit decision.** The agent cannot approve or reject. Only a named person can.")
        reviewer = st.text_input("Reviewer name (Quality Unit)")
        decision = st.radio("Decision", ["reject", "approve"])
        reason = st.text_area("Reason for decision")
        if st.form_submit_button("Sign and record"):
            if reviewer.strip() and reason.strip():
                asyncio.run(graph.run(Command(resume={"decision": decision, "reviewer": reviewer.strip(),
                                                      "reason": reason.strip()}), ss.thread))
                ss.package = None
                ss.signed = f"Decision '{decision}' by {reviewer.strip()} recorded in the audit log."
                st.rerun()
            else:
                st.error("Name and reason are required.")

if ss.get("signed"):
    st.success(ss.pop("signed"))

with st.sidebar:
    st.subheader("Audit trail")
    rows = audit.records()
    if rows:
        ok, bad_line = audit.verify()
        if ok:
            st.success(f"Hash chain intact ({len(rows)} records)")
        else:
            st.error(f"Tampering detected at line {bad_line}")
        st.dataframe([{"time": r.get("ts", ""), "event": r.get("event", ""), "actor": r.get("actor", "")}
                      for r in rows], hide_index=True)
        st.download_button("Download audit.jsonl", audit.LOG.read_text(), "audit.jsonl")
        if st.button("Tamper test: edit one old record"):
            lines = audit.LOG.read_text().splitlines()
            lines[0] = lines[0].replace('"actor": "system"', '"actor": "someone"', 1)
            audit.LOG.write_text("\n".join(lines) + "\n")
            st.rerun()
        if st.button("Archive this log and start a new one"):
            audit.LOG.rename(audit.LOG.with_name(f"audit-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"))
            st.rerun()
    else:
        st.write("No records yet. Run a review.")
