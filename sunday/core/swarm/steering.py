"""Live Steering Manager for dynamic mid-flight task updates."""

import logging
from typing import Any, Dict, List, Optional
from .bus import SwarmBus
from .events import TaskPatchEvent, SwarmEvent, EventTopic, EventPriority

logger = logging.getLogger(__name__)


class LiveSteeringManager:
    """Manages active task registry and facilitates real-time steering patches."""

    def __init__(self, bus: SwarmBus):
        self.bus = bus
        self._active_tasks: Dict[str, Dict[str, Any]] = {}

    def register_task(self, task_id: str, agent_name: str, instruction: str) -> None:
        """Track a new active task."""
        self._active_tasks[task_id] = {
            "task_id": task_id,
            "agent_name": agent_name,
            "instruction": instruction,
            "status": "running",
            "patches": [],
        }

    def mark_task_done(self, task_id: str, status: str = "completed") -> None:
        """Mark a task as finished or cancelled."""
        if task_id in self._active_tasks:
            self._active_tasks[task_id]["status"] = status

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Return list of currently running tasks."""
        return [t for t in self._active_tasks.values() if t["status"] == "running"]

    def find_latest_task_for_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Find the most recently started running task for an agent."""
        matching = [t for t in self._active_tasks.values() if t["agent_name"] == agent_name and t["status"] == "running"]
        return matching[-1] if matching else None

    async def apply_patch(
        self,
        task_id: str,
        patch_instruction: str,
        patch_params: Optional[Dict[str, Any]] = None,
        source_agent: str = "conductor",
    ) -> bool:
        """Publish a live-steering patch event to update an active task."""
        task_info = self._active_tasks.get(task_id)
        target_agent = task_info["agent_name"] if task_info else None

        patch_event = TaskPatchEvent(
            source_agent=source_agent,
            target_agent=target_agent,
            task_id=task_id,
            patch_instruction=patch_instruction,
            patch_params=patch_params or {},
            priority=EventPriority.CRITICAL,
        )

        if task_info:
            task_info["patches"].append(patch_instruction)

        logger.info(f"Applying live steering patch to task [{task_id}]: {patch_instruction}")
        await self.bus.publish(patch_event)
        return True

    async def cancel_task(self, task_id: str, source_agent: str = "conductor") -> bool:
        """Publish a cancellation event for an active task."""
        task_info = self._active_tasks.get(task_id)
        target_agent = task_info["agent_name"] if task_info else None

        cancel_event = SwarmEvent(
            source_agent=source_agent,
            target_agent=target_agent,
            topic=EventTopic.TASK_CANCEL,
            priority=EventPriority.CRITICAL,
            payload={"task_id": task_id},
        )
        if task_info:
            task_info["status"] = "cancelled"
        await self.bus.publish(cancel_event)
        return True
