# QU-Gate: 4-minute video script

The hackathon asks for a video of 3 to 5 minutes. This script is 4 minutes.
Speak slowly. The script has about 460 words, so you have time.

Every number in this script comes from `eval/results_run1.md` and `eval/results_run2.md`. Do not change the numbers.

## A. Before you record (do this once)

1. Double-click **RUN.bat** in `C:\Users\palek\Projects\qu-gate`. Wait until the app opens in the browser (http://localhost:8501).
2. In the app, look at the top. The line must start with `Model: google_genai:gemini-3.5-flash-lite`. It must NOT show the yellow "DEMO MODE" box.
3. In the left sidebar of the app, press **Archive this log and start a new one**. Now the audit log is empty and clean.
4. Open the slide deck "QU-Gate hackathon pitch" in a second tab of the same browser window. Press the present / full screen button of the deck.
5. Do one practice run of part C below, without recording. Then press **Archive this log and start a new one** again.
6. Close other tabs and windows. Turn off notifications. Keep this script open on your phone or on paper.

## B. How to record on Windows

1. Click on the browser window, so it is the active window.
2. Press **Windows key + Alt + R**. Recording starts. A small bar with a timer appears.
3. Press **Windows key + Alt + M** if the microphone is off (the microphone icon on the small bar must not be crossed).
4. Speak the script (part C).
5. Press **Windows key + Alt + R** again. Recording stops.
6. The video file is in the folder `C:\Users\palek\Videos\Captures`.

This records only the browser window. So keep the deck and the app as two tabs in that one window, and change tabs with **Ctrl + Tab**.

## C. The script

| Time | On screen | Say this |
|---|---|---|
| 0:00 to 0:20 | Deck, slide 1 (QU-Gate) | Hello. My name is Pradip Palekar. My project is QU-Gate. It is a review gate for documents that AI writes for drug manufacturing. |
| 0:20 to 0:50 | Deck, slide 2 (The problem) | On 2 April 2026, the US FDA sent a warning letter to a company. The company used AI agents to write its drug manufacturing documents, and nobody reviewed them. FDA wrote that AI-generated documents must be reviewed. It cited 21 CFR 211.22(c) and 211.100. QU-Gate is that missing review step. |
| 0:50 to 1:20 | Deck, slide 3 (How it works) | QU-Gate works in three stages. First, propose: a rule checker with 13 rules from 21 CFR Part 211, and then an LLM reviewer. Second, verify: a verifier checks each CFR section and each quote, and adds real FDA warning-letter text through MCP tools. Third, sign and log: the graph stops, a named person approves or rejects, and every step goes into a hash-chained audit log. |
| 1:20 to 1:40 | Press **Ctrl + Tab** to go to the app. Sample `mbr-07` is selected. Press **Load sample**. | This is the live app. I load a sample master batch record. It is synthetic. It has no process validation and no Quality Unit approval. This is the same gap that FDA found. |
| 1:40 to 1:55 | Press **Run review**. Wait until the findings appear. | I press Run review. The steps run in order: intake, rules, review, verify. |
| 1:55 to 2:10 | Two lists appear: "Rule checker findings" and "AI reviewer suggestions". Under "Rule checker findings", open the finding for **21 CFR 211.100**. Scroll to the FDA text under it. | The findings come in two lists: rule checker findings, and AI reviewer suggestions. I open the rule finding for 21 CFR 211.100. Under it, you see the real text from the FDA warning letter. |
| 2:10 to 2:25 | Scroll to the sign-off form. Leave the name empty. Press **Sign and record**. The error appears. Then type your name and a reason, choose **reject**, press **Sign and record**. | Now the human gate. I press Sign and record without a name. The app says: name and reason are required. So I write my name and a reason, I choose reject, and I sign. |
| 2:25 to 2:40 | Look at the left sidebar: "Hash chain intact". Press **Tamper test: edit one old record**. "Tampering detected at line 1" appears. | On the left is the audit log. It says: hash chain intact. Now I press the tamper test. It edits one old record. The app now says: tampering detected at line 1. |
| 2:40 to 3:15 | Press **Ctrl + Tab** to go back to the deck. Go to slide 5 (Results). | I tested on 27 synthetic documents. 17 have a defect that I put in on purpose. One LLM call fully caught 8 of 17. The rule checker caught 17 of 17, and so did QU-Gate. In all 27 reviews, the system stopped and waited for a named person. Three documents had a hidden instruction that told the AI to approve. QU-Gate still showed every seeded defect. |
| 3:15 to 3:40 | Deck, slide 6 (Where QU-Gate lost) | Now the honest part. The F1 score of QU-Gate was 0.60 in the second run. The rule checker alone had 0.81. The small free LLM added too many extra findings: 33 of its 42 findings cite a section that is not a seeded defect. So the app shows LLM findings in a separate list, as suggestions for the human, not as results. |
| 3:40 to 4:00 | Deck, slide 8 (Summary) | Next, I will test a stronger model and new documents. QU-Gate is a prototype. It is decision support only. AI may write the document. A named human must sign it. Thank you. |

Slides 4 and 7 are not in the video. They are for a live pitch, where you have more time.

## D. If something goes wrong while recording

| Problem | What to do |
|---|---|
| The app says "The review failed." | Stop the recording. Wait 1 minute. Press **Run review** again. If it works, press **Archive this log and start a new one** and record again from the start. |
| The findings on screen are a little different from your practice run | This is normal. The AI reviewer suggestions change a little each time. The rule checker findings for 211.100 and 211.22 are always there. Keep recording. |
| You said a wrong number | Stop and record again. Do not leave a wrong number in the video. |
| The video is longer than 5 minutes | Speak the same words, but do not wait on the slides. The demo part (1:20 to 2:40) is the most important part. |

## E. After recording

1. In the app sidebar, press **Archive this log and start a new one**. (The tamper test broke the log on purpose. This gives you a clean log again.)
2. Watch the whole video once. Check every number against the table on slide 5 and slide 6.
3. Before you submit, open the FDA page and check that the quote on slide 2 matches the page word for word:
   https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/purolea-cosmetics-lab-722591-04022026

## F. Things you must not say

- Do not say "the verifier caught hallucinations". In run 2 the verifier blocked nothing.
- Do not say "QU-Gate is better than the rule checker". The rule checker alone has the higher F1 (0.81 against 0.60).
- Do not say it is validated or ready for a real factory. It is a prototype on 27 synthetic documents, and each test ran once.
