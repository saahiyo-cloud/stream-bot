import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram API Credentials
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    # Multi-client worker tokens (comma-separated list for load balancing)
    MULTI_TOKENS = [
        token.strip()
        for token in os.getenv("MULTI_TOKENS", "").split(",")
        if token.strip()
    ]

    # Channel for storing media files (Required for persistence)
    # Must be an integer like -1001234567890
    BIN_CHANNEL = int(os.getenv("BIN_CHANNEL", "0"))

    # Server Network Settings
    PORT = int(os.getenv("PORT", "8080"))
    BIND_ADDRESS = os.getenv("BIND_ADDRESS", "0.0.0.0")

    # Public URLs for Link Generation
    # SERVER_URL is the direct backend origin
    SERVER_URL = os.getenv("SERVER_URL", f"http://localhost:{PORT}").rstrip("/")
    # WORKER_URL is the Cloudflare Worker proxy domain (e.g. https://dl.yourname.workers.dev)
    WORKER_URL = os.getenv("WORKER_URL", "").rstrip("/")

    # The effective public base URL shown to users (Worker URL takes precedence if configured)
    @classmethod
    def get_public_url(cls):
        return cls.WORKER_URL if cls.WORKER_URL else cls.SERVER_URL

    # Optional Channel Branding / Updates (leave empty if none)
    UPDATES_CHANNEL = os.getenv("UPDATES_CHANNEL", "").strip()
    FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "").strip()  # e.g., "@MyChannel" for force-sub

    # Bot Owner
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "stream_bot.db")

    # Streaming Buffer Settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1024 * 1024))  # 1 MB optimal chunk size
    CACHE_SIZE = int(os.getenv("CACHE_SIZE", "100"))

    # Hash prefix for vanity URLs (e.g. stream-...)
    HASH_PREFIX = os.getenv("HASH_PREFIX", "stream-")

