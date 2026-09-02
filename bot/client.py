import logging
import asyncio
from hydrogram import Client
from hydrogram.errors import FloodWait
from bot.config import Config

logger = logging.getLogger(__name__)

# Ensure event loop exists before Client/Dispatcher initialization on Python 3.10+
try:
    _loop = asyncio.get_event_loop()
except RuntimeError:
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)


class StreamBot(Client):
    def __init__(self):
        super().__init__(
            name="StreamBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            session_string=Config.SESSION_STRING if Config.SESSION_STRING else None,
            plugins=dict(root="bot/handlers"),
            sleep_threshold=15,
            workers=32
        )
        self.worker_clients = []
        self._worker_index = 0
        self.username = None
        self.me = None

    async def start(self):
        logger.info("Starting primary Telegram bot client...")
        while True:
            try:
                await super().start()
                break
            except FloodWait as e:
                logger.warning(f"Telegram login FloodWait: sleeping {e.value + 2} seconds to satisfy Telegram cooldown...")
                await asyncio.sleep(e.value + 2)

        self.me = await self.get_me()
        self.username = self.me.username
        logger.info(f"Bot started successfully as @{self.username} (ID: {self.me.id})")

        # Export session string for persistent zero-cooldown logins across redeployments
        if not Config.SESSION_STRING:
            try:
                exported = await self.export_session_string()
                logger.info(f"💡 SESSION_STRING generated: {exported}")
                logger.info("   Add SESSION_STRING to Railway Variables to eliminate login cooldowns permanently.")
            except Exception as exp_err:
                logger.debug(f"Could not export session: {exp_err}")

        # Initialize secondary worker clients for load-balancing chunk streaming
        if Config.MULTI_TOKENS:
            logger.info(f"Initializing {len(Config.MULTI_TOKENS)} multi-client workers...")
            for idx, token in enumerate(Config.MULTI_TOKENS, start=1):
                try:
                    worker = Client(
                        name=f"WorkerClient_{idx}",
                        api_id=Config.API_ID,
                        api_hash=Config.API_HASH,
                        bot_token=token,
                        no_updates=True,
                        sleep_threshold=15,
                        workers=16
                    )
                    while True:
                        try:
                            await worker.start()
                            break
                        except FloodWait as fe:
                            logger.warning(f"Worker {idx} login FloodWait: sleeping {fe.value + 2}s...")
                            await asyncio.sleep(fe.value + 2)

                    worker_me = await worker.get_me()
                    self.worker_clients.append(worker)
                    logger.info(f"Worker {idx} initialized as @{worker_me.username}")
                except Exception as e:
                    logger.error(f"Failed to initialize Worker {idx}: {e}")

        logger.info(f"Active worker pool size: {len(self.worker_clients) + 1} (including main client)")

    async def stop(self, *args):
        logger.info("Stopping bot and worker clients...")
        for worker in self.worker_clients:
            try:
                await worker.stop()
            except Exception as e:
                logger.error(f"Error stopping worker: {e}")
        await super().stop()
        logger.info("All clients stopped.")

    def get_stream_client(self):
        """
        Returns a client from the pool using round-robin to distribute MTProto chunk streaming load.
        """
        if not self.worker_clients:
            return self

        # Round robin over all available clients
        all_clients = [self] + self.worker_clients
        client = all_clients[self._worker_index % len(all_clients)]
        self._worker_index += 1
        return client


bot = StreamBot()
