import os
import asyncio
import logging
import sys

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
from server.app import create_web_app

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s - %(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("HF-Main")


async def main():
    logger.info("Initializing SQLite database...")
    await db.init_db()

    logger.info("Starting Telegram MTProto Stream Bot on Hugging Face...")
    await bot.start()

    # Hugging Face default port is 7860
    port = int(os.getenv("PORT", "7860"))
    bind_address = "0.0.0.0"

    app = await create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, bind_address, port)
    await site.start()

    public_url = Config.get_public_url()
    logger.info("=" * 60)
    logger.info("⚡ STREAM BOT IS NOW ONLINE ON HUGGING FACE SPACES!")
    logger.info(f"🤖 Bot Username   : @{bot.me.username if bot.me else 'unknown'}")
    logger.info(f"🌐 Backend Port   : {port}")
    logger.info(f"🔗 Public URL     : {public_url}")
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
