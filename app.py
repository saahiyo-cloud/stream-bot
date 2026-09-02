import asyncio
import logging
import sys
import os

# Ensure explicit asyncio event loop is set before importing hydrogram
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from aiohttp import web
from bot.config import Config
from bot.client import bot
from bot.database.db import db
from server.routes import setup_routes

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s - %(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("HF-Main")


async def main():
    logger.info("Initializing SQLite database...")
    await db.init_db()

    logger.info("Starting Telegram MTProto Stream Bot...")
    await bot.start()

    port = int(os.getenv("PORT", "7860") or 7860)
    bind_address = "0.0.0.0"

    logger.info(f"Starting async aiohttp streaming server on {bind_address}:{port}...")
    app = web.Application(client_max_size=1024 * 1024 * 10)
    setup_routes(app)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, bind_address, port)
    await site.start()

    public_url = Config.get_public_url()
    logger.info("=" * 60)
    logger.info("⚡ STREAM BOT IS NOW ONLINE ON HUGGING FACE SPACES!")
    logger.info(f"🤖 Bot Username   : @{bot.me.username if bot.me else 'unknown'}")
    logger.info(f"🌐 Backend Server : http://{bind_address}:{port}")
    logger.info(f"🔗 Public Domain  : {public_url}")
    logger.info(f"📦 Storage Channel: {Config.BIN_CHANNEL}")
    logger.info("=" * 60)

    # Keep running forever
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot shutting down...")
    except Exception as e:
        logger.critical(f"Fatal error in main loop: {e}", exc_info=True)
        sys.exit(1)
