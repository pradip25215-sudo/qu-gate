# QU-Gate evaluation (27 of 27 synthetic documents, model setting: google_genai:gemini-3.5-flash-lite)

| System | Precision | Recall | F1 |
|---|---|---|---|
| baseline | 0.19 | 0.37 | 0.24 |
| rules | 0.81 | 0.81 | 0.81 |
| qugate | 0.64 | 0.78 | 0.68 |

- Recall on seeded cases (n=17): baseline 0.53, rules 1.00, qugate 1.00
- Recall on hard cases (n=5): baseline 0.20, rules 0.00, qugate 0.00
- Recall on injection cases (n=3): baseline 0.00, rules 1.00, qugate 1.00
- False alarms on clean documents (n=2): baseline 2.5 per document, qugate 0.5 per document
- Baseline findings with an unverifiable citation or quote: 44 of 78
- Findings blocked by the QU-Gate verifier: 27
- Runs that stopped at the human gate: 27 of 27
- Mean seconds per QU-Gate review: 4.6
- Cases where QU-Gate missed a gold section: mbr-hard-blank-signature, mbr-hard-yield-no-limits, bpr-hard-low-yield, bpr-hard-out-of-spec
- Compliant documents where QU-Gate raised a false alarm: mbr-00, mbr-hard-reworded-validation
- Models that answered: google_genai:gemini-3.5-flash-lite
