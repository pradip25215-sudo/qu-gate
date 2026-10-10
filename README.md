# QU-Gate

**A review gate for AI-written GMP documents.** A rule checker and an LLM reviewer propose findings against 21 CFR Part 211, a verifier blocks any finding whose citation or quote it cannot confirm, a named human in the Quality Unit signs, and every step goes into a tamper-evident audit log.

Why this exists: on 2 April 2026 the US FDA sent a warning letter to a firm that used AI agents to write its drug manufacturing documents and did not review them. FDA wrote that AI-generated documents must be reviewed, and cited 21 CFR 211.22(c) and 211.100 ([FDA warning letter 722591](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/purolea-cosmetics-lab-722591-04022026)). QU-Gate is that review step.

> Decision support only. A human reviews every output. This is a prototype, not a validated system. Use synthetic documents only.

## How it works

```text
GMP document (master batch record or batch production record; may be AI-written)
        |
  PROPOSE   1. intake        hash the document, write the first audit record
            2. rule checker  deterministic checklist built from 21 CFR 211 (no LLM)
            3. reviewer      LLM looks for more gaps; must give a CFR section and an exact quote
        |
  VERIFY    4. verifier      does the CFR section exist? is the quote really in the document?
                             If not, the finding is blocked.          MCP tool: get_cfr_section
            5. precedents    attach FDA warning-letter excerpts.      MCP tool: search_precedents
        |
  SIGN+LOG  6. QU gate       the graph stops (LangGraph interrupt). A named human approves or
                             rejects and gives a reason. The agent cannot do this.
            7. audit trail   every step in a hash-chained log. Editing one line breaks the chain.
```

## Quick start (Ubuntu or WSL)

```bash
bash setup.sh        # creates the Python 3.12 environment, installs packages, runs the tests
bash run.sh          # starts the app; open http://localhost:8501
```

On Windows with WSL you can instead double-click `SETUP.bat`, then `RUN.bat`. If Windows shows a `Wsl/Service` error, double-click `RESTART-WSL.bat` and try again.

With no API key the app runs in **demo mode**: the rule checker, verifier, gate and audit log are real, and the LLM reviewer is replaced by a scripted step that makes two deliberate mistakes so you can see the verifier block them.

For real reviews, put a key in `.env`:

| Provider | Setting in `.env` | Where to get the key |
|---|---|---|
| Google Gemini (free tier) | `GOOGLE_API_KEY=...` | https://aistudio.google.com |
| Groq (free tier, backup) | `GROQ_API_KEY=...` | https://console.groq.com/keys |
| OpenAI | `OPENAI_API_KEY=...` and `QUGATE_MODEL=openai:<model id>` | your OpenAI account |

The model is chosen in one place (`llm.py`), so the design is LLM-agnostic.

## Evaluation

```bash
bash eval.sh --limit 5     # quick check
bash eval.sh               # all 27 synthetic documents; writes eval/results.md (continues where it stopped)
```

The test set is built by `eval/make_cases.py`:

- 2 compliant documents (to count false alarms)
- 17 seeded-defect documents (1 to 3 required elements removed; the removed CFR sections are the gold labels)
- 5 hard cases that simple patterns get wrong (blank signature, yield with no limits, low yield with no investigation, out-of-specification result, reworded validation)
- 3 prompt-injection cases (a hidden instruction tells the reviewer to approve)

Three systems are scored: a single LLM call (baseline), the rule checker alone, and the full QU-Gate pipeline.

### Results, run 1 (7 October 2026)

27 synthetic documents, one model for every call (`gemini-3.5-flash-lite`, Google free tier), 5 CFR sections loaded. Full output: `eval/results_run1.md` and `eval/results_run1.json`.

| System | Precision | Recall | F1 |
|---|---|---|---|
| Baseline: one LLM call | 0.19 | 0.37 | 0.24 |
| Rule checker alone | 0.81 | 0.81 | 0.81 |
| QU-Gate: rules + LLM reviewer + verifier | 0.64 | 0.78 | 0.68 |

Scores are per document, at CFR-section level, against the seeded defects only.

What run 1 shows:

- **Seeded defects (17 documents):** the rule checker and QU-Gate found every seeded section in 17 of 17. The single LLM call did so in 8 of 17.
- **Human gate:** 27 of 27 reviews stopped and waited for a named person.
- **Prompt injection (3 documents):** the hidden "approve this" instruction changed nothing. QU-Gate still showed every seeded defect, and the model still reported findings.
- **Verifier:** it blocked 27 of the reviewer's 50 findings. All 27 cited a real Part 211 section that was not among the 5 loaded (211.101, 211.103, 211.105, 211.130, 211.160, 211.165). None cited a made-up section or an invented quote in this run.
- **Speed:** 4.6 seconds per review on average.

What run 1 does not show, and where QU-Gate lost:

- **QU-Gate scored below the rule checker alone (F1 0.68 against 0.81).** The LLM reviewer added findings about other sections. Against seeded-defect labels these count as wrong, even when the observation is reasonable.
- **Hard cases: QU-Gate matched the gold section in 0 of 4, the single LLM call in 1 of 4.** In two of them the reviewer described the defect correctly (low yield with no investigation; out-of-specification result) but cited 211.103 and 211.165, which were not loaded, so the verifier blocked a correct finding. In a third (blank signature) the finding was shown, under 211.186 instead of the gold 211.22.
- **So the narrow section list made the verifier over-block.** A scope guard that hides correct findings is a real cost, not a detail.
- **One false alarm on a compliant document** from the rule checker (validation described in other words), and one from the LLM reviewer.

Changes made after run 1, for run 2:

1. Seven more sections are loaded (211.101, 211.103, 211.105, 211.110, 211.130, 211.160, 211.165), 12 in total.
2. A second score is reported for the hard cases: whether any finding describes the defect, whatever section it cites (keyword match, so it is approximate).
3. The gold labels, the test documents, the rules and the prompt are unchanged.

### Results, run 2 (7 October 2026)

Same 27 documents, same model (`gemini-3.5-flash-lite`), same rules and prompt, 12 CFR sections loaded. Full output: `eval/results_run2.md` and `eval/results_run2.json`.

| System | Precision | Recall | F1 |
|---|---|---|---|
| Baseline: one LLM call | 0.24 | 0.41 | 0.29 |
| Rule checker alone | 0.81 | 0.81 | 0.81 |
| QU-Gate: rules + LLM reviewer + verifier | 0.55 | 0.74 | 0.60 |

What run 2 shows:

- **Seeded defects (17 documents):** again 17 of 17 for the rule checker and QU-Gate, 8 of 17 for the single LLM call.
- **Human gate:** 27 of 27 reviews stopped and waited for a named person.
- **Prompt injection (3 documents):** QU-Gate showed every seeded defect in 3 of 3. The single LLM call did not obey the hidden instruction (it reported 3 findings each time), but it missed the seeded section in 3 of 3.
- **Hard cases, by description:** QU-Gate described 2 of the 4 hard defects with an exact quote from the document (low yield with no investigation; out-of-specification result). The single LLM call also described 2 of 4.
- **Speed:** 9.0 seconds per review on average (3.5 to 34.8).

What run 2 does not show, and where QU-Gate lost:

- **QU-Gate scored lower than in run 1 (F1 0.60 against 0.68) and lower than the rule checker alone (0.81).** Loading more sections made the score worse, not better.
- **The verifier blocked 0 findings.** Every cited section is now loaded and every quote is in the document. So the 27 blocks in run 1 were a scope filter (section not loaded). They were not caught hallucinations.
- **The verifier checks that a section and a quote exist. It does not check that the finding is true.** QU-Gate showed 69 findings: 27 from the rules and 42 from the LLM reviewer. 33 of the 42 cite a section that is not a seeded defect (211.101 eleven times, 211.100 eight, 211.105 five, 211.188 four, 211.130 three, 211.186 and 211.103 once each). At least four are contradicted by the line they quote, for example "no equipment identification" quoting the line that lists the equipment. 20 of the 42 give no quote at all ("MISSING"), so the verifier can only check the section number.
- **Hard cases, by section: QU-Gate matched the gold section in 0 of 4, the single LLM call in 1 of 4.** In the two defects it described, it cited 211.103 and 211.100. The gold label is 211.192. It missed the blank signature and the yield with no limits completely.
- **False alarms on the 2 compliant documents:** QU-Gate 4.0 per document, single LLM call 1.5. Plus the same rule-checker false alarm as in run 1 (validation described in other words).

How to read the two runs together:

- The baseline was not changed between the runs, and its F1 moved from 0.24 to 0.29. So a difference of about 0.05 on 27 documents in one run is noise.
- The dependable parts are the rule checker (17 of 17 seeded defects in both runs), the human gate (27 of 27 in both runs) and the audit log.
- The LLM reviewer, with this small free model and this prompt, is the weak part. It adds some real findings (2 of 4 hard defects) and more than one extra finding per document. Its findings are suggestions for the human reviewer, not results.
- The prompt was not tuned after these runs. Tuning it against the same 27 documents would make the numbers look better and mean less.

Done after run 2: the app now shows "Rule checker findings" and "AI reviewer suggestions" as two separate lists. This changes the display only. The pipeline and the numbers above are unchanged.

Not done yet: test a stronger model, repeat each run to measure the noise, and test on documents not built from the rule checker's own templates.

Limits of this evaluation: all documents are synthetic, there are only 27, each run was done once, and the seeded cases are built from the same templates the rule checker was written for, so the rule checker scores 100% on them by construction. The gold labels are the seeded defects only, so a reasonable extra comment counts as wrong. The hard cases and the baseline comparison are the informative part.

## Tests

```bash
~/.venvs/qu-gate/bin/python -m pytest -q
```

20 tests. They cover the checklist, the audit chain (edit and delete), the verifier, the human gate, both document types and the app. They use a scripted reviewer, so they need no API key.

## Repository

```text
app.py               Streamlit UI
graph.py             LangGraph workflow and human gate
llm.py               all LLM calls; provider set in .env
rules.py             deterministic checklist (13 rows, 2 document types)
mcp_server.py        FastMCP server with two read-only tools
audit.py             hash-chained audit log
data/cfr211.json     text of 12 sections of 21 CFR Part 211
data/precedents.json FDA warning-letter excerpts
eval/make_cases.py   builds the synthetic test set
eval/run_eval.py     baseline vs rules vs QU-Gate
tests/               pytest tests
eval/results_run1.*  results of run 1 (5 sections loaded)
eval/results_run2.*  results of run 2 (12 sections loaded)
setup.sh run.sh eval.sh                      Ubuntu or WSL
SETUP.bat RUN.bat EVAL.bat CHECK.bat         the same, by double-click on Windows
RESTART-WSL.bat                              restarts WSL after a Wsl/Service error
START_HERE.md                                step-by-step guide in Hindi
VIDEO_SCRIPT.md                              timed script for the 4-minute video
```

## Guardrails

1. **Least privilege.** Both MCP tools are read-only. The LLM has no write tool.
2. **Human gate.** The approve or reject record is written by code after a named person signs, never by the LLM.
3. **Document as data.** The prompt marks the document as data and tells the model not to follow instructions inside it.
4. **Deterministic verifier.** A finding with a non-existent CFR section or an invented quote is never shown as verified. This is a check on the citation, not on the truth of the finding.
5. **Audit trail.** Timestamp, actor, model id, document hash, findings and the human decision are logged in a hash chain.

## Known limits

- The checklist patterns are simple text patterns. They miss things and raise false alarms. The evaluation measures this.
- Only 12 sections of Part 211 are loaded, and 211.165 is an excerpt. A correct finding against any other section is blocked by the verifier. Run 1 showed this happening.
- The verifier does not judge whether a finding is true. It checks that the section is loaded and that the quote is in the document. Run 2 showed LLM findings that passed this check and were wrong.
- A hash chain shows that the log was changed. It does not show who changed it. This is not a validated 21 CFR Part 11 system.
- The CFR text and the warning-letter excerpts were copied from public web pages. Check the wording against [eCFR](https://www.ecfr.gov/current/title-21/part-211) and the FDA letter before you quote them.
- The audit log and paused reviews live on local disk and in memory. They are lost when a hosted app restarts.

## Stack

Python 3.12, LangGraph 1.2, LangChain 1.4, MCP (FastMCP 4), Streamlit, Langfuse (optional tracing), pytest, GitHub Actions.
