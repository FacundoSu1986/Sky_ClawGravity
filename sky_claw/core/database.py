import aiosqlite
import json
import logging

logger = logging.getLogger("SkyClaw.Database")

class DatabaseAgent:
    def __init__(self, db_path: str = "sky_claw_state.db"):
        self.db_path = db_path

    async def init_db(self):
        """Inicializa esquemas con modo WAL para alta concurrencia."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scraper_state (
                    domain TEXT PRIMARY KEY,
                    cookies TEXT,
                    failures INTEGER DEFAULT 0,
                    locked_until REAL DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at REAL
                )
            """)
            await db.commit()
            logger.info("Base de datos SQLite inicializada en modo WAL (incluye agent_memory).")

    async def get_circuit_breaker_state(self, domain: str) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM scraper_state WHERE domain = ?", (domain,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else {"failures": 0, "locked_until": 0}

    async def update_circuit_breaker(self, domain: str, failures: int, locked_until: float):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO scraper_state (domain, failures, locked_until) 
                VALUES (?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET 
                failures=excluded.failures, locked_until=excluded.locked_until
            """, (domain, failures, locked_until))
            await db.commit()

    async def get_memory(self, key: str) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM agent_memory WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_memory(self, key: str, value: str, updated_at: float):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO agent_memory (key, value, updated_at) 
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET 
                value=excluded.value, updated_at=excluded.updated_at
            """, (key, value, updated_at))
            await db.commit()
