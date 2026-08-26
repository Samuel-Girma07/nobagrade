import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import User, Chat, Message, CallbackQuery

from config import ADMIN_ID
import database as db
from handlers.states import CheckCreditStates
from handlers import user as user_handlers
from handlers import admin as admin_handlers

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(tmp_path, monkeypatch):
    test_db_file = tmp_path / "test_handlers_bot.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_file)
    await db.init_db()
    yield test_db_file

@pytest.fixture
def memory_storage():
    return MemoryStorage()

def create_fsm_context(storage, bot_id=1, chat_id=100, user_id=100):
    key = StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id)
    return FSMContext(storage=storage, key=key)

@pytest.mark.asyncio
async def test_cmd_start(memory_storage):
    user = User(id=123, is_bot=False, first_name="Alice", username="alice_tg")
    chat = Chat(id=123, type="private")
    message = MagicMock(spec=Message)
    message.from_user = user
    message.chat = chat
    message.answer = AsyncMock()

    state = create_fsm_context(memory_storage, user_id=123, chat_id=123)
    await user_handlers.cmd_start(message, state)

    message.answer.assert_called_once()
    args, kwargs = message.answer.call_args
    assert "Hello, Alice!" in args[0]
    assert kwargs.get("reply_markup") is not None
    assert await state.get_state() is None

@pytest.mark.asyncio
async def test_start_check_credit_flow(memory_storage):
    user = User(id=123, is_bot=False, first_name="Alice")
    chat = Chat(id=123, type="private")
    
    # User clicks "Check Remaining Credit"
    callback_msg = MagicMock(spec=Message)
    callback_msg.edit_text = AsyncMock()
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = user
    callback.message = callback_msg
    callback.answer = AsyncMock()

    state = create_fsm_context(memory_storage, user_id=123, chat_id=123)
    await user_handlers.start_check_credit(callback, state)

    assert await state.get_state() == CheckCreditStates.waiting_for_api_key.state
    callback.answer.assert_called_once()
    callback_msg.edit_text.assert_called_once()

    # User submits API key
    submit_msg = MagicMock(spec=Message)
    submit_msg.from_user = user
    submit_msg.chat = chat
    submit_msg.text = "sk-live-abcdef123456"
    submit_msg.answer = AsyncMock()

    mock_bot = MagicMock()
    admin_bot_msg = MagicMock(spec=Message)
    admin_bot_msg.message_id = 7777
    mock_bot.send_message = AsyncMock(return_value=admin_bot_msg)

    await user_handlers.process_api_key_submission(submit_msg, state, mock_bot)

    # State cleared
    assert await state.get_state() is None
    # User received confirmation
    submit_msg.answer.assert_called_once()
    user_reply_text = submit_msg.answer.call_args[0][0]
    assert "Request #1 Submitted!" in user_reply_text

    # Admin was notified
    mock_bot.send_message.assert_called_once()
    admin_call_kwargs = mock_bot.send_message.call_args[1]
    assert admin_call_kwargs["chat_id"] == ADMIN_ID
    assert "sk-live-abcdef123456" in admin_call_kwargs["text"]

    # Verify DB record
    req = await db.get_request_by_id(1)
    assert req is not None
    assert req["admin_message_id"] == 7777
    assert req["status"] == "pending"

@pytest.mark.asyncio
async def test_admin_reply_and_delivery():
    # Setup request in DB
    req_id = await db.create_request(
        user_id=12345,
        username="test_client",
        full_name="Client Name",
        api_key="sk-live-test999"
    )
    admin_msg_id = 8888
    await db.set_admin_message_id(req_id, admin_msg_id)

    # Admin replies to the forwarded message
    admin_user = User(id=ADMIN_ID, is_bot=False, first_name="Admin")
    replied_message = MagicMock(spec=Message)
    replied_message.message_id = admin_msg_id

    admin_reply_msg = MagicMock(spec=Message)
    admin_reply_msg.from_user = admin_user
    admin_reply_msg.reply_to_message = replied_message
    admin_reply_msg.text = "$120.00 Remaining (Valid until Dec 2026)"
    admin_reply_msg.answer = AsyncMock()

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()

    await admin_handlers.handle_admin_reply_message(admin_reply_msg, mock_bot)

    # User notification verified
    mock_bot.send_message.assert_called_once()
    user_call_kwargs = mock_bot.send_message.call_args[1]
    assert user_call_kwargs["chat_id"] == 12345
    assert "$120.00 Remaining" in user_call_kwargs["text"]

    # Admin received success confirmation
    admin_reply_msg.answer.assert_called_once()
    assert "Delivered to user successfully!" in admin_reply_msg.answer.call_args[0][0]

    # Verify DB updated
    updated_req = await db.get_request_by_id(req_id)
    assert updated_req["status"] == "replied"
    assert updated_req["response_credit"] == "$120.00 Remaining (Valid until Dec 2026)"

@pytest.mark.asyncio
async def test_admin_manual_reply_command():
    req_id = await db.create_request(
        user_id=67890,
        username="manual_user",
        full_name="Manual User",
        api_key="sk-manual-111"
    )

    admin_user = User(id=ADMIN_ID, is_bot=False, first_name="Admin")
    cmd_msg = MagicMock(spec=Message)
    cmd_msg.from_user = admin_user
    cmd_msg.text = f"/reply {req_id} 500 API calls remaining"
    cmd_msg.answer = AsyncMock()

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()

    await admin_handlers.cmd_manual_reply(cmd_msg, mock_bot)

    mock_bot.send_message.assert_called_once()
    assert mock_bot.send_message.call_args[1]["chat_id"] == 67890
    assert "500 API calls remaining" in mock_bot.send_message.call_args[1]["text"]

    cmd_msg.answer.assert_called_once()
    assert "Delivered to user successfully!" in cmd_msg.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_admin_stats_and_pending_commands():
    await db.create_request(1, "u1", "U1", "key-1")
    req2_id = await db.create_request(2, "u2", "U2", "key-2")
    await db.update_request_reply(req2_id, "$10 remaining")

    admin_user = User(id=ADMIN_ID, is_bot=False, first_name="Admin")

    # Test /stats
    stats_msg = MagicMock(spec=Message)
    stats_msg.from_user = admin_user
    stats_msg.answer = AsyncMock()
    await admin_handlers.cmd_stats(stats_msg)

    stats_text = stats_msg.answer.call_args[0][0]
    assert "Total Requests:</b> 2" in stats_text
    assert "Pending Requests:</b> 1" in stats_text
    assert "Replied Requests:</b> 1" in stats_text

    # Test /pending
    pending_msg = MagicMock(spec=Message)
    pending_msg.from_user = admin_user
    pending_msg.answer = AsyncMock()
    await admin_handlers.cmd_pending(pending_msg)

    pending_text = pending_msg.answer.call_args[0][0]
    assert "Pending Requests:" in pending_text
    assert "Request #1" in pending_text
