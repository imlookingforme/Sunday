"""Durable Task State Machine and Execution Lifecycle Engine for Sunday 2.0.

Provides robust, persistent, recoverable task states, explicit state transitions,
cancellation propagation, execution budgets, checkpoint references, tool audit links,
and post-crash recovery journaling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """Formal states in a task lifecycle."""
    QUEUED = "queued"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    VERIFYING = "verifying"
    BLOCKED = "blocked"
    RETRY_SCHEDULED = "retry_scheduled"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    RECOVERING = "recovering"


# Valid explicit state transitions
VALID_TRANSITIONS: Dict[TaskState, Set[TaskState]] = {
    TaskState.QUEUED: {TaskState.PLANNING, TaskState.CANCELLED, TaskState.BLOCKED},
    TaskState.PLANNING: {TaskState.READY, TaskState.WAITING_APPROVAL, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.READY: {TaskState.RUNNING, TaskState.CANCELLED, TaskState.BLOCKED},
    TaskState.RUNNING: {
        TaskState.VERIFYING,
        TaskState.WAITING_APPROVAL,
        TaskState.FAILED,
        TaskState.CANCELLED,
        TaskState.INTERRUPTED,
        TaskState.RETRY_SCHEDULED,
    },
    TaskState.WAITING_APPROVAL: {TaskState.READY, TaskState.RUNNING, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.VERIFYING: {TaskState.COMPLETED, TaskState.RETRY_SCHEDULED, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.BLOCKED: {TaskState.READY, TaskState.QUEUED, TaskState.CANCELLED},
    TaskState.RETRY_SCHEDULED: {TaskState.READY, TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.INTERRUPTED: {TaskState.RECOVERING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.RECOVERING: {TaskState.READY, TaskState.RUNNING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.COMPLETED: set(),
    TaskState.FAILED: {TaskState.RETRY_SCHEDULED},
    TaskState.CANCELLED: set(),
}


@dataclass
class ExecutionBudget:
    """Resource bounds on task execution."""
    max_duration_seconds: float = 600.0
    max_retries: int = 3
    max_tool_calls: int = 50
    token_budget: Optional[int] = None
    cost_budget_usd: Optional[float] = None


@dataclass
class TaskRecord:
    """Complete durable task entity representing full lifecycle state."""
    task_id: str
    original_request: str
    workspace: str = "."
    parent_id: Optional[str] = None
    state: TaskState = TaskState.QUEUED
    assigned_agent: Optional[str] = None
    acceptance_criteria: List[str] = field(default_factory=list)
    plan: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    dependencies: List[str] = field(default_factory=list)
    checkpoint_refs: List[str] = field(default_factory=list)
    pending_approvals: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    verification_results: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    budget: ExecutionBudget = field(default_factory=ExecutionBudget)
    error_info: Optional[Dict[str, Any]] = None
    completion_summary: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class DurableTaskEngine:
    """Durable Task Engine managing task persistence, state transitions, and recovery."""

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = str(db_path or Path("sunday") / "data" / "sunday.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_done = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Create or migrate durable task table schemas."""
        if self._init_done:
            return

        def _sync_init():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS durable_tasks (
                        task_id TEXT PRIMARY KEY,
                        parent_id TEXT,
                        workspace TEXT,
                        original_request TEXT NOT NULL,
                        state TEXT NOT NULL,
                        assigned_agent TEXT,
                        acceptance_criteria TEXT,
                        plan TEXT,
                        current_step INTEGER DEFAULT 0,
                        dependencies TEXT,
                        checkpoint_refs TEXT,
                        pending_approvals TEXT,
                        tool_results TEXT,
                        verification_results TEXT,
                        retry_count INTEGER DEFAULT 0,
                        budget TEXT,
                        error_info TEXT,
                        completion_summary TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS task_state_transitions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT NOT NULL,
                        from_state TEXT NOT NULL,
                        to_state TEXT NOT NULL,
                        reason TEXT,
                        timestamp REAL NOT NULL
                    )
                """)
                conn.commit()

        await asyncio.to_thread(_sync_init)
        self._init_done = True

    async def create_task(
        self,
        task_id: str,
        original_request: str,
        workspace: str = ".",
        parent_id: Optional[str] = None,
        acceptance_criteria: Optional[List[str]] = None,
        budget: Optional[ExecutionBudget] = None,
        assigned_agent: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> TaskRecord:
        """Create and persist a new durable task."""
        await self.initialize()
        now = time.time()
        record = TaskRecord(
            task_id=task_id,
            original_request=original_request,
            workspace=workspace,
            parent_id=parent_id,
            state=TaskState.QUEUED,
            assigned_agent=assigned_agent,
            acceptance_criteria=acceptance_criteria or [],
            dependencies=dependencies or [],
            budget=budget or ExecutionBudget(),
            created_at=now,
            updated_at=now,
        )

        def _sync_create():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO durable_tasks (
                        task_id, parent_id, workspace, original_request, state,
                        assigned_agent, acceptance_criteria, plan, current_step,
                        dependencies, checkpoint_refs, pending_approvals,
                        tool_results, verification_results, retry_count, budget,
                        error_info, completion_summary, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.task_id,
                        record.parent_id,
                        record.workspace,
                        record.original_request,
                        record.state.value,
                        record.assigned_agent,
                        json.dumps(record.acceptance_criteria),
                        json.dumps(record.plan),
                        record.current_step,
                        json.dumps(record.dependencies),
                        json.dumps(record.checkpoint_refs),
                        json.dumps(record.pending_approvals),
                        json.dumps(record.tool_results),
                        json.dumps(record.verification_results),
                        record.retry_count,
                        json.dumps(asdict(record.budget)),
                        json.dumps(record.error_info) if record.error_info else None,
                        record.completion_summary,
                        record.created_at,
                        record.updated_at,
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_sync_create)
        logger.info(f"Durable task [{task_id}] created in QUEUED state.")
        return record

    async def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """Load task record by id."""
        await self.initialize()

        def _sync_get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM durable_tasks WHERE task_id = ?", (task_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return dict(row)

        raw = await asyncio.to_thread(_sync_get)
        if not raw:
            return None

        budget_data = json.loads(raw["budget"]) if raw.get("budget") else {}
        budget = ExecutionBudget(**budget_data)

        return TaskRecord(
            task_id=raw["task_id"],
            parent_id=raw["parent_id"],
            workspace=raw["workspace"] or ".",
            original_request=raw["original_request"],
            state=TaskState(raw["state"]),
            assigned_agent=raw["assigned_agent"],
            acceptance_criteria=json.loads(raw["acceptance_criteria"] or "[]"),
            plan=json.loads(raw["plan"] or "[]"),
            current_step=raw["current_step"] or 0,
            dependencies=json.loads(raw["dependencies"] or "[]"),
            checkpoint_refs=json.loads(raw["checkpoint_refs"] or "[]"),
            pending_approvals=json.loads(raw["pending_approvals"] or "[]"),
            tool_results=json.loads(raw["tool_results"] or "[]"),
            verification_results=json.loads(raw["verification_results"] or "{}"),
            retry_count=raw["retry_count"] or 0,
            budget=budget,
            error_info=json.loads(raw["error_info"]) if raw.get("error_info") else None,
            completion_summary=raw["completion_summary"],
            created_at=raw["created_at"],
            updated_at=raw["updated_at"],
        )

    async def transition(
        self,
        task_id: str,
        to_state: TaskState,
        reason: str = "",
        updates: Optional[Dict[str, Any]] = None,
    ) -> TaskRecord:
        """Validate and apply state transition."""
        await self.initialize()
        async with self._lock:
            task = await self.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            from_state = task.state
            if to_state not in VALID_TRANSITIONS.get(from_state, set()):
                raise ValueError(
                    f"Illegal task transition from {from_state.value} to {to_state.value} for task {task_id}"
                )

            now = time.time()
            task.state = to_state
            task.updated_at = now

            if updates:
                for k, v in updates.items():
                    if hasattr(task, k):
                        setattr(task, k, v)

            def _sync_update():
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        UPDATE durable_tasks
                        SET state = ?, assigned_agent = ?, acceptance_criteria = ?, plan = ?,
                            current_step = ?, dependencies = ?, checkpoint_refs = ?,
                            pending_approvals = ?, tool_results = ?, verification_results = ?,
                            retry_count = ?, budget = ?, error_info = ?, completion_summary = ?,
                            updated_at = ?
                        WHERE task_id = ?
                        """,
                        (
                            task.state.value,
                            task.assigned_agent,
                            json.dumps(task.acceptance_criteria),
                            json.dumps(task.plan),
                            task.current_step,
                            json.dumps(task.dependencies),
                            json.dumps(task.checkpoint_refs),
                            json.dumps(task.pending_approvals),
                            json.dumps(task.tool_results),
                            json.dumps(task.verification_results),
                            task.retry_count,
                            json.dumps(asdict(task.budget)),
                            json.dumps(task.error_info) if task.error_info else None,
                            task.completion_summary,
                            task.updated_at,
                            task.task_id,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO task_state_transitions (task_id, from_state, to_state, reason, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (task.task_id, from_state.value, to_state.value, reason, now),
                    )
                    conn.commit()

            await asyncio.to_thread(_sync_update)
            logger.info(f"Task [{task_id}] transitioned {from_state.value} -> {to_state.value} ({reason})")
            return task

    async def list_tasks(
        self,
        state: Optional[TaskState] = None,
        parent_id: Optional[str] = None,
    ) -> List[TaskRecord]:
        """List tasks optionally filtered by state or parent."""
        await self.initialize()

        def _sync_list():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = "SELECT task_id FROM durable_tasks WHERE 1=1"
                params = []
                if state:
                    query += " AND state = ?"
                    params.append(state.value)
                if parent_id is not None:
                    query += " AND parent_id = ?"
                    params.append(parent_id)
                query += " ORDER BY created_at DESC"
                cursor.execute(query, tuple(params))
                return [r["task_id"] for r in cursor.fetchall()]

        task_ids = await asyncio.to_thread(_sync_list)
        records = []
        for tid in task_ids:
            rec = await self.get_task(tid)
            if rec:
                records.append(rec)
        return records

    async def cancel_task_tree(self, root_task_id: str, reason: str = "User cancelled") -> List[str]:
        """Recursively cancel a task and all of its descendants."""
        cancelled = []

        async def _cancel(tid: str):
            task = await self.get_task(tid)
            if not task:
                return
            if task.state not in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):
                await self.transition(tid, TaskState.CANCELLED, reason=reason)
                cancelled.append(tid)

            children = await self.list_tasks(parent_id=tid)
            for child in children:
                await _cancel(child.task_id)

        await _cancel(root_task_id)
        return cancelled

    async def recover_interrupted_tasks(self) -> List[TaskRecord]:
        """Identify tasks that were in RUNNING/PLANNING when the system halted and move them to INTERRUPTED."""
        await self.initialize()
        running_tasks = await self.list_tasks(state=TaskState.RUNNING)
        planning_tasks = await self.list_tasks(state=TaskState.PLANNING)
        recovered = []

        for task in running_tasks + planning_tasks:
            updated = await self.transition(
                task.task_id,
                TaskState.INTERRUPTED,
                reason="System restart detected unfinalized execution",
            )
            recovered.append(updated)

        return recovered
