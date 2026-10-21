"""Base class for all Sunday Swarm specialist agents."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

from .bus import SwarmBus
from .events import (
    SwarmEvent,
    EventTopic,
    EventPriority,
    TaskAssignEvent,
    TaskPatchEvent,
    StatusNudgeEvent,
)

logger = logging.getLogger(__name__)


class SwarmAgent(ABC):
    """Abstract base class for a specialist in the Sunday Swarm."""

    def __init__(
        self,
        name: str,
        role: str,
        bus: SwarmBus,
        system_prompt: str = "",
        allowed_tools: Optional[List[str]] = None,
        memory_namespace: Optional[str] = None,
    ):
        self.name = name
        self.role = role
        self.bus = bus
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools or []
        self.memory_namespace = memory_namespace or f"swarm:{name}"

        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_contexts: Dict[str, Dict[str, Any]] = {}
        self._running = False

    async def start(self) -> None:
        """Register the agent with the SwarmBus and initialize mailboxes."""
        if self._running:
            return
        self._running = True
        self.bus.register_agent_mailbox(self.name, self.handle_event)
        self.bus.subscribe(EventTopic.TASK_PATCH.value, self._handle_possible_patch)
        self.bus.subscribe(EventTopic.TASK_CANCEL.value, self._handle_possible_cancel)
        logger.info(f"SwarmAgent [{self.name}] started and registered to bus.")

    async def stop(self) -> None:
        """Cancel all active tasks and unregister from the bus."""
        self._running = False
        self.bus.unregister_agent_mailbox(self.name, self.handle_event)
        self.bus.unsubscribe(EventTopic.TASK_PATCH.value, self._handle_possible_patch)
        self.bus.unsubscribe(EventTopic.TASK_CANCEL.value, self._handle_possible_cancel)

        # Cancel running background tasks
        for task_id, task in list(self.active_tasks.items()):
            if not task.done():
                task.cancel()
        self.active_tasks.clear()
        logger.info(f"SwarmAgent [{self.name}] stopped.")

    async def handle_event(self, event: SwarmEvent) -> None:
        """Main event router for incoming events directed to this agent."""
        if event.topic == EventTopic.TASK_ASSIGN and isinstance(event, TaskAssignEvent):
            await self._handle_task_assign(event)
        elif event.topic == EventTopic.TASK_PATCH and isinstance(event, TaskPatchEvent):
            await self.handle_task_patch(event)
        elif event.topic == EventTopic.TASK_CANCEL:
            await self._handle_task_cancel(event)
        else:
            await self.on_custom_event(event)

    async def _handle_possible_patch(self, event: SwarmEvent) -> None:
        if isinstance(event, TaskPatchEvent):
            if event.task_id in self.active_tasks or event.task_id in self.task_contexts:
                await self.handle_task_patch(event)

    async def _handle_possible_cancel(self, event: SwarmEvent) -> None:
        task_id = event.payload.get("task_id")
        if task_id and task_id in self.active_tasks:
            await self.cancel_task(task_id)

    async def _handle_task_assign(self, event: TaskAssignEvent) -> None:
        """Dispatch assigned task to background execution."""
        task_id = event.task_id
        existing_patches = self.task_contexts.get(task_id, {}).get("patches", [])
        self.task_contexts[task_id] = {
            "instruction": event.instruction,
            "context": event.context,
            "patches": existing_patches,
            "status": "running",
        }

        # Spawn background execution
        task_coro = self.execute_task(task_id, event.instruction, event.context)
        bg_task = asyncio.create_task(self._task_wrapper(task_id, task_coro))
        self.active_tasks[task_id] = bg_task

    async def _task_wrapper(self, task_id: str, coro) -> None:
        try:
            result = await coro
            self.task_contexts[task_id]["status"] = "completed"
            await self.publish_nudge(
                task_id=task_id,
                status="completed",
                summary=f"Task completed successfully.",
                details={"result": result},
            )
        except asyncio.CancelledError:
            self.task_contexts[task_id]["status"] = "cancelled"
            logger.info(f"Task {task_id} on [{self.name}] was cancelled.")
        except Exception as e:
            self.task_contexts[task_id]["status"] = "failed"
            logger.error(f"Task {task_id} failed on [{self.name}]: {e}", exc_info=True)
            await self.publish_nudge(
                task_id=task_id,
                status="failed",
                summary=f"Task failed: {str(e)}",
                details={"error": str(e)},
                priority=EventPriority.CRITICAL,
            )
        finally:
            self.active_tasks.pop(task_id, None)

    @abstractmethod
    async def execute_task(self, task_id: str, instruction: str, context: Dict[str, Any]) -> Any:
        """Implement the agent's core task logic."""
        pass

    async def handle_task_patch(self, event: TaskPatchEvent) -> None:
        """Default live-steering handler: stores patch and notifies active execution."""
        task_id = event.task_id
        if task_id in self.task_contexts:
            self.task_contexts[task_id]["patches"].append({
                "patch_instruction": event.patch_instruction,
                "patch_params": event.patch_params,
            })
            logger.info(f"[{self.name}] Received live steering patch for task {task_id}: {event.patch_instruction}")
            await self.on_task_patched(task_id, event.patch_instruction, event.patch_params)

    async def on_task_patched(self, task_id: str, patch_instruction: str, patch_params: Dict[str, Any]) -> None:
        """Hook for agent subclasses to dynamically adapt running code/execution."""
        pass

    async def cancel_task(self, task_id: str) -> None:
        """Cancel an ongoing task."""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            self.task_contexts[task_id]["status"] = "cancelled"
            await self.publish_nudge(
                task_id=task_id,
                status="cancelled",
                summary="Task execution was stopped by user request.",
            )

    async def publish_nudge(
        self,
        task_id: str,
        status: str,
        summary: str,
        details: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.HIGH,
    ) -> None:
        """Send a conversational milestone nudge back to the Conductor."""
        nudge = StatusNudgeEvent(
            source_agent=self.name,
            target_agent="conductor",
            task_id=task_id,
            status=status,
            summary=summary,
            details=details or {},
            priority=priority,
        )
        await self.bus.publish(nudge)

    async def on_custom_event(self, event: SwarmEvent) -> None:
        """Optional hook for arbitrary custom events."""
        pass
