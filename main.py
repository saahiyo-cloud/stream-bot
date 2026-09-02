import asyncio
import logging
import sys

# Ensure an active event loop exists on MainThread before module imports on Python 3.10+
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from aiohttp import web
from hydrogram import idle

from bot.config import Config
from bot.client import bot
from bot.database.db import db
from server.app import create_web_server

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s - %(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("Main")


async def main():
    if not Config.API_ID or not Config.API_HASH or not Config.BOT_TOKEN:
        logger.error(
            "CRITICAL: Missing API_ID, API_HASH, or BOT_TOKEN in environment variables.\n"
            "Please check your .env file or environment settings before running the bot."
        )
        sys.exit(1)

    logger.info("Initializing SQLite database...")
    await db.init_db()

    logger.info("Starting Telegram MTProto Stream Bot...")
    await bot.start()

    logger.info(f"Starting async aiohttp streaming server on {Config.BIND_ADDRESS}:{Config.PORT}...")
    runner = await create_web_server()
    site = web.TCPSite(runner, Config.BIND_ADDRESS, Config.PORT)
    await site.start()

    public_url = Config.get_public_url()
    logger.info("=" * 60)
    logger.info(f"⚡ STREAM BOT IS NOW ONLINE & READY!")
    logger.info(f"🤖 Bot Username   : @{bot.username}")
    logger.info(f"🌐 Backend Server : http://{Config.BIND_ADDRESS}:{Config.PORT}")
    logger.info(f"🔗 Public Domain  : {public_url}")
    logger.info(f"📦 Storage Channel: {Config.BIN_CHANNEL or 'Direct Messages'}")
    logger.info("=" * 60)

    try:
        await idle()
    finally:
        logger.info("Shutting down services gracefully...")
        await bot.stop()
        await runner.cleanup()
        logger.info("All services shut down.")


if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution terminated by user.")

