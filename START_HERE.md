# यहाँ से शुरू करें (QU-Gate)

Project का folder Windows में यहाँ है: `C:\Users\palek\Projects\qu-gate`
Ubuntu (WSL) में वही folder यहाँ दिखता है: `/mnt/c/Users/palek/Projects/qu-gate`

## सबसे आसान तरीका (सिर्फ़ double-click)

1. File Explorer में `C:\Users\palek\Projects\qu-gate` खोलें।
2. **SETUP.bat** पर double-click करें। काली window खुलेगी। 3 से 10 मिनट रुकें, जब तक `SETUP DONE.` न दिखे। फिर कोई भी key दबाकर window बंद करें।
3. **RUN.bat** पर double-click करें। लगभग 10 second में browser में app खुल जाएगा (http://localhost:8501)।
4. App बंद करने के लिए RUN वाली काली window बंद कर दें।

Windows "Windows protected your PC" पूछे तो **More info** और फिर **Run anyway** दबाएँ।

अगर double-click से काम न हो, तो नीचे लिखे Ubuntu terminal वाले steps करें। दोनों तरीके एक ही काम करते हैं।

---

नीचे की हर command Ubuntu terminal में चलानी है।

## 1. Setup (सिर्फ़ एक बार)

1. Start menu से **Ubuntu** खोलें।
2. यह दो commands चलाएँ:

```bash
cd /mnt/c/Users/palek/Projects/qu-gate
bash setup.sh
```

3. 3 से 10 मिनट रुकें। अंत में यह दिखना चाहिए:

```text
20 passed
SETUP DONE.
```

`setup.sh` खुद Python 3.12 का environment बनाता है, सारे packages install करता है, `.env` file बनाता है और tests चलाता है। `sudo` या password नहीं माँगेगा।

## 2. App चलाएँ

```bash
cd /mnt/c/Users/palek/Projects/qu-gate
bash run.sh
```

फिर Windows के browser में खोलें: http://localhost:8501

App बंद करने के लिए terminal में `Ctrl+C` दबाएँ।

## 3. App में क्या करना है (demo का रास्ता)

1. "Sample documents" में `mbr-07` चुनें और **Load sample** दबाएँ। यह FDA वाले case जैसा document है: process validation नहीं, Quality Unit approval नहीं।
2. **Run review** दबाएँ। Steps एक-एक करके दिखेंगे: intake, rules, review, verify।
3. Findings दो lists में दिखेंगे: "Rule checker findings" और "AI reviewer suggestions"। "Rule checker findings" में 21 CFR 211.100 वाला finding खोलें। नीचे असली FDA warning letter का हिस्सा दिखेगा।
4. "Blocked by the verifier" table देखें। यहाँ वे findings हैं जिन्हें verifier ने रोका।
5. बिना नाम भरे **Sign and record** दबाएँ। Error आएगा: "Name and reason are required."
6. नाम और कारण भरें, "reject" चुनें, **Sign and record** दबाएँ।
7. बाईं तरफ़ sidebar में "Hash chain intact" दिखेगा।
8. Sidebar में **Tamper test: edit one old record** दबाएँ। अब "Tampering detected at line 1" दिखेगा।
9. नया साफ़ log शुरू करने के लिए **Archive this log and start a new one** दबाएँ।

## 4. असली model जोड़ें (अभी app DEMO MODE में है)

बिना API key के app "DEMO MODE" में चलता है। Rule checker, verifier, human gate और audit log असली हैं। सिर्फ़ LLM reviewer नकली (scripted) है।

1. https://aistudio.google.com खोलें, Google account से login करें, **Get API key** दबाएँ, key copy करें।
2. VS Code में project खोलें:

```bash
cd /mnt/c/Users/palek/Projects/qu-gate
code .
```

3. VS Code में `.env` file खोलें। यह line ढूँढें और key `=` के ठीक बाद paste करें (बीच में space नहीं):

```text
GOOGLE_API_KEY=यहाँ_अपनी_key
```

4. (Optional backup) https://console.groq.com/keys से key लेकर `GROQ_API_KEY=` के बाद paste करें।
5. File save करें (`Ctrl+S`)।
6. Terminal में app बंद करें (`Ctrl+C`) और फिर चलाएँ: `bash run.sh`
7. अब ऊपर पीला "DEMO MODE" box नहीं दिखेगा। उसकी जगह "Model: google_genai:gemini-3.8-flash" दिखेगा।

अगर model के नाम का error आए: AI Studio में जो Flash model free दिखे, उसका नाम `.env` में इस तरह लिखें: `QUGATE_MODEL=google_genai:MODEL-NAME`

**अगर hackathon में OpenAI ज़रूरी है:** `.env` में `OPENAI_API_KEY=` भरें, और `# QUGATE_MODEL=openai:PUT-MODEL-ID-HERE` वाली line से `# ` हटाकर model id लिखें।

## 5. Evaluation चलाएँ (असली key लगाने के बाद)

```bash
cd /mnt/c/Users/palek/Projects/qu-gate
bash eval.sh --limit 5
```

ठीक चले तो पूरा चलाएँ (27 documents, लगभग 5 से 10 मिनट):

```bash
bash eval.sh
```

Windows में यही काम **EVAL.bat** पर double-click से होता है।

Result यहाँ बनेगा: `eval/results.md`।

**यह दो बार चल चुका है (7 October 2026)।** Results यहाँ रखे हैं, इन्हें मत हटाएँ:

- Run 1 (5 CFR sections): `eval/results_run1.md`
- Run 2 (12 CFR sections): `eval/results_run2.md`

दोनों की table और जो cases fail हुए, वे `README.md` में "Results, run 1" और "Results, run 2" में लिखे हैं। Slides और video में सिर्फ़ यही numbers बोलें।

दोबारा चलाने की ज़रूरत नहीं है। अगर फिर भी चलाएँ, तो नया result `eval/results.md` में जाएगा; run 1 और run 2 की files नहीं बदलेंगी।

## 6. GitHub पर डालें

पहले github.com पर `qu-gate` नाम का खाली repository बनाएँ (README मत जोड़ें)। फिर:

```bash
cd /mnt/c/Users/palek/Projects/qu-gate
git init
git add .
git commit -m "QU-Gate: review gate for AI-written GMP documents"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/qu-gate.git
git push -u origin main
```

`.env` file GitHub पर नहीं जाएगी (`.gitignore` में है), इसलिए आपकी key सुरक्षित रहेगी।

Hackathon के rules में code publish करने की अनुमति है या नहीं, यह push करने से पहले पूछ लें।

## 7. कुछ गड़बड़ हो तो

| समस्या | क्या करें |
|---|---|
| `bash: setup.sh: No such file` | पहले `cd /mnt/c/Users/palek/Projects/qu-gate` चलाएँ |
| `curl: command not found` | `sudo apt update && sudo apt install -y curl` चलाएँ, फिर `bash setup.sh` |
| Browser में page नहीं खुलता | Terminal में `bash run.sh` चल रहा है या नहीं देखें; फिर http://localhost:8501 दोबारा खोलें |
| "The review failed" | `.env` में key और model का नाम जाँचें; free limit लगी हो तो 1 मिनट रुककर दोबारा चलाएँ |
| काली window में `Wsl/Service/0x80072746` या "An existing connection was forcibly closed" | **RESTART-WSL.bat** पर double-click करें। `Done` दिखने तक रुकें, window बंद करें। फिर **RUN.bat** या **EVAL.bat** दोबारा double-click करें |
| EVAL बीच में रुक गया (`429` या `503`) | कुछ नहीं बिगड़ा। **EVAL.bat** दोबारा double-click करें; वह वहीं से आगे चलेगा जहाँ रुका था। `429` का मतलब आज की free limit ख़त्म; अगले दिन चलाएँ |
| Tests fail | `bash setup.sh` दोबारा चलाएँ और पूरा output मुझे भेजें |
