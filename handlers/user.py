import html
from datetime import datetime, timezone
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
import database as db
from handlers.states import CheckCreditStates
from keyboards.user_kb import (
    get_main_menu_keyboard,
    get_cancel_keyboard,
    get_back_to_menu_keyboard,
)

router = Router()

def get_user_display(user) -> str:
    name = html.escape(user.full_name or "Unknown")
    if user.username:
        return f'<a href="tg://user?id={user.id}">{name}</a> (@{html.escape(user.username)})'
    return f'<a href="tg://user?id={user.id}">{name}</a>'

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_name = html.escape(message.from_user.first_name or "there")
    text = (
        f"👋 <b>Hello, {user_name}!</b>\n\n"
        "Welcome to the <b>API Key Credit Checker Bot</b>.\n\n"
        "Here you can submit your API key to check its remaining credit/balance. "
        "Your request will be reviewed by our administrator and the balance details will be sent right back to you.\n\n"
        "👇 <i>Select an option below to begin:</i>"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")

@router.message(Command("help"))
@router.callback_query(F.data == "show_help")
async def show_help(event: Message | CallbackQuery, state: FSMContext) -> None:
    text = (
        "ℹ️ <b>How it works:</b>\n\n"
        "1️⃣ Tap <b>💳 Check Remaining Credit</b>.\n"
        "2️⃣ Send your API key or key identifier to the bot.\n"
        "3️⃣ Your request is forwarded to the administrator.\n"
        "4️⃣ The administrator checks the remaining credit and replies.\n"
        "5️⃣ You will instantly receive a notification with your updated balance!\n\n"
        "💡 <i>You can also view your request history anytime with <b>📜 My Recent Checks</b>.</i>"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(
            text, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML"
        )
    else:
        await event.answer(
            text, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML"
        )

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    text = (
        "🏠 <b>Main Menu</b>\n\n"
        "Please select what you would like to do:"
    )
    await callback.message.edit_text(
        text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML"
    )

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Action cancelled.")
    text = "❌ <b>Action cancelled.</b>\n\nReturning to the main menu."
    await callback.message.edit_text(
        text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML"
    )

@router.callback_query(F.data == "check_credit")
async def start_check_credit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(CheckCreditStates.waiting_for_api_key)
    text = (
        "🔑 <b>Submit API Key for Balance Check</b>\n\n"
        "Please send your <b>API key</b> (or key identifier / account details) as a text message below.\n\n"
        "<i>Click Cancel if you wish to go back.</i>"
    )
    await callback.message.edit_text(
        text, reply_markup=get_cancel_keyboard(), parse_mode="HTML"
    )

@router.message(CheckCreditStates.waiting_for_api_key)
async def process_api_key_submission(message: Message, state: FSMContext, bot: Bot) -> None:
    api_key_text = (message.text or "").strip()
    if not api_key_text:
        await message.answer(
            "⚠️ Please send a valid text message containing the API key.",
            reply_markup=get_cancel_keyboard()
        )
        return

    if len(api_key_text) > 1000:
        await message.answer(
            "⚠️ The submitted key is too long (maximum 1,000 characters). Please send a valid API key.",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.clear()

    user = message.from_user
    username = user.username if user.username else None
    full_name = user.full_name or "Unknown"

    # Save to database
    request_id = await db.create_request(
        user_id=user.id,
        username=username,
        full_name=full_name,
        api_key=api_key_text
    )

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    user_display = get_user_display(user)

    admin_notification = (
        f"📩 <b>New API Key Credit Request #{request_id}</b>\n\n"
        f"👤 <b>From:</b> {user_display}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"📅 <b>Time:</b> {now_utc}\n\n"
        f"🔑 <b>API Key / Details:</b>\n"
        f"<code>{html.escape(api_key_text)}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 <b>How to respond:</b>\n"
        f"👉 <i>Swipe / Reply directly to this message with the remaining credit amount to send it to the user.</i>\n"
        f"<i>Or use: <code>/reply {request_id} &lt;credit_amount&gt;</code></i>"
    )

    try:
        admin_msg = await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_notification,
            parse_mode="HTML"
        )
        await db.set_admin_message_id(request_id, admin_msg.message_id)
    except Exception:
        user_reply = (
            "⚠️ <b>Notice:</b> Your request has been saved, but we encountered an issue forwarding it to the admin.\n"
            "Please try again later or contact support."
        )
        await message.answer(user_reply, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
        return

    user_reply = (
        f"✅ <b>Request #{request_id} Submitted!</b>\n\n"
        f"🔑 <b>Submitted Key:</b> <code>{html.escape(api_key_text)}</code>\n\n"
        "⏳ <i>Your request has been forwarded to the administrator. You will receive a direct notification as soon as your remaining credit is verified.</i>"
    )
    await message.answer(user_reply, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "my_history")
async def show_user_history(callback: CallbackQuery) -> None:
    await callback.answer()
    requests = await db.get_user_recent_requests(callback.from_user.id, limit=5)
    
    if not requests:
        text = (
            "📜 <b>Your Recent Requests</b>\n\n"
            "You haven't submitted any API key checks yet.\n\n"
            "Click <b>💳 Check Remaining Credit</b> to submit one!"
        )
        await callback.message.edit_text(
            text, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML"
        )
        return

    text_parts = ["📜 <b>Your Recent Credit Requests:</b>\n"]
    for req in requests:
        req_id = req["id"]
        key_snippet = html.escape(req["api_key"])
        if len(key_snippet) > 20:
            key_snippet = key_snippet[:10] + "..." + key_snippet[-6:]
        
        status = req["status"]
        if status == "replied":
            status_badge = "🟢 <b>Replied</b>"
            credit_info = f"💳 <b>Credit:</b> {html.escape(req['response_credit'] or 'N/A')}\n"
        elif status == "pending":
            status_badge = "🟡 <b>Pending Admin Review</b>"
            credit_info = ""
        else:
            status_badge = f"⚪ {html.escape(status.capitalize())}"
            credit_info = ""

        text_parts.append(
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔖 <b>Request #{req_id}</b> — {status_badge}\n"
            f"🔑 <b>Key:</b> <code>{key_snippet}</code>\n"
            f"📅 <b>Date:</b> {req['created_at']}\n"
            f"{credit_info}"
        )

    text = "\n".join(text_parts)
    await callback.message.edit_text(
        text, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML"
    )
