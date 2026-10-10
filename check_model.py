"""Test the Google API key and find a Gemini model that works with QU-Gate.

Run from the project folder:   ~/.venvs/qu-gate/bin/python check_model.py      (or double-click CHECK.bat)
It tests every Flash model once, writes logs/check.txt (the key itself is never written), and saves
the working main model and backups in .env (QUGATE_MODEL, QUGATE_FALLBACK).
"""
import json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import llm                                              # noqa: E402  (also loads .env)

API = "https://generativelanguage.googleapis.com/v1beta"
SKIP = ("live", "tts", "image", "audio", "native", "transcribe", "embedding", "computer", "robotics")
LINES: list[str] = []


def say(*parts) -> None:
    line = llm.scrub(" ".join(str(p) for p in parts))
    print(line)
    LINES.append(line)


def call(path: str, key: str, body: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(f"{API}/{path}", data=json.dumps(body).encode() if body else None,
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}
    except Exception as e:                              # noqa: BLE001  (no network, DNS, timeout)
        return 0, {"error": {"message": f"{type(e).__name__}: {e}"}}


def err(data: dict) -> str:
    """Short reason for a failed call. For a quota error it names the quota that ran out and its limit."""
    e = data.get("error", {})
    parts = []
    for d in e.get("details", []):
        for v in d.get("violations", []):
            parts.append(f"quota {v.get('quotaId', '?')} limit={v.get('quotaValue', '?')}")
        if d.get("retryDelay"):
            parts.append(f"retry in {d['retryDelay']}")
    return (f"{e.get('status', '')} " + ("; ".join(parts) if parts else e.get("message", "")[:300])).strip()


def rank(name: str) -> tuple:
    """Newest stable full-size Flash first. Lite and preview models go last."""
    nums = [int(x) for x in re.findall(r"\d+", name)[:2]] + [0, 0]
    return ("preview" in name or "exp" in name, "lite" in name, -nums[0], -nums[1], name)


def set_env(key: str, value: str) -> None:
    path = HERE / ".env"
    lines = path.read_text().splitlines() if path.exists() else []
    lines = [l for l in lines if not l.startswith(key + "=")]
    lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    say("QU-Gate model check", time.strftime("%Y-%m-%d %H:%M:%S"))
    key = os.getenv("GOOGLE_API_KEY", "")
    say("model setting now:", llm.MODEL, "| fallback:", llm.FALLBACK or "none")
    if not key:
        say("RESULT: GOOGLE_API_KEY is empty in .env. Paste the key after GOOGLE_API_KEY= and run again.")
        return 1
    say("GOOGLE_API_KEY: present, length", len(key), "starts with", key[:3] + "...")

    status, data = call("models?pageSize=200", key)
    if status != 200:
        say("list models: HTTP", status, err(data))
        say("RESULT: the key was refused or the network is blocked. Create a new key at https://aistudio.google.com "
            "(Get API key) and paste it after GOOGLE_API_KEY= in .env.")
        return 1
    names = [m["name"].split("/", 1)[1] for m in data.get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    flash = sorted((n for n in names if "flash" in n and not any(w in n for w in SKIP)), key=rank)
    say("list models: HTTP 200,", len(names), "text models. Flash candidates:", ", ".join(flash) or "none")

    current = llm.MODEL.split(":", 1)[1] if llm.MODEL.startswith("google_genai:") else ""
    say("Testing every candidate with one small call:")
    ok = []
    for name in flash[:14]:
        status, data = call(f"models/{name}:generateContent", key,
                            {"contents": [{"parts": [{"text": "Reply with the single word OK."}]}]})
        say(f"  {name}: HTTP {status}", "OK" if status == 200 else err(data))
        if status == 200:
            ok.append(name)
        time.sleep(1)
    if not ok:
        say("RESULT: no Gemini model accepts requests from this key right now (busy or free quota used up). "
            "Try again later, or add a Groq key (GROQ_API_KEY) in .env.")
        return 1

    order = ([current] if current in ok else []) + [n for n in ok if n != current]
    working = ""
    for name in order[:3]:
        llm.MODEL, llm.FALLBACK, llm.IS_DEMO = f"google_genai:{name}", "", False
        try:
            found = llm.review("MBR", (HERE / "eval" / "docs" / "mbr-07.txt").read_text(), [])
            say(f"  QU-Gate review with {name}: OK,", len(found), "findings:", [f["cfr_section"] for f in found])
            working = name
            break
        except Exception as exc:                        # noqa: BLE001
            say(f"  QU-Gate review with {name}: FAILED", llm.log_error(exc)[:600])
    if not working:
        say("RESULT: small calls work but a full review failed. See logs/errors.log.")
        return 1
    backups = [n for n in ok if n != working][:3]
    set_env("QUGATE_MODEL", f"google_genai:{working}")
    set_env("QUGATE_FALLBACK", ",".join(f"google_genai:{n}" for n in backups))
    say(f"RESULT: main model {working}; backups {', '.join(backups) or 'none'}. Saved in .env.")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        (HERE / "logs").mkdir(exist_ok=True)
        (HERE / "logs" / "check.txt").write_text("\n".join(LINES) + "\n")
    sys.exit(code)
