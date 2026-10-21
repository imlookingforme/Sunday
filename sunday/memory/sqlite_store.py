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

class SQLiteStore:
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

        tables = [
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                role TEXT,
                content TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                tags TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                summary TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                entry TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS custom_agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                system_prompt TEXT NOT NULL,
                model TEXT DEFAULT 'llama3.1',
                allowed_tools TEXT NOT NULL,
                memory_namespace TEXT NOT NULL,
                config_json TEXT DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        ]

        for table_query in tables:
            await self._execute(table_query)

        self._initialized = True

    async def add_message(self, session_id: str, role: str, content: str):
        await self.initialize()
        await self._execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )

    async def get_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        await self.initialize()
        return await self._fetchall(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit)
        )

    async def set_fact(self, key: str, value: str, tags: List[str] = None):
        await self.initialize()
        tags_str = ",".join(tags) if tags else ""
        await self._execute(
            "INSERT OR REPLACE INTO facts (key, value, tags) VALUES (?, ?, ?)",
            (key, value, tags_str)
        )

    async def get_fact(self, key: str) -> Optional[str]:
        await self.initialize()
        res = await self._fetchall("SELECT value FROM facts WHERE key = ?", (key,))
        return res[0]['value'] if res else None

    async def get_facts_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        await self.initialize()
        return await self._fetchall("SELECT * FROM facts WHERE tags LIKE ?", (f"%{tag}%",))

    async def add_session_summary(self, session_id: str, summary: str):
        await self.initialize()
        await self._execute(
            "INSERT OR REPLACE INTO summaries (session_id, summary) VALUES (?, ?)",
            (session_id, summary)
        )

    async def add_note(self, title: str, content: str):
        await self.initialize()
        await self._execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)",
            (title, content)
        )

    async def add_journal_entry(self, date: str, entry: str):
        await self.initialize()
        await self._execute(
            "INSERT INTO journal (date, entry) VALUES (?, ?)",
            (date, entry)
        )

    async def set_profile_data(self, key: str, value: str):
        await self.initialize()
        await self._execute(
            "INSERT OR REPLACE INTO user_profile (key, value) VALUES (?, ?)",
            (key, value)
        )

    async def get_profile_data(self, key: str) -> Optional[str]:
        await self.initialize()
        res = await self._fetchall("SELECT value FROM user_profile WHERE key = ?", (key,))
        return res[0]['value'] if res else None

    async def save_custom_agent(self, agent_data: Dict[str, Any]) -> None:
        await self.initialize()
        import json
        allowed_tools_str = json.dumps(agent_data.get("allowed_tools", []))
        config_str = json.dumps(agent_data.get("config", {}))
        await self._execute(
            """INSERT OR REPLACE INTO custom_agents
               (id, name, description, system_prompt, model, allowed_tools, memory_namespace, config_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent_data["id"],
                agent_data["name"],
                agent_data.get("description", ""),
                agent_data["system_prompt"],
                agent_data.get("model", "llama3.1"),
                allowed_tools_str,
                agent_data.get("memory_namespace", f"custom_agent:{agent_data['id']}"),
                config_str,
            )
        )

    async def get_custom_agent(self, name_or_id: str) -> Optional[Dict[str, Any]]:
        await self.initialize()
        import json
        res = await self._fetchall(
            "SELECT * FROM custom_agents WHERE id = ? OR name = ?",
            (name_or_id, name_or_id)
        )
        if not res:
            return None
        item = dict(res[0])
        item["allowed_tools"] = json.loads(item.get("allowed_tools") or "[]")
        item["config"] = json.loads(item.get("config_json") or "{}")
        return item

    async def list_custom_agents(self) -> List[Dict[str, Any]]:
        await self.initialize()
        import json
        rows = await self._fetchall("SELECT * FROM custom_agents ORDER BY created_at DESC")
        result = []
        for r in rows:
            item = dict(r)
            item["allowed_tools"] = json.loads(item.get("allowed_tools") or "[]")
            item["config"] = json.loads(item.get("config_json") or "{}")
            result.append(item)
        return result

    async def delete_custom_agent(self, name_or_id: str) -> bool:
        await self.initialize()
        count = await self._execute(
            "DELETE FROM custom_agents WHERE id = ? OR name = ?",
            (name_or_id, name_or_id)
        )
        return count > 0
