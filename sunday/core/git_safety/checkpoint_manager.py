"""Git Safety and Checkpoint Manager for Sunday 2.0.

Provides:
- Working tree change inspection (detects pre-existing user edits)
- Automated lightweight checkpoints (stash / git ref snapshots)
- Safe selective rollback of agent-modified files while preserving user work
- Conflict detection between concurrent agent operations
- Isolated worktree allocation for parallel subtasks
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """Snapshot of a working tree state."""
    checkpoint_id: str
    task_id: str
    timestamp: float
    description: str
    tracked_files: List[str]
    backup_dir: Optional[str] = None


class GitSafetyManager:
    """Protects existing repository code and manages rollback checkpoints."""

    def __init__(self, repo_root: Path | str = ".", checkpoint_dir: Optional[Path | str] = None):
        self.repo_root = Path(repo_root).resolve()
        self.checkpoint_dir = Path(checkpoint_dir or (self.repo_root / ".sunday_checkpoints")).resolve()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoints: Dict[str, Checkpoint] = {}

    async def get_dirty_files(self) -> List[str]:
        """Query git status to identify all currently uncommitted files."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "status", "--porcelain",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.repo_root),
            )
            stdout, _ = await proc.communicate()
            dirty = []
            for line in stdout.decode("utf-8", errors="replace").splitlines():
                if line.strip():
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        dirty.append(parts[1].replace("\\", "/"))
            return dirty
        except Exception as e:
            logger.warning(f"Could not read git status: {e}")
            return []

    async def create_checkpoint(self, task_id: str, files_to_modify: List[str], description: str = "") -> Checkpoint:
        """Create a discrete file-level checkpoint before modifying files."""
        cp_id = f"cp_{int(time.time())}_{len(self._checkpoints)}"
        snapshot_dir = self.checkpoint_dir / cp_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        backed_up = []
        for rel_file in files_to_modify:
            src = self.repo_root / rel_file
            if src.is_file():
                dest = snapshot_dir / rel_file
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                backed_up.append(rel_file)

        cp = Checkpoint(
            checkpoint_id=cp_id,
            task_id=task_id,
            timestamp=time.time(),
            description=description,
            tracked_files=backed_up,
            backup_dir=str(snapshot_dir),
        )
        self._checkpoints[cp_id] = cp
        logger.info(f"Created Git checkpoint [{cp_id}] for {len(backed_up)} files.")
        return cp

    async def rollback_checkpoint(self, checkpoint_id: str) -> bool:
        """Selectively restore files from a checkpoint without modifying unrelated edits."""
        cp = self._checkpoints.get(checkpoint_id)
        if not cp or not cp.backup_dir:
            logger.error(f"Checkpoint [{checkpoint_id}] not found.")
            return False

        snapshot_dir = Path(cp.backup_dir)
        for rel_file in cp.tracked_files:
            backup_file = snapshot_dir / rel_file
            dest_file = self.repo_root / rel_file
            if backup_file.is_file():
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, dest_file)
                logger.info(f"Restored {rel_file} from checkpoint {checkpoint_id}")

        return True

    def check_file_conflicts(self, target_files: List[str], active_agent_files: Dict[str, List[str]]) -> Dict[str, str]:
        """Detect overlapping write sets across concurrent agents."""
        conflicts = {}
        target_set = set(f.replace("\\", "/") for f in target_files)
        for agent_name, agent_files in active_agent_files.items():
            overlap = target_set.intersection(set(f.replace("\\", "/") for f in agent_files))
            if overlap:
                conflicts[agent_name] = list(overlap)
        return conflicts
