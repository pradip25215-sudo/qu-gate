"""QU-Gate graph: intake -> rules -> LLM review -> citation verifier + precedents (MCP) -> human Quality Unit gate.

PROPOSE  (rules, review)   VERIFY  (verify)   SIGN + LOG  (qu_gate, audit)
"""
import asyncio, hashlib, json, os, sys, threading
from pathlib import Path
from typing_extensions import TypedDict
from langchain_core.runnables import RunnableConfig
from langchain.mcp import MCPAdapter
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
import audit, llm
from rules import rule_check

HERE = Path(__file__).parent
MCP_CONFIG = {"mcpServers": {"qu": {"command": sys.executable, "args": [str(HERE / "mcp_server.py")],
                                    "env": {**os.environ, "FASTMCP_LOG_LEVEL": "ERROR"}}}}
CHECKPOINTER = InMemorySaver()          # one shared checkpointer, so a paused run can be resumed
_RUN_LOCK = threading.Lock()            # one graph run at a time in this process (two sign-offs cannot overlap)


class State(TypedDict, total=False):
    doc_type: str
    text: str
    rule_findings: list
    llm_findings: list
    verified: list
    rejected: list
    decision: dict


def _data(tool_result):                 # MCP tool results arrive as a list of content blocks
    return json.loads(tool_result[0]["text"])


def _squash(s: str) -> str:             # compare quotes without caring about line breaks and extra spaces
    return " ".join(s.split())


def build(tools: dict):
    def intake(s: State, config: RunnableConfig):
        audit.append("doc_received", "system",
                     {"review_id": config["configurable"]["thread_id"], "doc_type": s["doc_type"],
                      "sha256": hashlib.sha256(s["text"].encode()).hexdigest()})
        return {}

    def rules_node(s: State):
        found = rule_check(s["doc_type"], s["text"])
        audit.append("rule_check", "system", {"findings": found})
        return {"rule_findings": found}

    def review_node(s: State, config: RunnableConfig):
        found = llm.review(s["doc_type"], s["text"], s["rule_findings"], config=config)
        audit.append("llm_review", "agent", {"findings": found}, model=llm.LAST_MODEL)
        return {"llm_findings": found}

    async def verify_node(s: State):
        verified, rejected = [], []
        doc = _squash(s["text"])
        for f in s["rule_findings"] + s["llm_findings"]:
            cfr = _data(await tools["get_cfr_section"].ainvoke({"section": f["cfr_section"]}))
            quote_ok = f["evidence_quote"] == "MISSING" or _squash(f["evidence_quote"]) in doc
            if not cfr["found"]:
                rejected.append({**f, "why": "CFR section not in our Part 211 copy"})
            elif not quote_ok:
                rejected.append({**f, "why": "quote not found in document"})
            else:
                hits = _data(await tools["search_precedents"].ainvoke({"cfr_section": f["cfr_section"]}))["hits"]
                verified.append({**f, "cfr_title": cfr["title"], "precedents": hits})
        audit.append("verify", "system", {"verified": verified, "rejected": rejected})
        return {"verified": verified, "rejected": rejected}

    def qu_gate(s: State, config: RunnableConfig):
        decision = interrupt({"question": "Quality Unit decision needed", "findings": s["verified"],
                              "rejected_by_verifier": s["rejected"]})
        # who, what, why. The timestamp is added by audit. A review can have only one decision record.
        audit.append("qu_decision", decision["reviewer"],
                     {"review_id": config["configurable"]["thread_id"], **decision}, once_per_review=True)
        return {"decision": decision}

    g = StateGraph(State)
    for name, fn in [("intake", intake), ("rules", rules_node), ("review", review_node),
                     ("verify", verify_node), ("qu_gate", qu_gate)]:
        g.add_node(name, fn)
    g.add_edge(START, "intake"); g.add_edge("intake", "rules"); g.add_edge("rules", "review")
    g.add_edge("review", "verify"); g.add_edge("verify", "qu_gate"); g.add_edge("qu_gate", END)
    return g.compile(checkpointer=CHECKPOINTER)


def _callbacks() -> list:
    """Langfuse tracing, only when the keys are set. A tracing problem must never stop a review."""
    if not (os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")):
        return []
    try:
        from langfuse.langchain import CallbackHandler
        return [CallbackHandler()]
    except Exception as exc:            # noqa: BLE001
        print("Langfuse tracing is off:", exc, file=sys.stderr)
        return []


async def run(payload, thread_id: str, on_step=None):
    """payload = {'doc_type':..., 'text':...} to start, or Command(resume={...}) to continue.
    Returns {'pending': <package waiting for the human, or None>, 'state': <graph state>}."""
    cfg = {"configurable": {"thread_id": thread_id}, "callbacks": _callbacks()}
    pending = None
    with _RUN_LOCK:
        return await _run_locked(payload, cfg, on_step)


async def _run_locked(payload, cfg, on_step):
    pending = None
    async with MCPAdapter(MCP_CONFIG) as adapter:
        tools = {t.name: t for t in await adapter.list_tools()}
        app = build(tools)
        if isinstance(payload, Command) and not app.get_state(cfg).next:
            # Nothing is waiting at the gate (already signed, e.g. a double click). Never record a decision twice.
            return {"pending": None, "state": app.get_state(cfg).values}
        async for update in app.astream(payload, cfg, stream_mode="updates"):
            for node, data in update.items():
                if node == "__interrupt__":
                    pending = data[0].value
                elif on_step:
                    on_step(node, data)
        return {"pending": pending, "state": app.get_state(cfg).values}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python graph.py <document.txt> [MBR|BPR]")
    doc = open(sys.argv[1]).read()
    doc_type = sys.argv[2] if len(sys.argv) > 2 else "MBR"
    show = lambda node, data: print("step:", node)
    print("model:", llm.MODEL)
    r = asyncio.run(run({"doc_type": doc_type, "text": doc}, "cli-1", show))
    print(json.dumps(r["pending"], indent=2))
    human = {"decision": input("approve or reject: "), "reviewer": input("Your name: "), "reason": input("Reason: ")}
    asyncio.run(run(Command(resume=human), "cli-1", show))
    print("Decision saved. Audit chain intact:", audit.verify())
