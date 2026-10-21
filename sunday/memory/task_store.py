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

class TaskStore:
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
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                due_date TEXT,
                priority INTEGER,
                tags TEXT,
                status TEXT,
                parent_id TEXT,
                source_url TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._initialized = True
        
    async def create_task(self, task_id: str, title: str, description: str = "", 
                         due_date: str = None, priority: int = 1, tags: str = "",
                         status: str = "pending", parent_id: str = None, source_url: str = None):
        await self.initialize()
        await self._execute(
            """INSERT INTO tasks (id, title, description, due_date, priority, tags, status, parent_id, source_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, title, description, due_date, priority, tags, status, parent_id, source_url)
        )
        
    async def get_tasks(self, status: str = None) -> List[Dict[str, Any]]:
        await self.initialize()
        if status:
            return await self._fetchall("SELECT * FROM tasks WHERE status = ?", (status,))
        return await self._fetchall("SELECT * FROM tasks")
        
    async def update_task_status(self, task_id: str, status: str):
        await self.initialize()
        await self._execute(
            "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
            (status, task_id)
        )
        
    async def break_down_task(self, parent_id: str, subtasks: List[Dict[str, Any]]):
        await self.initialize()
        for st in subtasks:
            await self.create_task(
                task_id=st["id"],
                title=st["title"],
                description=st.get("description", ""),
                parent_id=parent_id,
                status="pending"
            )
            
    async def batch_reschedule(self, task_ids: List[str], new_due_date: str):
        await self.initialize()
        for tid in task_ids:
            await self._execute(
                "UPDATE tasks SET due_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                (new_due_date, tid)
            )
