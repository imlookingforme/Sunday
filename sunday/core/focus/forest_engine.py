"""Forest Engine: SQLite-backed focus tree growth simulator for Sunday."""

import logging
import time
from enum import Enum
from typing import Dict, Any, Optional
import aiosqlite

logger = logging.getLogger(__name__)

class TreeGrowthStage(Enum):
    SEED = "seed"
    SPROUT = "sprout"
    SAPLING = "sapling"
    TREE = "tree"
    FLOWERING = "flowering"
    WILTED = "wilted"

class ForestEngine:
    """Manages the virtual focus forest, growing trees based on sustained focus."""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._current_tree: Optional[Dict[str, Any]] = None

    async def initialize(self):
        """Initialize the SQLite database schema for the forest."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS trees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    species TEXT NOT NULL,
                    tag TEXT,
                    start_time REAL NOT NULL,
                    target_duration REAL NOT NULL,
                    end_time REAL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            ''')
            await db.commit()

    async def plant_tree(self, duration_minutes: float, species: str = "Cherry Blossom", tag: str = "General") -> int:
        """Start a new focus session and plant a seed."""
        if self._current_tree:
            raise ValueError("A tree is already growing!")

        now = time.time()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO trees (species, tag, start_time, target_duration, stage, status) VALUES (?, ?, ?, ?, ?, ?)',
                (species, tag, now, duration_minutes * 60, TreeGrowthStage.SEED.value, "growing")
            )
            tree_id = cursor.lastrowid
            await db.commit()

        self._current_tree = {
            "id": tree_id,
            "species": species,
            "start_time": now,
            "target_duration": duration_minutes * 60,
            "stage": TreeGrowthStage.SEED
        }
        logger.info(f"Planted a {species} tree for {duration_minutes}m. (ID: {tree_id})")
        return tree_id

    async def update_growth(self) -> Dict[str, Any]:
        """Update the growth stage based on elapsed time."""
        if not self._current_tree:
            return {"status": "no_active_tree"}

        now = time.time()
        elapsed = now - self._current_tree["start_time"]
        progress = min(1.0, elapsed / self._current_tree["target_duration"])

        # Determine stage based on progress
        new_stage = TreeGrowthStage.SEED
        if progress >= 1.0:
            new_stage = TreeGrowthStage.FLOWERING
        elif progress >= 0.75:
            new_stage = TreeGrowthStage.TREE
        elif progress >= 0.5:
            new_stage = TreeGrowthStage.SAPLING
        elif progress >= 0.25:
            new_stage = TreeGrowthStage.SPROUT

        # Only update DB if stage changed or completed
        if new_stage != self._current_tree["stage"] or progress >= 1.0:
            self._current_tree["stage"] = new_stage
            status = "completed" if progress >= 1.0 else "growing"
            end_time = now if progress >= 1.0 else None
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE trees SET stage = ?, status = ?, end_time = ? WHERE id = ?',
                    (new_stage.value, status, end_time, self._current_tree["id"])
                )
                await db.commit()

            if progress >= 1.0:
                logger.info(f"Tree {self._current_tree['id']} fully grown!")
                completed_tree = self._current_tree.copy()
                completed_tree["status"] = "completed"
                self._current_tree = None
                return completed_tree

        return {
            "id": self._current_tree["id"],
            "progress": progress,
            "stage": new_stage.value,
            "status": "growing"
        }

    async def wilt_tree(self) -> Dict[str, Any]:
        """Force wilt the current tree due to a distraction infraction."""
        if not self._current_tree:
            return {"status": "no_active_tree"}

        now = time.time()
        tree_id = self._current_tree["id"]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE trees SET stage = ?, status = ?, end_time = ? WHERE id = ?',
                (TreeGrowthStage.WILTED.value, "wilted", now, tree_id)
            )
            await db.commit()

        logger.warning(f"Tree {tree_id} has wilted due to distraction.")
        self._current_tree = None
        
        return {"id": tree_id, "status": "wilted"}
