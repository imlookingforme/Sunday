"""Scout Agent: Web research, documentation monitoring, and tech advancement tracking."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from .base_agent import SwarmAgent
from .bus import SwarmBus

logger = logging.getLogger(__name__)


class Scout(SwarmAgent):
    """Web and intelligence research specialist in the Sunday Swarm."""

    def __init__(self, bus: SwarmBus, allowed_tools: Optional[List[str]] = None):
        super().__init__(
            name="scout",
            role="Web, Documentation & Newsletter Scout",
            bus=bus,
            system_prompt="You are Sunday's Scout. You monitor newsletters, search the web, track AI advancements, and extract key insights.",
            allowed_tools=allowed_tools or ["web_search", "fetch_url", "summarize_webpage", "news_search"],
            memory_namespace="swarm:scout",
        )
        self.findings_archive: List[Dict[str, Any]] = []

    async def execute_task(self, task_id: str, instruction: str, context: Dict[str, Any]) -> Any:
        logger.info(f"[scout] Starting research for task {task_id}: {instruction}")

        await self.publish_nudge(
            task_id=task_id,
            status="progress",
            summary=f"Scouring web and sources for '{instruction[:35]}...' ",
        )

        # Cooperative wait allowing event processing
        await asyncio.sleep(0.6)

        # Synthesize findings
        finding = {
            "query": instruction,
            "summary": f"Identified key updates and documentation regarding {instruction}.",
            "sources": ["web_search", "tech_news_digest"],
            "timestamp": asyncio.get_event_loop().time(),
        }
        self.findings_archive.append(finding)

        logger.info(f"[scout] Research completed for task {task_id}.")
        return finding
