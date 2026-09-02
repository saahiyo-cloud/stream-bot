import os
from dotenv import load_dotenv

load_dotenv()


def _get_int(key: str, default: int = 0) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    cleaned = str(val).strip().strip('"\'')
    try:
        return int(cleaned) if cleaned else default
    except ValueError:
        return default


class Config:
    # Telegram API Credentials (required - set via environment variables)
    API_ID = _get_int("API_ID", 0)
    API_HASH = os.getenv("API_HASH", "").strip().strip('"\'')
    BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"\'')
    SESSION_STRING = os.getenv("SESSION_STRING", "").strip().strip('"\'')

    # Multi-client worker tokens (comma-separated list for load balancing)
    MULTI_TOKENS = [
        token.strip().strip('"\'')
        for token in os.getenv("MULTI_TOKENS", "").split(",")
        if token.strip().strip('"\'')
    ]

    # Channel for storing media files (Required for persistence)
    # Must be an integer like -1001234567890
    BIN_CHANNEL = _get_int("BIN_CHANNEL", 0)

    # Server Network Settings
    PORT = _get_int("PORT", 7860)
    BIND_ADDRESS = os.getenv("BIND_ADDRESS", "0.0.0.0").strip()

    # Public URLs for Link Generation
    SERVER_URL = os.getenv("SERVER_URL", "").strip().strip('"\'').rstrip("/")
    WORKER_URL = os.getenv("WORKER_URL", "").strip().strip('"\'').rstrip("/")

    # The effective public base URL shown to users
    @classmethod
    def get_public_url(cls):
        return cls.WORKER_URL if cls.WORKER_URL else cls.SERVER_URL

    # Optional Channel Branding / Updates (leave empty if none)
    UPDATES_CHANNEL = os.getenv("UPDATES_CHANNEL", "").strip()
    FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "").strip()

    # Bot Owner
    OWNER_ID = _get_int("OWNER_ID", 0)

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "stream_bot.db").strip().strip('"\'')

    # Streaming Buffer Settings
    CHUNK_SIZE = _get_int("CHUNK_SIZE", 1024 * 1024)  # 1 MB optimal chunk size
    CACHE_SIZE = _get_int("CACHE_SIZE", 100)

    # Hash prefix for vanity URLs (e.g. stream-...)
    HASH_PREFIX = os.getenv("HASH_PREFIX", "stream-").strip()

