"""Audit trail must stay valid JSON, only grow, and never lose entries. Run: python -m pytest tests -q"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit import append_audit_entry, now_iso  # noqa: E402
from models import AuditEntry  # noqa: E402


def entry(i: int) -> AuditEntry:
    return AuditEntry(timestamp=now_iso(), run_id=f"r{i}", model="test", user_id=None, page="/", message=f"m{i}",
                      stop_reason="final_result", reply="ok")


def test_appends_keep_valid_json_and_order(tmp_path):
    path = tmp_path / "audit.json"
    for i in range(3):
        append_audit_entry(entry(i), path)
        assert [e["run_id"] for e in json.loads(path.read_text())] == [f"r{j}" for j in range(i + 1)]


def test_existing_bytes_are_never_rewritten(tmp_path):
    path = tmp_path / "audit.json"
    append_audit_entry(entry(0), path)
    first = path.read_bytes().rstrip()[:-1].rstrip()  # file minus the closing "]"
    append_audit_entry(entry(1), path)
    assert path.read_bytes().startswith(first)


def test_concurrent_writers_lose_nothing(tmp_path):
    path = tmp_path / "audit.json"
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda i: append_audit_entry(entry(i), path), range(40)))
    assert sorted(e["run_id"] for e in json.loads(path.read_text())) == sorted(f"r{i}" for i in range(40))


def test_corrupt_file_is_kept_not_wiped(tmp_path):
    path = tmp_path / "audit.json"
    path.write_text("not json at all")
    append_audit_entry(entry(0), path)
    assert [e["run_id"] for e in json.loads(path.read_text())] == ["r0"]
    backups = list(tmp_path.glob("audit.corrupt-*.json"))
    assert len(backups) == 1 and backups[0].read_text() == "not json at all"


def test_empty_array_file(tmp_path):
    path = tmp_path / "audit.json"
    path.write_text("[]\n")
    append_audit_entry(entry(0), path)
    assert len(json.loads(path.read_text())) == 1


def test_redacts_pii():
    from audit import redact
    assert redact("card 4111 1111 1111 1111 ok") == "card [card number removed] ok"
    assert redact("mail a.b@yale.edu") == "mail [email removed]"
    assert redact("call 203-555-0142") == "call [phone removed]"
    assert redact("XL for $68.00, the 2025 tee") == "XL for $68.00, the 2025 tee"


def test_chat_rate_limit_returns_429_and_is_audited(monkeypatch):
    from fastapi.testclient import TestClient
    import main
    from models import ChatResponse

    async def fake_run_chat(*_args, **_kwargs):
        return ChatResponse(reply="ok")

    audited = []
    monkeypatch.setattr(main, "run_chat", fake_run_chat)
    monkeypatch.setattr(main, "append_audit_entry", audited.append)
    main._chat_hits.clear()
    client = TestClient(main.app)
    codes = [client.post("/api/chat", json={"message": "hi"}).status_code for _ in range(main.CHAT_RATE_LIMIT + 2)]
    assert codes[: main.CHAT_RATE_LIMIT] == [200] * main.CHAT_RATE_LIMIT
    assert codes[main.CHAT_RATE_LIMIT:] == [429, 429]
    assert [e.stop_reason for e in audited] == ["rate_limited", "rate_limited"]
    main._chat_hits.clear()


def test_fallback_turn_is_audited_with_stop_reason(monkeypatch):
    import asyncio
    import agent

    audited = []
    monkeypatch.setattr(agent, "SIMULATE_OUTAGE", True)
    monkeypatch.setattr(agent, "append_audit_entry", audited.append)
    response = asyncio.run(agent.run_chat("navy hoodies", []))
    assert response.degraded and response.products
    assert audited[0].stop_reason == "fallback:RuntimeError"
    assert audited[0].degraded and audited[0].product_ids == [c.product_id for c in response.products]
