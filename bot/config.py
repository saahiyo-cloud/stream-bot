import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram API Credentials (with defaults for cloud runners)
    API_ID = int(os.getenv("API_ID", "36818500") or 36818500)
    API_HASH = os.getenv("API_HASH", "2be9ab61d199c2e7a09c29c2d866f84d") or "2be9ab61d199c2e7a09c29c2d866f84d"
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8903766051:AAFoaxItE4t8tTDld2VPvQliurHAL24fIzk") or "8903766051:AAFoaxItE4t8tTDld2VPvQliurHAL24fIzk"

    # Multi-client worker tokens (comma-separated list for load balancing)
    MULTI_TOKENS = [
        token.strip()
        for token in os.getenv("MULTI_TOKENS", "").split(",")
        if token.strip()
    ]

    # Channel for storing media files (Required for persistence)
    # Must be an integer like -1001234567890
    BIN_CHANNEL = int(os.getenv("BIN_CHANNEL", "-1004405063378") or 0)

    # Server Network Settings
    PORT = int(os.getenv("PORT", "7860") or 7860)
    BIND_ADDRESS = os.getenv("BIND_ADDRESS", "0.0.0.0")

    # Public URLs for Link Generation
    SERVER_URL = os.getenv("SERVER_URL", "https://saahiyo-stream-bot.hf.space").rstrip("/")
    WORKER_URL = os.getenv("WORKER_URL", "https://dl.shakir-ansarii075.workers.dev").rstrip("/")

    # The effective public base URL shown to users (Worker URL takes precedence if configured)
    @classmethod
    def get_public_url(cls):
        return cls.WORKER_URL if cls.WORKER_URL else cls.SERVER_URL

    # Optional Channel Branding / Updates (leave empty if none)
    UPDATES_CHANNEL = os.getenv("UPDATES_CHANNEL", "").strip()
    FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "").strip()

    # Bot Owner
    OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "stream_bot.db")

    # Streaming Buffer Settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", str(1024 * 1024)))  # 1 MB optimal chunk size
    CACHE_SIZE = int(os.getenv("CACHE_SIZE", "100"))

    # Hash prefix for vanity URLs (e.g. stream-...)
    HASH_PREFIX = os.getenv("HASH_PREFIX", "stream-")
