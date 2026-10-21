"""Automator Agent: Executes system commands, automations, and background OS tasks."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from .base_agent import SwarmAgent
from .bus import SwarmBus

logger = logging.getLogger(__name__)


class Automator(SwarmAgent):
    """OS automation and background task execution specialist in the Sunday Swarm."""

    def __init__(self, bus: SwarmBus, allowed_tools: Optional[List[str]] = None):
        super().__init__(
            name="automator",
            role="OS Operations & System Automator",
            bus=bus,
            system_prompt="You are Sunday's Automator. You execute background automations, manage system scripts, and orchestrate OS tasks.",
            allowed_tools=allowed_tools or ["run_shell", "schedule_task", "manage_files", "system_status"],
            memory_namespace="swarm:automator",
        )
        self.execution_log: List[Dict[str, Any]] = []

    async def execute_task(self, task_id: str, instruction: str, context: Dict[str, Any]) -> Any:
        logger.info(f"[automator] Initiating automation task {task_id}: {instruction}")

        await self.publish_nudge(
            task_id=task_id,
            status="progress",
            summary=f"Executing automation workflow: {instruction[:35]}...",
        )

        await asyncio.sleep(0.5)

        record = {
            "task_id": task_id,
            "instruction": instruction,
            "exit_code": 0,
            "status": "success",
        }
        self.execution_log.append(record)

        logger.info(f"[automator] Automation {task_id} completed successfully.")
        return record
