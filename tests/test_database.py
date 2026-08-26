import pytest
import pytest_asyncio
import os
import aiosqlite
from pathlib import Path

import database as db

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(tmp_path, monkeypatch):
    test_db_file = tmp_path / "test_bot.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_file)
    await db.init_db()
    yield test_db_file

@pytest.mark.asyncio
async def test_init_db_creates_tables():
    # Calling init_db multiple times should be idempotent
    await db.init_db()
    stats = await db.get_stats()
    assert stats == {"total": 0, "pending": 0, "replied": 0}

@pytest.mark.asyncio
async def test_create_and_get_request():
    req_id = await db.create_request(
        user_id=12345678,
        username="john_doe",
        full_name="John Doe",
        api_key="sk-openai-test-key-123"
    )
    assert req_id == 1

    req = await db.get_request_by_id(req_id)
    assert req is not None
    assert req["id"] == 1
    assert req["user_id"] == 12345678
    assert req["username"] == "john_doe"
    assert req["full_name"] == "John Doe"
    assert req["api_key"] == "sk-openai-test-key-123"
    assert req["status"] == "pending"
    assert req["response_credit"] is None
    assert req["admin_message_id"] is None

@pytest.mark.asyncio
async def test_set_and_get_by_admin_message_id():
    req_id = await db.create_request(
        user_id=98765432,
        username=None,
        full_name="Anonymous User",
        api_key="sk-ant-test-key-456"
    )
    await db.set_admin_message_id(req_id, 55501)

    req = await db.get_request_by_admin_message(55501)
    assert req is not None
    assert req["id"] == req_id
    assert req["admin_message_id"] == 55501
    assert req["username"] is None

    # Non-existent admin message id
    not_found = await db.get_request_by_admin_message(99999)
    assert not_found is None

@pytest.mark.asyncio
async def test_update_request_reply():
    req_id = await db.create_request(
        user_id=111222,
        username="alice",
        full_name="Alice Wonderland",
        api_key="sk-alice-789"
    )

    updated = await db.update_request_reply(req_id, "$50.00 credit remaining (Exp: 2027)")
    assert updated is not None
    assert updated["id"] == req_id
    assert updated["status"] == "replied"
    assert updated["response_credit"] == "$50.00 credit remaining (Exp: 2027)"
    assert updated["replied_at"] is not None

    stats = await db.get_stats()
    assert stats["total"] == 1
    assert stats["pending"] == 0
    assert stats["replied"] == 1

@pytest.mark.asyncio
async def test_get_user_recent_requests():
    user_id = 999
    # Create 7 requests for user 999
    for i in range(1, 8):
        await db.create_request(
            user_id=user_id,
            username="test_multi",
            full_name="Test Multi",
            api_key=f"key-{i}"
        )

    # By default limit is 5
    recent_5 = await db.get_user_recent_requests(user_id, limit=5)
    assert len(recent_5) == 5
    assert recent_5[0]["api_key"] == "key-7"  # Most recent first

    all_7 = await db.get_user_recent_requests(user_id, limit=10)
    assert len(all_7) == 7

@pytest.mark.asyncio
async def test_get_pending_requests():
    id1 = await db.create_request(1, "u1", "User 1", "key-1")
    id2 = await db.create_request(2, "u2", "User 2", "key-2")
    id3 = await db.create_request(3, "u3", "User 3", "key-3")

    pending = await db.get_pending_requests()
    assert len(pending) == 3

    # Reply to id2
    await db.update_request_reply(id2, "$10 remaining")

    pending_after = await db.get_pending_requests()
    assert len(pending_after) == 2
    assert [p["id"] for p in pending_after] == [id1, id3]
