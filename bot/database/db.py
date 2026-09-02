import aiosqlite
import time
from bot.config import Config


class Database:
    def __init__(self, db_path=Config.DATABASE_URL):
        self.db_path = db_path
        self._conn = None

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT UNIQUE NOT NULL,
                    message_id INTEGER NOT NULL,
                    file_name TEXT,
                    file_size INTEGER NOT NULL,
                    mime_type TEXT,
                    file_unique_id TEXT,
                    user_id INTEGER,
                    created_at INTEGER,
                    views_count INTEGER DEFAULT 0,
                    downloads_count INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    joined_at INTEGER
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_file_hash ON files(file_hash)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_file_unique_id ON files(file_unique_id)")
            await db.commit()

    async def add_file(self, file_hash: str, message_id: int, file_name: str, file_size: int,
                       mime_type: str, file_unique_id: str, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT OR REPLACE INTO files 
                (file_hash, message_id, file_name, file_size, mime_type, file_unique_id, user_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (file_hash, message_id, file_name, file_size, mime_type, file_unique_id, user_id, int(time.time())))
            await db.commit()
            return cursor.lastrowid

    async def get_file_by_hash(self, file_hash: str):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM files WHERE file_hash = ?", (file_hash,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def get_file_by_unique_id(self, file_unique_id: str):
        if not file_unique_id:
            return None
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM files WHERE file_unique_id = ? ORDER BY id DESC LIMIT 1", (file_unique_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def increment_views(self, file_hash: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE files SET views_count = views_count + 1 WHERE file_hash = ?", (file_hash,))
            await db.commit()

    async def increment_downloads(self, file_hash: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE files SET downloads_count = downloads_count + 1 WHERE file_hash = ?", (file_hash,))
            await db.commit()

    async def add_user(self, user_id: int, first_name: str, username: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, first_name, username, joined_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, first_name, username, int(time.time())))
            await db.commit()

    async def get_stats(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM files")
            total_files = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT SUM(file_size) FROM files")
            total_size = (await cursor.fetchone())[0] or 0

            return {
                "total_files": total_files,
                "total_users": total_users,
                "total_size": total_size
            }


db = Database()
