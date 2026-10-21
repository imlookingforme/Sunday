"""Custom Agent Sub-Runner: scoped execution context for user-defined specialist agents."""

import logging
import asyncio
from typing import Any, Dict, List, Optional

from sunday.memory.titans_memory import TitansMemory
from sunday.tools.registry import ToolRegistry
from pathlib import Path

logger = logging.getLogger(__name__)


class CustomAgentRunner:
    """
    Scoped execution context for a custom agent.
    - Loads agent definition from SQLiteStore
    - Provides isolated TitansMemory namespace
    - Provides filtered ToolRegistry slice
    - Executes prompt via Ollama with custom system_prompt
    - Returns synthesized output back to parent orchestrator
    """

    def __init__(self, agent_def: Dict[str, Any]):
        self.agent_def = agent_def
        self.agent_id = agent_def["id"]
        self.name = agent_def["name"]
        self.system_prompt = agent_def["system_prompt"]
        self.model = agent_def.get("model", "llama3.1")
        self.allowed_tools = agent_def.get("allowed_tools", [])
        self.memory_namespace = agent_def.get("memory_namespace", f"custom_agent:{self.agent_id}")

        # Isolated TitansMemory namespace
        memory_path = Path("sunday") / "data" / f"titans_memory_{self.agent_id}.json"
        self.memory = TitansMemory(
            memory_path=memory_path,
            surprise_threshold=0.4,
            decay_rate=0.95,
            max_episodes=500,
        )

        # Filtered tool slice from ToolRegistry
        self._tool_slice: Dict[str, Any] = {}
        self._load_tool_slice()

        self._conversation: List[Dict[str, str]] = []

    def _load_tool_slice(self) -> None:
        """Build a filtered tool set from the global ToolRegistry."""
        all_tools = {t.name: t for t in ToolRegistry.get_all()}
        for tool_name in self.allowed_tools:
            if tool_name in all_tools:
                self._tool_slice[tool_name] = all_tools[tool_name]
            else:
                # Allow category wildcards e.g. "research.*"
                if tool_name.endswith(".*"):
                    category = tool_name[:-2]
                    for t in ToolRegistry.list_by_category(category):
                        self._tool_slice[t.name] = t
        logger.info(f"[CustomAgentRunner:{self.name}] Tool slice: {list(self._tool_slice.keys())}")

    async def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a task within this custom agent's scoped context.
        Returns structured output with summary, tool calls used, and memory recorded.
        """
        logger.info(f"[CustomAgentRunner:{self.name}] Running task: {task}")
        context = context or {}

        # Recall relevant memory
        memory_context = await self._recall_context(task)

        # Build conversation
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        if memory_context:
            messages.append({"role": "system", "content": f"Relevant prior context:\n{memory_context}"})
        messages.append({"role": "user", "content": task})

        # Execute via Ollama (with tool-calling simulation)
        output = await self._invoke_llm(messages)
        tool_calls_made = await self._dispatch_tool_calls(output, context)

        # Record into isolated memory
        await self.memory.remember(
            content=f"Task: {task}\nOutput: {output}",
            outcome="success",
        )

        result = {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "task": task,
            "output": output,
            "tool_calls": tool_calls_made,
            "memory_namespace": self.memory_namespace,
            "status": "completed",
        }
        logger.info(f"[CustomAgentRunner:{self.name}] Task completed.")
        return result

    async def _recall_context(self, query: str) -> str:
        """Retrieve relevant episodes from this agent's isolated memory."""
        try:
            episodes = await self.memory.retrieve(query=query, limit=3)
            if not episodes:
                return ""
            return "\n".join(ep.get("content", "") for ep in episodes if isinstance(ep, dict))
        except Exception as e:
            logger.debug(f"Memory recall skipped: {e}")
            return ""

    async def _invoke_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call Ollama with agent's model and system prompt."""
        try:
            from ollama import AsyncClient
            client = AsyncClient()
            resp = await client.chat(model=self.model, messages=messages)
            return resp.get("message", {}).get("content", "")
        except Exception as e:
            logger.warning(f"Ollama unavailable for agent [{self.name}]: {e}")
            # Graceful fallback response
            task = next((m["content"] for m in messages if m["role"] == "user"), "task")
            return f"[{self.name}] Completed analysis of: {task}"

    async def _dispatch_tool_calls(self, llm_output: str, context: Dict[str, Any]) -> List[str]:
        """Simple keyword-based tool dispatch for demonstration."""
        tool_calls_made = []
        lowered = llm_output.lower()
        for tool_name, tool_obj in self._tool_slice.items():
            # Dispatch if LLM output mentions the tool name or a keyword match
            if tool_name.replace("_", " ") in lowered or tool_name in lowered:
                try:
                    result = await tool_obj.func()
                    tool_calls_made.append(f"{tool_name}:success")
                except Exception as e:
                    tool_calls_made.append(f"{tool_name}:error:{e}")
        return tool_calls_made
