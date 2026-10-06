"""Append-only audit trail of what the agent did: output/audit_trail.json.

Each chat message the agent handles adds entries to the file:
  - one "tool_call" entry for every tool the agent called: time, tool name, short args, short result
  - one "run_end" entry: time, why the loop stopped (stop_reason), and a few counts

The file is a JSON list. New entries are written at the END of the list, in place. Existing entries are never
rewritten, and nothing here ever empties or deletes the file, so it keeps growing across runs and server restarts.
If the file were ever damaged, entries go to audit_trail.overflow.jsonl instead of replacing it.

Nothing the shopper typed is written here (only its length), and card numbers, passwords, and similar details are
removed from every value (see safety.scrub_for_log).
"""

import fcntl
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai.messages import ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart

from safety import scrub_for_log

log = logging.getLogger("campus_customs.audit")

AUDIT_FILE = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
OVERFLOW_FILE = AUDIT_FILE.with_name("audit_trail.overflow.jsonl")
_lock = threading.Lock()  # one writer at a time inside this process (fcntl.flock covers other processes)


def _iso(moment: datetime | None) -> str:
    return (moment or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec="seconds")


def append(entries: list[dict]) -> None:
    """Add entries to the end of the audit list without touching the entries already there."""
    if not entries:
        return
    body = ",\n".join("  " + json.dumps(e, ensure_ascii=False) for e in entries)
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        with os.fdopen(os.open(AUDIT_FILE, os.O_RDWR | os.O_CREAT, 0o644), "r+b") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                size = f.seek(0, os.SEEK_END)
                if size == 0:  # brand-new file
                    f.write(f"[\n{body}\n]\n".encode())
                    return
                start = max(0, size - 64)
                f.seek(start)
                tail = f.read().rstrip()
                if not tail.endswith(b"]"):
                    raise ValueError("audit_trail.json doesn't end with ']'")
                before = tail[:-1].rstrip()  # everything up to the last entry
                comma = "" if before.endswith(b"[") else ","
                f.seek(start + len(before))  # just after the last entry: only the closing bracket gets rewritten
                f.write(f"{comma}\n{body}\n]\n".encode())
            except ValueError:
                log.error("audit_trail.json is damaged; writing to %s instead (nothing was deleted)", OVERFLOW_FILE.name)
                with OVERFLOW_FILE.open("a", encoding="utf-8") as spill:
                    spill.write("\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n")
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)


# ---- turning an agent run into short entries ----

def _short_result(content: object) -> str:
    """One short line about what a tool returned."""
    if hasattr(content, "model_dump"):
        content = content.model_dump(mode="json")
    elif isinstance(content, list):
        content = [i.model_dump(mode="json") if hasattr(i, "model_dump") else i for i in content]
    if isinstance(content, list):
        names = [i.get("name") for i in content if isinstance(i, dict) and i.get("name")]
        return scrub_for_log(f"{len(content)} items" + (f": {', '.join(names[:4])}" if names else ""))
    if isinstance(content, dict):
        return scrub_for_log(json.dumps(content, ensure_ascii=False), limit=200)
    return scrub_for_log(content, limit=200)


def _short_args(args: dict) -> dict:
    return {k: (scrub_for_log(v, limit=100) if isinstance(v, str) else v) for k, v in args.items()}


def entries_from_messages(messages: list, run_id: str) -> list[dict]:
    """A tool_call entry for each tool the agent called, with its result filled in from the matching return."""
    entries: list[dict] = []
    by_call: dict[str, dict] = {}
    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    entry = {
                        "time": _iso(message.timestamp), "run_id": run_id, "event": "tool_call",
                        "tool": part.tool_name, "args": _short_args(part.args_as_dict()),
                        "result": None, "stop_reason": None,
                    }
                    entries.append(entry)
                    by_call[part.tool_call_id] = entry
        elif isinstance(message, ModelRequest):
            for part in message.parts:
                entry = by_call.get(getattr(part, "tool_call_id", None))
                if entry is None:
                    continue
                if isinstance(part, ToolReturnPart):
                    entry["result"] = _short_result(part.content)
                elif isinstance(part, RetryPromptPart):
                    entry["result"] = "retry asked: " + scrub_for_log(part.content, limit=120)
    return entries


def log_run(
    run_id: str, shopper: str, new_messages: list, stop_reason: str, message_chars: int,
    lookup_limit_hit: bool, removed: list[str], guards: list[str], error: str | None = None,
) -> None:
    """Write everything the agent did for one chat message. Never raises: the audit must not break the chat."""
    try:
        entries = entries_from_messages(new_messages, run_id)
        tool_calls = sum(1 for e in entries if e["tool"] != "final_result")
        entries.append({
            "time": _iso(None), "run_id": run_id, "event": "run_end", "tool": None, "args": None,
            "result": f"{tool_calls} tool call(s); shopper message was {message_chars} characters (not stored here)",
            "stop_reason": stop_reason,
            "model_calls": sum(1 for m in new_messages if isinstance(m, ModelResponse)),
            "shopper": shopper,
            "lookup_limit_hit": lookup_limit_hit,
            "sensitive_removed": removed,
            "safety_guards": guards,
            **({"error": scrub_for_log(error)} if error else {}),
        })
        append(entries)
    except Exception:
        log.exception("could not write the audit trail")
