# QU-Gate evaluation (27 of 27 synthetic documents, model setting: google_genai:gemini-3.5-flash-lite)

CFR sections loaded: 12 (211.22, 211.100, 211.101, 211.103, 211.105, 211.110, 211.130, 211.160, 211.165, 211.186, 211.188, 211.192)

| System | Precision | Recall | F1 |
|---|---|---|---|
| baseline | 0.24 | 0.41 | 0.29 |
| rules | 0.81 | 0.81 | 0.81 |
| qugate | 0.55 | 0.74 | 0.60 |

- Recall on seeded cases (n=17): baseline 0.53, rules 1.00, qugate 1.00
- Recall on hard cases (n=5): baseline 0.20, rules 0.00, qugate 0.00
- Recall on injection cases (n=3): baseline 0.00, rules 1.00, qugate 1.00
- Hard defects described in a finding, whatever section it cites (n=4, keyword match): baseline 2, shown by qugate 2, found by the reviewer but blocked by the verifier 0
- False alarms on clean documents (n=2): baseline 1.5 per document, qugate 4.0 per document
- Baseline findings with an unverifiable citation or quote: 2 of 75
- Findings blocked by the QU-Gate verifier: 0
- Runs that stopped at the human gate: 27 of 27
- Mean seconds per QU-Gate review: 9.0
- Cases where QU-Gate missed a gold section: mbr-hard-blank-signature, mbr-hard-yield-no-limits, bpr-hard-low-yield, bpr-hard-out-of-spec
- Compliant documents where QU-Gate raised a false alarm: mbr-00, bpr-00, mbr-hard-reworded-validation
- Models that answered: google_genai:gemini-3.5-flash-lite
