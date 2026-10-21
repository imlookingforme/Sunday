import os
import asyncio
from typing import List, Dict, Any, Optional

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    import sqlite3
    HAS_AIOSQLITE = False

DEFAULT_DB_PATH = os.path.join("sunday", "data", "sunday.db")

class KnowledgeGraph:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._initialized = False

    async def _execute(self, query: str, params: tuple = ()):
        if HAS_AIOSQLITE:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, params) as cursor:
                    await db.commit()
                    return cursor.rowcount
        else:
            def sync_exec():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.rowcount
            return await asyncio.to_thread(sync_exec)

    async def _fetchall(self, query: str, params: tuple = ()):
        if HAS_AIOSQLITE:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        else:
            def sync_fetchall():
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
            return await asyncio.to_thread(sync_fetchall)

    async def initialize(self):
        if self._initialized:
            return

        await self._execute("""
            CREATE TABLE IF NOT EXISTS triples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                predicate TEXT,
                object TEXT,
                confidence REAL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(subject, predicate, object)
            )
        """)
        self._initialized = True

    async def add_triple(self, subject: str, predicate: str, object_: str, confidence: float = 1.0):
        await self.initialize()
        await self._execute(
            """INSERT OR IGNORE INTO triples (subject, predicate, object, confidence)
               VALUES (?, ?, ?, ?)""",
            (subject, predicate, object_, confidence)
        )

    async def query(self, subject: str = None, predicate: str = None, object_: str = None) -> List[Dict[str, Any]]:
        await self.initialize()

        conditions = []
        params = []

        if subject:
            conditions.append("subject = ?")
            params.append(subject)
        if predicate:
            conditions.append("predicate = ?")
            params.append(predicate)
        if object_:
            conditions.append("object = ?")
            params.append(object_)

        query_str = "SELECT * FROM triples"
        if conditions:
            query_str += " WHERE " + " AND ".join(conditions)

        return await self._fetchall(query_str, tuple(params))
