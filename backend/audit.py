"""Append-only audit trail of agent activity: output/audit_trail.json (a JSON array, one entry per chat turn).

Entries are only ever added: each write splices the new entry in before the closing "]" under an
exclusive file lock, so existing entries are never rewritten and the file survives restarts.
"""

import fcntl
import json
import logging
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart
from pydantic_core import to_jsonable_python

from models import AuditEntry, AuditToolCall

log = logging.getLogger("campus_customs.audit")

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
TEXT_LIMIT = 300
OUTPUT_TOOL = "final_result"  # PydanticAI's structured-output tool; logged as the stop, not as a tool call
_lock = threading.Lock()

# PII scrubbing: nothing sensitive a shopper types should land in the log.
_CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\d)")


def redact(text: str) -> str:
    text = _CARD.sub("[card number removed]", text)
    text = _EMAIL.sub("[email removed]", text)
    return _PHONE.sub("[phone removed]", text)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def short(text: str, limit: int = TEXT_LIMIT) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summarize_result(content: object) -> tuple[str, bool]:
    """Compact, human-readable summary of a tool result, plus whether it succeeded."""
    data = to_jsonable_python(content)
    if isinstance(data, dict):
        ok = data.get("found", True) is not False and "error" not in data
        if "results" in data and "total_matches" in data:
            ids = [r.get("product_id") for r in data["results"]]
            fixes = f", corrected {data['corrections']}" if data.get("corrections") else ""
            return short(f"{data['total_matches']} matches{fixes}; returned {len(ids)}: {', '.join(ids)}"), True
        if "requested_size_status" in data:
            sizes = ", ".join(f"{s['size']}={s['quantity']}" for s in data.get("sizes", []))
            status = f" → {data['requested_size']} {data['requested_size_status']}" if data.get("requested_size") else ""
            return short(f"{data.get('product_id')}: {sizes}{status}"), ok
        if "price_display" in data and "product_id" in data:
            return short(f"{data['product_id']}: {data['price_display']}"), ok
        if "logged_in" in data:
            return ("logged_in=true (own profile)" if data["logged_in"] else "logged_in=false"), True
        return short(json.dumps(data, ensure_ascii=False)), ok
    return short(json.dumps(data, ensure_ascii=False)), True


def build_entry(
    *,
    run_id: str,
    model: str,
    started: float,
    finished: float,
    messages: list[ModelMessage],
    history_len: int,
    user_id: int | None,
    page: str | None,
    message: str,
    stop_reason: str,
    reply: str,
    product_ids: list[str],
    degraded: bool,
    usage: object | None = None,
) -> AuditEntry:
    """Turn this turn's PydanticAI messages (excluding replayed history) into an audit entry."""
    new = messages[history_len:]
    calls: dict[str, dict] = {}
    order: list[str] = []
    retries: list[str] = []
    requests = 0
    for msg in new:
        if isinstance(msg, ModelResponse):
            requests += 1
            for part in msg.parts:
                if isinstance(part, ToolCallPart) and part.tool_name != OUTPUT_TOOL:
                    args = {k: redact(v) if isinstance(v, str) else v for k, v in part.args_as_dict().items()}
                    calls[part.tool_call_id] = {"tool": part.tool_name, "args": args, "result": "(no result)", "ok": False}
                    order.append(part.tool_call_id)
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_call_id in calls:
                    summary, ok = summarize_result(part.content)
                    calls[part.tool_call_id].update(result=summary, ok=ok, timestamp=part.timestamp.isoformat())
                elif isinstance(part, RetryPromptPart):
                    target = part.tool_name or "output"
                    text = part.content if isinstance(part.content, str) else json.dumps(to_jsonable_python(part.content))
                    retries.append(short(f"{target}: {text}", 200))
                    if part.tool_call_id in calls:
                        calls[part.tool_call_id].update(result=short(f"retry: {text}", 200), ok=False)
    return AuditEntry(
        timestamp=now_iso(),
        run_id=run_id,
        model=model,
        user_id=user_id,
        page=page,
        message=short(redact(message)),
        tool_calls=[AuditToolCall(**calls[i]) for i in order],
        retries=retries,
        model_requests=getattr(usage, "requests", None) or requests,
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        stop_reason=stop_reason,
        reply=short(redact(reply)),
        product_ids=product_ids,
        degraded=degraded,
        duration_ms=int((finished - started) * 1000),
    )


def append_audit_entry(entry: AuditEntry, path: Path = AUDIT_PATH) -> None:
    """Append one entry without rewriting earlier ones. Never raises: auditing must not break chat."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        block = json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, indent=2)
        block = "\n".join("  " + line for line in block.splitlines())
        with _lock:  # threads in this process
            fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
            with os.fdopen(fd, "r+b") as f:
                fcntl.flock(f, fcntl.LOCK_EX)  # other processes (e.g. a second worker)
                try:
                    _splice(f, block, path)
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        log.exception("Could not write audit entry")


def _splice(f, block: str, path: Path) -> None:
    f.seek(0, os.SEEK_END)
    size = f.tell()
    if size == 0:
        f.write(f"[\n{block}\n]\n".encode())
        return
    # Find the closing "]" by scanning back over trailing whitespace.
    pos, tail = size, b""
    while pos > 0:
        step = min(4096, pos)
        pos -= step
        f.seek(pos)
        tail = f.read(step) + tail
        if tail.strip():
            break
    stripped = tail.rstrip()
    if not stripped.endswith(b"]"):
        # Not a JSON array we wrote: keep it (never delete) and start a fresh file.
        backup = path.with_name(f"{path.stem}.corrupt-{datetime.now():%Y%m%d-%H%M%S}{path.suffix}")
        f.close()
        path.rename(backup)
        log.error("Audit file was not a JSON array; moved to %s", backup.name)
        path.write_text(f"[\n{block}\n]\n", encoding="utf-8")
        return
    before = stripped[:-1].rstrip()  # everything up to the last entry's "}" (or the opening "[")
    f.seek(pos + len(before))
    f.truncate()
    separator = "\n" if before.endswith(b"[") else ",\n"
    f.write(f"{separator}{block}\n]\n".encode())
