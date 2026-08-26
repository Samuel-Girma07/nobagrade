import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

from config import BOT_TOKEN, PROXY_URL
import database as db
from handlers import user, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("nobabot")

async def set_bot_commands(bot: Bot) -> None:
    try:
        commands = [
            BotCommand(command="start", description="Start the bot and open the main menu"),
            BotCommand(command="help", description="How to check your API key balance"),
        ]
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")

async def wait_for_connection(bot: Bot) -> None:
    delay = 3
    while True:
        try:
            logger.info("Attempting to connect to Telegram API (api.telegram.org)...")
            bot_info = await bot.get_me()
            logger.info(f" Connected successfully! Bot: @{bot_info.username} (ID: {bot_info.id})")
            return
        except Exception as e:
            logger.warning(
                f"Connection failed: {e}\n"
                f"Retrying in {delay} seconds... (If your network restricts Telegram, please enable your VPN / Proxy)"
            )
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 30)

async def main() -> None:
    logger.info("Initializing database...")
    await db.init_db()

    session = None
    if PROXY_URL:
        logger.info(f"Using configured proxy: {PROXY_URL}")
        session = AiohttpSession(proxy=PROXY_URL)

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Register routers
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Retry until network is available (e.g. user starts VPN or proxy)
    await wait_for_connection(bot)
    await set_bot_commands(bot)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Bot is now actively listening for messages...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot terminated by user.")
