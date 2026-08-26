import html
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command

from config import ADMIN_ID
import database as db
from keyboards.user_kb import get_main_menu_keyboard

router = Router()
# Filter all messages in this router to only ADMIN_ID
router.message.filter(F.from_user.id == ADMIN_ID)

@router.message(Command("admin"))
async def cmd_admin_help(message: Message) -> None:
    text = (
        "🛠 <b>Admin Commands & Instructions:</b>\n\n"
        "1️⃣ <b>Replying to Requests:</b>\n"
        "• Simply <b>swipe and reply</b> to any request notification message with the remaining credit amount. The bot will deliver it instantly to the user.\n"
        "• Or use: <code>/reply &lt;request_id&gt; &lt;credit_details&gt;</code>\n\n"
        "2️⃣ <b>Management Commands:</b>\n"
        "• <code>/pending</code> — List all requests awaiting review\n"
        "• <code>/stats</code> — View bot statistics and counters\n"
        "• <code>/admin</code> — Show this help message"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    stats = await db.get_stats()
    text = (
        "📊 <b>Bot Statistics:</b>\n\n"
        f"• <b>Total Requests:</b> {stats['total']}\n"
        f"• <b>Pending Requests:</b> {stats['pending']}\n"
        f"• <b>Replied Requests:</b> {stats['replied']}\n"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("pending"))
async def cmd_pending(message: Message) -> None:
    pending_list = await db.get_pending_requests(limit=10)
    if not pending_list:
        await message.answer("✅ <b>No pending requests!</b> All requests have been answered.", parse_mode="HTML")
        return

    text_parts = ["⏳ <b>Pending Requests:</b>\n"]
    for req in pending_list:
        user_info = html.escape(req["full_name"] or "Unknown")
        if req["username"]:
            user_info += f" (@{html.escape(req['username'])})"
        
        key_snippet = html.escape(req["api_key"])
        if len(key_snippet) > 25:
            key_snippet = key_snippet[:12] + "..." + key_snippet[-8:]
            
        text_parts.append(
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔖 <b>Request #{req['id']}</b>\n"
            f"👤 <b>User:</b> {user_info} (ID: <code>{req['user_id']}</code>)\n"
            f"🔑 <b>Key:</b> <code>{key_snippet}</code>\n"
            f"📅 <b>Time:</b> {req['created_at']}\n"
            f"👉 <i>Reply with: <code>/reply {req['id']} &lt;credit&gt;</code></i>"
        )
    
    text = "\n".join(text_parts)
    await message.answer(text, parse_mode="HTML")

@router.message(Command("reply"))
async def cmd_manual_reply(message: Message, bot: Bot) -> None:
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "⚠️ <b>Usage:</b> <code>/reply &lt;request_id&gt; &lt;credit_details&gt;</code>\n"
            "<i>Example: <code>/reply 1 $15.50 remaining</code></i>",
            parse_mode="HTML"
        )
        return

    try:
        request_id = int(parts[1])
    except ValueError:
        await message.answer("⚠️ Request ID must be an integer number.", parse_mode="HTML")
        return

    credit_text = parts[2].strip()
    await process_admin_response(message, request_id, credit_text, bot)

@router.message(F.reply_to_message)
async def handle_admin_reply_message(message: Message, bot: Bot) -> None:
    replied_msg_id = message.reply_to_message.message_id
    req = await db.get_request_by_admin_message(replied_msg_id)

    if not req:
        # Not a reply to a known request notification
        return

    credit_text = (message.text or "").strip()
    if not credit_text:
        await message.answer("⚠️ Please enter a text response with the remaining credit.", parse_mode="HTML")
        return

    await process_admin_response(message, req["id"], credit_text, bot)

async def process_admin_response(
    admin_msg: Message, request_id: int, credit_text: str, bot: Bot
) -> None:
    req = await db.get_request_by_id(request_id)
    if not req:
        await admin_msg.answer(f"❌ Request #{request_id} was not found in the database.", parse_mode="HTML")
        return

    if req["status"] == "replied":
        await admin_msg.answer(
            f"⚠️ <b>Request #{request_id} was already answered on {req['replied_at']}.</b>\n"
            f"Previous response: <code>{html.escape(req['response_credit'] or '')}</code>\n\n"
            f"Sending an update to the user...",
            parse_mode="HTML"
        )

    # Update in database
    await db.update_request_reply(request_id, credit_text)

    # Format notification for the user
    user_notification = (
        f"🎉 <b>API Key Credit Balance Update</b>\n\n"
        f"🔖 <b>Request ID:</b> #{request_id}\n"
        f"🔑 <b>API Key / Details:</b>\n"
        f"<code>{html.escape(req['api_key'])}</code>\n\n"
        f"💳 <b>Remaining Credit:</b>\n"
        f"<b>{html.escape(credit_text)}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Thank you for using our service!</i>"
    )

    try:
        await bot.send_message(
            chat_id=req["user_id"],
            text=user_notification,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        user_name_display = html.escape(req["full_name"] or "User")
        if req["username"]:
            user_name_display += f" (@{html.escape(req['username'])})"

        await admin_msg.answer(
            f"✅ <b>Delivered to user successfully!</b>\n\n"
            f"🔖 <b>Request:</b> #{request_id}\n"
            f"👤 <b>Recipient:</b> {user_name_display} (ID: <code>{req['user_id']}</code>)\n"
            f"💳 <b>Credit sent:</b> <code>{html.escape(credit_text)}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await admin_msg.answer(
            f"❌ <b>Error delivering message to user (ID: {req['user_id']}):</b>\n<code>{html.escape(str(e))}</code>\n"
            "<i>(The user may have blocked or stopped the bot)</i>",
            parse_mode="HTML"
        )
