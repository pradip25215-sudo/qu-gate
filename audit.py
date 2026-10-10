"""Append-only, hash-chained audit log. Standard library only.

Every record stores the hash of the record before it. If anyone edits or deletes a line,
verify() reports the first line where the chain breaks.
"""
import hashlib, json, threading, time
from pathlib import Path

LOG = Path(__file__).parent / "logs" / "audit.jsonl"
_LOCK = threading.Lock()                 # one writer at a time inside this process


def _hash(record: dict) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()


def _lines() -> list[str]:
    return LOG.read_text().splitlines() if LOG.exists() else []


def append(event: str, actor: str, payload: dict, model: str = "", once_per_review: bool = False) -> str:
    """Add one record and return its hash.

    once_per_review=True: if this review (payload["review_id"]) already has a record of this event,
    nothing is written and "" is returned. This is how a decision is recorded only once.
    """
    with _LOCK:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        lines = _lines()
        if once_per_review:
            for old in records():
                if old.get("event") == event and old.get("payload", {}).get("review_id") == payload.get("review_id"):
                    return ""
        try:
            prev = json.loads(lines[-1])["hash"] if lines else "GENESIS"
        except (ValueError, KeyError):
            prev = "UNREADABLE"          # the last line was damaged; verify() will report it
        record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event,
                  "actor": actor, "model": model, "payload": payload, "prev": prev}
        record["hash"] = _hash(record)
        line = json.dumps(record, sort_keys=True)
        with LOG.open("a") as f:
            f.write(line + "\n")
        # Guard against a repeated write (seen once on a Windows folder used from WSL; cause not confirmed).
        # A record can never legitimately appear twice, because each one contains the hash before it.
        after = _lines()
        if len(after) >= 2 and after[-1] == after[-2] == line:
            while len(after) >= 2 and after[-1] == after[-2]:
                after.pop()
            LOG.write_text("\n".join(after) + "\n")
        return record["hash"]


def verify() -> tuple[bool, int]:
    """Return (chain_ok, first_bad_line). first_bad_line is 0 when the chain is intact."""
    prev = "GENESIS"
    for n, line in enumerate(_lines(), start=1):
        try:
            record = json.loads(line)
            claimed = record.pop("hash")
        except (ValueError, KeyError):
            return False, n
        if record.get("prev") != prev or _hash(record) != claimed:
            return False, n
        prev = claimed
    return True, 0


def records() -> list[dict]:
    out = []
    for line in _lines():
        try:
            out.append(json.loads(line))
        except ValueError:
            out.append({"event": "UNREADABLE LINE", "actor": "", "ts": "", "model": "", "payload": {}})
    return out
