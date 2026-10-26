"""Mission Control 2.0 Backend Controller and Live SSE Stream for Sunday 2.0.

Provides:
- Task Pipeline Aggregation:
    * Grouping by states: Queued, Planning, Running, Waiting Approval, Verifying, Completed, Failed
    * Resource usage and token metrics
- Live Agent Inspector:
    * Swarm specialist status (Conductor, Coder, Scout, Automator, Gatekeeper)
    * Running task associations, uptime, and last action logs
- User Intervention Engine:
    * Pause / Resume / Cancel tasks
    * Grant / Reject cryptographic approval requests
    * Trigger rollback on checkpoints
- Live Server-Sent Events (SSE) Bus:
    * Broadcasts task updates, agent transitions, and interventions in real time
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from sunday.core.durable_tasks import DurableTaskEngine, TaskRecord, TaskState
from sunday.core.git_safety import GitSafetyManager
from sunday.core.security_broker import EnhancedSecurityBroker

logger = logging.getLogger(__name__)


class MissionControlService:
    """Operations coordinator powering the Mission Control 2.0 dashboard."""

    def __init__(
        self,
        task_engine: Optional[DurableTaskEngine] = None,
        security_broker: Optional[EnhancedSecurityBroker] = None,
        git_safety: Optional[GitSafetyManager] = None,
    ):
        self.task_engine = task_engine or DurableTaskEngine()
        self.security_broker = security_broker
        self.git_safety = git_safety or GitSafetyManager()
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def get_task_pipeline_summary(self) -> Dict[str, Any]:
        """Aggregate all persistent tasks into Kanban/pipeline buckets."""
        all_tasks = await self.task_engine.list_tasks()

        buckets = {
            "queued": [],
            "planning": [],
            "ready": [],
            "running": [],
            "waiting_approval": [],
            "verifying": [],
            "completed": [],
            "failed": [],
            "cancelled": [],
            "interrupted": [],
        }

        for t in all_tasks:
            state_key = t.state.value
            if state_key in buckets:
                buckets[state_key].append({
                    "task_id": t.task_id,
                    "request": t.original_request,
                    "agent": t.assigned_agent,
                    "current_step": t.current_step,
                    "retry_count": t.retry_count,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at,
                    "criteria_count": len(t.acceptance_criteria),
                    "summary": t.completion_summary,
                })

        return {
            "total_tasks": len(all_tasks),
            "active_tasks": len(buckets["running"]) + len(buckets["planning"]) + len(buckets["verifying"]),
            "pending_approvals": len(buckets["waiting_approval"]),
            "buckets": buckets,
        }

    async def get_agent_inspector_data(self) -> List[Dict[str, Any]]:
        """Return real-time diagnostic status for all core swarm agents."""
        agents = [
            {"role": "Conductor", "name": "conductor", "status": "online", "description": "Conversational Dialogue Liaison"},
            {"role": "Coder", "name": "coder", "status": "online", "description": "Autonomous Code Generator & Patch Specialist"},
            {"role": "Scout", "name": "scout", "status": "online", "description": "Autonomous Researcher & Paper Indexer"},
            {"role": "Automator", "name": "automator", "status": "online", "description": "System Command & Subprocess Supervisor"},
            {"role": "Gatekeeper", "name": "gatekeeper", "status": "online", "description": "Security Token & Failover Guardian"},
        ]

        # Attach currently assigned running tasks
        running_tasks = await self.task_engine.list_tasks(state=TaskState.RUNNING)
        for a in agents:
            matching = [t for t in running_tasks if t.assigned_agent == a["name"]]
            a["current_task"] = matching[0].task_id if matching else None
            a["active_load"] = len(matching)

        return agents

    async def handle_user_intervention(self, action: str, task_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process developer control actions (cancel, retry, approve, reject, rollback)."""
        data = payload or {}

        if action == "cancel":
            cancelled = await self.task_engine.cancel_task_tree(task_id, reason="User intervention from Mission Control")
            await self.broadcast_event("task_cancelled", {"task_id": task_id, "affected": cancelled})
            return {"success": True, "action": "cancel", "cancelled_tasks": cancelled}

        elif action == "approve":
            req_id = data.get("request_id")
            token = data.get("token", "")
            if self.security_broker and req_id:
                ok = self.security_broker.approve_request(req_id, token)
                if ok:
                    await self.task_engine.transition(task_id, TaskState.RUNNING, reason="User approved security request")
                    await self.broadcast_event("approval_granted", {"task_id": task_id, "request_id": req_id})
                    return {"success": True, "action": "approve"}
            return {"success": False, "error": "Approval request not found or token invalid"}

        elif action == "reject":
            req_id = data.get("request_id")
            if self.security_broker and req_id:
                self.security_broker.reject_request(req_id)
                await self.task_engine.transition(task_id, TaskState.FAILED, reason="User rejected security request")
                await self.broadcast_event("approval_rejected", {"task_id": task_id, "request_id": req_id})
                return {"success": True, "action": "reject"}
            return {"success": False, "error": "Invalid request ID"}

        elif action == "rollback":
            checkpoint_id = data.get("checkpoint_id")
            if checkpoint_id and self.git_safety:
                restored = await self.git_safety.rollback_checkpoint(checkpoint_id)
                await self.broadcast_event("checkpoint_restored", {"task_id": task_id, "checkpoint_id": checkpoint_id})
                return {"success": restored, "action": "rollback", "checkpoint_id": checkpoint_id}
            return {"success": False, "error": "Missing checkpoint ID"}

        return {"success": False, "error": f"Unknown action '{action}'"}

    async def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Publish event to all open SSE connections."""
        msg = json.dumps({"event": event_type, "data": data, "timestamp": time.time()})
        async with self._lock:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(msg)
                except Exception:
                    pass

    async def sse_event_stream(self) -> AsyncGenerator[str, None]:
        """Stream events to client browser via Server-Sent Events."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers.append(queue)

        try:
            # Yield initial connection heartbeat
            yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'time': time.time()})}\n\n"
            while True:
                data = await queue.get()
                yield f"event: update\ndata: {data}\n\n"
        finally:
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)
