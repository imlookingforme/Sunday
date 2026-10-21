"""Pattern Learner - Tracks user intent events in SQLite and mines temporal/sequential habits."""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any

try:
    import aiosqlite

    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

logger = logging.getLogger(__name__)

DEFAULT_INTENT_DB = os.path.join("sunday", "data", "intent_patterns.db")


class PatternLearner:
    """Logs user intents and uncovers temporal and sequential usage patterns."""

    def __init__(self, db_path: str = DEFAULT_INTENT_DB):
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

    async def _fetchall(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
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
        """Initialize database tables for intent tracking and habit discovery."""
        if self._initialized:
            return

        await self._execute("""
            CREATE TABLE IF NOT EXISTS intent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_input TEXT,
                classified_intent TEXT,
                confidence REAL,
                final_intent TEXT,
                time_bucket TEXT,
                day_of_week INTEGER,
                hour INTEGER,
                was_suggestion INTEGER DEFAULT 0,
                suggestion_accepted INTEGER DEFAULT NULL
            )
        """)
        self._initialized = True

    def _get_time_bucket(self, hour: int) -> str:
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"

    async def log_intent_event(
        self,
        user_input: str,
        classified_intent: str,
        confidence: float,
        final_intent: str,
        was_suggestion: bool = False,
        suggestion_accepted: bool | None = None,
    ):
        """Record classified user interaction event."""
        await self.initialize()
        now = datetime.now()
        time_bucket = self._get_time_bucket(now.hour)
        day_of_week = now.weekday()
        accepted_int = (
            1 if suggestion_accepted is True else (0 if suggestion_accepted is False else None)
        )

        await self._execute(
            """INSERT INTO intent_events
               (user_input, classified_intent, confidence, final_intent, time_bucket, day_of_week, hour, was_suggestion, suggestion_accepted)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_input,
                classified_intent,
                confidence,
                final_intent,
                time_bucket,
                day_of_week,
                now.hour,
                1 if was_suggestion else 0,
                accepted_int,
            ),
        )

    async def get_frequent_intents_by_time(self, hour: int | None = None) -> list[dict[str, Any]]:
        """Mines what intents the user usually triggers at a given hour or time bucket."""
        await self.initialize()
        target_hour = hour if hour is not None else datetime.now().hour
        time_bucket = self._get_time_bucket(target_hour)

        query = """
            SELECT final_intent, COUNT(*) as frequency
            FROM intent_events
            WHERE time_bucket = ?
            GROUP BY final_intent
            ORDER BY frequency DESC
            LIMIT 5
        """
        return await self._fetchall(query, (time_bucket,))

    async def get_sequential_pattern(self, current_intent: str) -> str | None:
        """Finds what intent commonly follows the current intent using sequential window analysis."""
        await self.initialize()
        query = """
            WITH sequenced AS (
                SELECT final_intent,
                       LEAD(final_intent) OVER (ORDER BY id) as next_intent
                FROM intent_events
            )
            SELECT next_intent, COUNT(*) as frequency
            FROM sequenced
            WHERE final_intent = ? AND next_intent IS NOT NULL
            GROUP BY next_intent
            ORDER BY frequency DESC
            LIMIT 1
        """
        rows = await self._fetchall(query, (current_intent,))
        if rows and rows[0]["frequency"] >= 2:
            return rows[0]["next_intent"]
        return None

    async def get_total_events_count(self) -> int:
        """Returns total count of tracked events."""
        await self.initialize()
        rows = await self._fetchall("SELECT COUNT(*) as count FROM intent_events")
        return rows[0]["count"] if rows else 0
