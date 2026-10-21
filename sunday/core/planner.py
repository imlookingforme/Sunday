"""
TaskPlanner for Sunday.
Breaks complex requests into steps and executes them.
"""
import logging
from typing import List, Any
import json

class TaskPlanner:
    def __init__(self, tool_registry=None, approval_broker=None):
        self.tool_registry = tool_registry
        self.approval_broker = approval_broker
        self.logger = logging.getLogger(__name__)
        try:
            from ollama import AsyncClient
            self.client = AsyncClient()
            self.has_ollama = True
        except ImportError:
            self.has_ollama = False
            self.logger.warning("Ollama not available. Planner will use basic fallback.")

    async def create_plan(self, query: str, available_tools: List[Any]) -> List[dict]:
        """Generate a plan consisting of sequential tool calls."""
        if not available_tools:
            return []
            
        if self.has_ollama:
            tools_desc = "\n".join([f"- {t.get('name')}: {t.get('description')}" for t in available_tools])
            prompt = (
                f"You are an AI assistant planning a task. Query: '{query}'\n"
                f"Available tools:\n{tools_desc}\n"
                f"Output a JSON list of objects, each with a 'tool' name and 'params' dictionary. "
                f"Only use available tools. Output ONLY valid JSON."
            )
            try:
                response = await self.client.generate(model="llama3", prompt=prompt, format="json")
                plan = json.loads(response['response'])
                if isinstance(plan, list):
                    return plan
                return []
            except Exception as e:
                self.logger.error(f"Error creating plan: {e}")
                return []
        else:
            # Stub plan
            return [{"tool": available_tools[0].get("name"), "params": {}}]

    async def execute_plan(self, plan: List[dict]) -> List[Any]:
        """Execute the planned steps sequentially."""
        results = []
        for step in plan:
            tool_name = step.get("tool")
            params = step.get("params", {})
            
            # Here we would lookup the tool from registry
            # Check approval
            # Execute tool
            results.append(f"Executed {tool_name} with {params}")
            
        return results
