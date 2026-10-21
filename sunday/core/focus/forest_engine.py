"""Forest Focus Engine: Virtual tree life cycle, focus sprints, and persistent forest garden."""

import asyncio
import logging
import time
import aiosqlite
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TreeGrowthStage(Enum):
    """Stages of a tree's growth cycle."""
    SEED = "seed"            # 0% - 20%
    SPROUT = "sprout"        # 20% - 50%
    SAPLING = "sapling"      # 50% - 80%
    MATURE_TREE = "mature"   # 100% completed
    WILTED_TREE = "wilted"   # Failed due to distraction


class ForestEngine:
    """Manages focus sessions, tree growth, and persistent forest history."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("sunday/data/forest.db")
        self.current_session: Optional[Dict[str, Any]] = None
        self._lock = asyncio.Lock()
        self._init_done = False

    async def initialize(self) -> None:
        """Create sqlite tables if not present."""
        if self._init_done:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS forest_sessions (
                    session_id TEXT PRIMARY KEY,
                    tag TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    status TEXT NOT NULL,
                    growth_percentage REAL NOT NULL,
                    tree_species TEXT NOT NULL
                )
            """)
            await db.commit()
        self._init_done = True

    async def start_session(
        self,
        duration_minutes: int = 25,
        tag: str = "Academic Study",
        tree_species: str = "Sakura Cherry Blossom"
    ) -> Dict[str, Any]:
        """Start a new timed focus sprint."""
        await self.initialize()
        async with self._lock:
            if self.current_session and self.current_session.get("status") == "growing":
                return self.current_session

            session_id = f"forest_{int(time.time())}"
            self.current_session = {
                "session_id": session_id,
                "tag": tag,
                "duration_minutes": duration_minutes,
                "start_time": time.time(),
                "end_time": None,
                "status": "growing",
                "stage": TreeGrowthStage.SEED.value,
                "growth_percentage": 0.0,
                "tree_species": tree_species
            }

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO forest_sessions (session_id, tag, duration_minutes, start_time, status, growth_percentage, tree_species)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, tag, duration_minutes, self.current_session["start_time"], "growing", 0.0, tree_species)
                )
                await db.commit()

            logger.info(f"Forest session started: {session_id} ({duration_minutes}m, {tree_species})")
            return self.current_session

    async def get_current_status(self) -> Dict[str, Any]:
        """Calculate live progress and growth stage of current session."""
        if not self.current_session:
            return {"active": False, "status": "idle"}

        if self.current_session["status"] != "growing":
            return {"active": False, **self.current_session}

        now = time.time()
        elapsed_seconds = now - self.current_session["start_time"]
        total_seconds = self.current_session["duration_minutes"] * 60.0
        progress = min(1.0, max(0.0, elapsed_seconds / total_seconds))
        percentage = round(progress * 100.0, 1)

        # Stage calculation
        if progress >= 1.0:
            stage = TreeGrowthStage.MATURE_TREE
            # Automatically finish mature session
            return await self.complete_session()
        elif progress >= 0.8:
            stage = TreeGrowthStage.SAPLING
        elif progress >= 0.3:
            stage = TreeGrowthStage.SPROUT
        else:
            stage = TreeGrowthStage.SEED

        self.current_session["growth_percentage"] = percentage
        self.current_session["stage"] = stage.value

        remaining_seconds = max(0.0, total_seconds - elapsed_seconds)

        return {
            "active": True,
            **self.current_session,
            "elapsed_seconds": round(elapsed_seconds, 1),
            "remaining_seconds": round(remaining_seconds, 1)
        }

    async def wilt_current_tree(self, reason: str = "Distraction exceeded limit") -> Dict[str, Any]:
        """Wilt the current growing tree due to sustained distraction."""
        await self.initialize()
        async with self._lock:
            if not self.current_session or self.current_session["status"] != "growing":
                return {"success": False, "message": "No active tree growing"}

            now = time.time()
            self.current_session["status"] = "wilted"
            self.current_session["stage"] = TreeGrowthStage.WILTED_TREE.value
            self.current_session["end_time"] = now
            self.current_session["wilt_reason"] = reason

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE forest_sessions
                    SET status = 'wilted', end_time = ?, growth_percentage = ?
                    WHERE session_id = ?
                    """,
                    (now, self.current_session["growth_percentage"], self.current_session["session_id"])
                )
                await db.commit()

            logger.warning(f"Tree wilted in session {self.current_session['session_id']}: {reason}")
            result = dict(self.current_session)
            return result

    async def complete_session(self) -> Dict[str, Any]:
        """Successfully complete focus sprint and record mature tree."""
        await self.initialize()
        async with self._lock:
            if not self.current_session or self.current_session["status"] != "growing":
                return self.current_session or {"active": False}

            now = time.time()
            self.current_session["status"] = "mature"
            self.current_session["stage"] = TreeGrowthStage.MATURE_TREE.value
            self.current_session["growth_percentage"] = 100.0
            self.current_session["end_time"] = now

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE forest_sessions
                    SET status = 'mature', end_time = ?, growth_percentage = 100.0
                    WHERE session_id = ?
                    """,
                    (now, self.current_session["session_id"])
                )
                await db.commit()

            logger.info(f"Tree successfully matured in session {self.current_session['session_id']}")
            result = dict(self.current_session)
            return result

    async def get_forest_summary(self) -> Dict[str, Any]:
        """Get aggregate statistics of all trees in the forest."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT status, count(*) FROM forest_sessions GROUP BY status") as cursor:
                rows = await cursor.fetchall()
                counts = dict(rows)

            async with db.execute(
                "SELECT session_id, tag, duration_minutes, status, growth_percentage, tree_species, start_time FROM forest_sessions ORDER BY start_time DESC LIMIT 20"
            ) as cursor:
                recent_rows = await cursor.fetchall()
                recent = [
                    {
                        "session_id": r[0],
                        "tag": r[1],
                        "duration_minutes": r[2],
                        "status": r[3],
                        "growth_percentage": r[4],
                        "tree_species": r[5],
                        "start_time": r[6],
                    }
                    for r in recent_rows
                ]

        mature = counts.get("mature", 0)
        wilted = counts.get("wilted", 0)
        total = mature + wilted
        success_rate = round((mature / total * 100.0), 1) if total > 0 else 100.0

        return {
            "total_trees": total,
            "mature_trees": mature,
            "wilted_trees": wilted,
            "success_rate": success_rate,
            "recent_sessions": recent,
            "active_session": self.current_session if self.current_session and self.current_session.get("status") == "growing" else None
        }
