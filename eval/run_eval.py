"""Seeded-defect evaluation.

Three systems are scored on the same documents:
  baseline   one LLM call, nothing else
  rules      the deterministic checklist alone
  qugate     rules + LLM reviewer + verifier (what the human sees at the gate)

Run from the repo root:   python -m eval.run_eval            (continues where the last run stopped)
                          python -m eval.run_eval --fresh    (forget earlier progress, start again)
                          python -m eval.run_eval --limit 5  (first 5 cases only)

Each finished case is saved at once to eval/progress.jsonl, so a stopped or failed run loses nothing.
A case whose model calls keep failing (busy model, rate limit) is skipped and retried on the next run.
Results go to eval/results.json and eval/results.md. Everything printed is also saved in logs/eval.log.
"""
import argparse, asyncio, json, logging, re, sys, time, warnings
from pathlib import Path

warnings.filterwarnings("ignore")                       # provider and beta warnings hide the progress lines
logging.disable(logging.WARNING)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import audit, graph, llm                      # noqa: E402
from mcp_server import CFR                    # noqa: E402
from rules import rule_check                  # noqa: E402

PROGRESS = ROOT / "eval" / "progress.jsonl"
LOGFILE = ROOT / "logs" / "eval.log"
WAITS = (15, 30, 60)                                    # seconds to wait before the 2nd, 3rd and 4th try
PAUSE = 0.0 if llm.IS_DEMO else 5.0                     # seconds between the baseline call and the QU-Gate call
SETTING = f"{llm.MODEL} | {len(CFR)} sections"          # what a saved progress row was produced with


def say(text: str = "") -> None:
    text = llm.scrub(text)
    print(text, flush=True)
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    with LOGFILE.open("a") as f:
        f.write(text + "\n")


def prf(pred: set, gold: set) -> tuple[float, float, float]:
    """Precision, recall, F1 for one document. A clean document with no findings scores 1, 1, 1."""
    if not pred and not gold:
        return 1.0, 1.0, 1.0
    tp = len(pred & gold)
    p = tp / len(pred) if pred else 0.0
    r = tp / len(gold) if gold else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def attempt(what: str, fn):
    """Call fn. On failure wait and try again, up to 4 tries. Raises the last error."""
    for n in range(len(WAITS) + 1):
        try:
            return fn()
        except Exception as exc:              # noqa: BLE001  (busy model, rate limit, network)
            reason = llm.scrub(f"{type(exc).__name__}: {exc}")[:300]
            if n == len(WAITS):
                raise
            say(f"   {what} failed: {reason}")
            say(f"   waiting {WAITS[n]}s, then try {n + 2} of {len(WAITS) + 1}")
            time.sleep(WAITS[n])


def run_case(case: dict) -> dict:
    text, gold = (ROOT / case["file"]).read_text(), set(case["gold"])
    squashed = " ".join(text.split())

    base = attempt("baseline call", lambda: llm.review(case["doc_type"], text, []))
    base_model = llm.LAST_MODEL
    base_bad = [f for f in base if f["cfr_section"] not in CFR
                or (f["evidence_quote"] != "MISSING" and " ".join(f["evidence_quote"].split()) not in squashed)]
    rules_only = rule_check(case["doc_type"], text)

    time.sleep(PAUSE)                                    # space out the two model calls (free-tier per-minute limits)
    t0 = time.time()
    out = attempt("QU-Gate review", lambda: asyncio.run(
        graph.run({"doc_type": case["doc_type"], "text": text}, f"eval-{case['id']}-{time.time()}")))
    shown = out["pending"]["findings"] if out["pending"] else []
    blocked = out["pending"]["rejected_by_verifier"] if out["pending"] else []
    pattern = case.get("issue_pattern", "")
    names = lambda findings: any(re.search(pattern, f["issue"], re.I | re.S) for f in findings) if pattern else None
    return {
        "issue_baseline": names(base), "issue_qugate": names(shown), "issue_blocked": names(blocked),
        "id": case["id"], "kind": case.get("kind", ""), "gold": sorted(gold),
        "baseline": prf({f["cfr_section"] for f in base}, gold),
        "rules": prf({f["cfr_section"] for f in rules_only}, gold),
        "qugate": prf({f["cfr_section"] for f in shown}, gold),
        "baseline_findings": len(base), "baseline_bad_citations": len(base_bad),
        "qugate_findings": len(shown), "qugate_blocked": len(blocked),
        "stopped_at_gate": out["pending"] is not None, "seconds": round(time.time() - t0, 1),
        "models": sorted({base_model, llm.LAST_MODEL}),
    }


def main(sleep_s: float = 6.0, limit: int = 0, fresh: bool = False) -> list[dict]:
    audit.LOG = ROOT / "logs" / "eval_audit.jsonl"       # keep evaluation runs out of the main audit log
    cases = [json.loads(line) for line in (ROOT / "eval" / "cases.jsonl").read_text().splitlines() if line.strip()]
    if limit:
        cases = cases[:limit]
    if fresh and PROGRESS.exists():
        PROGRESS.unlink()
    done = {}
    if PROGRESS.exists():
        for line in PROGRESS.read_text().splitlines():
            row = json.loads(line)
            if row.get("setting") == SETTING:            # progress made with another model or rule set is not reused
                done[row["id"]] = row

    say(f"\n=== QU-Gate evaluation, {time.strftime('%Y-%m-%d %H:%M:%S')}, model setting: {llm.MODEL}"
        + (f", backups: {llm.FALLBACK}" if llm.FALLBACK else ""))
    todo = [c for c in cases if c["id"] not in done]
    say(f"{len(cases)} cases: {len(cases) - len(todo)} already done, {len(todo)} to run")
    failed, in_a_row = [], 0
    for n, case in enumerate(todo, start=1):
        say(f"[{n}/{len(todo)}] {case['id']}")
        try:
            row = run_case(case)
        except Exception as exc:              # noqa: BLE001
            failed.append(case["id"])
            say(f"   SKIPPED after 4 tries: {llm.scrub(f'{type(exc).__name__}: {exc}')[:2500]}")
            in_a_row += 1
            if in_a_row >= 2:
                say("   Two cases in a row could not be run. The model provider is refusing requests "
                    "(busy, or the free quota is used up). Stopping now so you do not wait for nothing.")
                failed += [c["id"] for c in todo[n:]]
                break
            continue
        in_a_row = 0
        row["setting"] = SETTING
        done[row["id"]] = row
        with PROGRESS.open("a") as f:
            f.write(json.dumps(row) + "\n")
        say(f"   done in {row['seconds']}s: QU-Gate showed {row['qugate_findings']}, blocked {row['qugate_blocked']}")
        time.sleep(sleep_s)                                   # stay under free-tier rate limits

    rows = [done[c["id"]] for c in cases if c["id"] in done]
    report = summarise(rows, len(cases), failed)
    (ROOT / "eval" / "results.json").write_text(json.dumps(rows, indent=2))
    (ROOT / "eval" / "results.md").write_text(report)
    say("\n" + report)
    if failed:
        say(f"{len(failed)} case(s) could not be run now. Run the evaluation again later: only those cases will run.")
    else:
        say("ALL CASES DONE.")
    return rows


def summarise(rows: list[dict], total: int, failed: list[str]) -> str:
    def mean(values):
        values = list(values)
        return sum(values) / len(values) if values else 0.0

    lines = [f"# QU-Gate evaluation ({len(rows)} of {total} synthetic documents, model setting: {llm.MODEL})", "",
             f"CFR sections loaded: {len(CFR)} ({', '.join(sorted(CFR, key=lambda k: int(k.split('.')[1])))})", ""]
    if llm.IS_DEMO:
        lines += ["**DEMO MODE: no real model was called. The baseline and qugate rows below are not results.**",
                  "Add an API key to .env and run again.", ""]
    if not rows:
        return "\n".join(lines + ["No case finished. The model provider was busy or the key was refused."]) + "\n"
    if len(rows) < total:
        lines += [f"**Incomplete: {total - len(rows)} case(s) not run yet"
                  + (f" ({', '.join(failed)})" if failed else "") + ". Run the evaluation again to finish.**", ""]
    lines += ["| System | Precision | Recall | F1 |", "|---|---|---|---|"]
    for name in ("baseline", "rules", "qugate"):
        p, r, f = (mean(x[name][i] for x in rows) for i in range(3))
        lines.append(f"| {name} | {p:.2f} | {r:.2f} | {f:.2f} |")
    lines.append("")

    for kind in ("seeded", "hard", "injection"):
        sub = [x for x in rows if x["kind"] == kind]
        if sub:
            lines.append(f"- Recall on {kind} cases (n={len(sub)}): baseline {mean(x['baseline'][1] for x in sub):.2f}, "
                         f"rules {mean(x['rules'][1] for x in sub):.2f}, qugate {mean(x['qugate'][1] for x in sub):.2f}")
    issue = [x for x in rows if x.get("issue_qugate") is not None]
    if issue:
        lines.append(f"- Hard defects described in a finding, whatever section it cites (n={len(issue)}, keyword match): "
                     f"baseline {sum(bool(x['issue_baseline']) for x in issue)}, "
                     f"shown by qugate {sum(bool(x['issue_qugate']) for x in issue)}, "
                     f"found by the reviewer but blocked by the verifier {sum(bool(x['issue_blocked']) and not x['issue_qugate'] for x in issue)}")
    clean = [x for x in rows if x["kind"] == "clean"]
    if clean:
        lines.append(f"- False alarms on clean documents (n={len(clean)}): baseline "
                     f"{mean(x['baseline_findings'] for x in clean):.1f} per document, "
                     f"qugate {mean(x['qugate_findings'] for x in clean):.1f} per document")
    total_base = sum(x["baseline_findings"] for x in rows)
    bad = sum(x["baseline_bad_citations"] for x in rows)
    lines.append(f"- Baseline findings with an unverifiable citation or quote: {bad} of {total_base}")
    lines.append(f"- Findings blocked by the QU-Gate verifier: {sum(x['qugate_blocked'] for x in rows)}")
    lines.append(f"- Runs that stopped at the human gate: {sum(x['stopped_at_gate'] for x in rows)} of {len(rows)}")
    lines.append(f"- Mean seconds per QU-Gate review: {mean(x['seconds'] for x in rows):.1f}")
    missed = [x["id"] for x in rows if x["gold"] and x["qugate"][1] < 1.0]
    lines.append(f"- Cases where QU-Gate missed a gold section: {', '.join(missed) if missed else 'none'}")
    alarms = [x["id"] for x in rows if not x["gold"] and x["qugate_findings"]]
    lines.append(f"- Compliant documents where QU-Gate raised a false alarm: {', '.join(alarms) if alarms else 'none'}")
    models = sorted({m for x in rows for m in x.get("models", [])})
    lines.append(f"- Models that answered: {', '.join(models)}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only run the first N cases")
    ap.add_argument("--sleep", type=float, default=12.0, help="seconds to wait between cases")
    ap.add_argument("--fresh", action="store_true", help="forget earlier progress and start again")
    args = ap.parse_args()
    main(sleep_s=0.0 if llm.IS_DEMO else args.sleep, limit=args.limit, fresh=args.fresh)
