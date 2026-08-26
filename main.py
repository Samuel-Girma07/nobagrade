import asyncio
import logging
import os
import sys
from aiohttp import web
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

async def health_check(request: web.Request) -> web.Response:
    stats = await db.get_stats()
    return web.json_response({
        "status": "online",
        "service": "nobabot",
        "stats": stats
    })

async def start_web_server(port: int) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/healthz", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check HTTP server started on port {port}")
    return runner

async def main() -> None:
    logger.info("Initializing database...")
    await db.init_db()

    # If running on a cloud host with PORT (e.g. Render Web Service)
    port_env = os.getenv("PORT")
    web_runner = None
    if port_env:
        try:
            web_runner = await start_web_server(int(port_env))
        except Exception as e:
            logger.warning(f"Could not start health check HTTP server: {e}")

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
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot terminated by user.")
