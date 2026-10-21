"""
Main Orchestrator for Sunday.
Routes user input, manages intent, context, and integrations.
"""
import logging
from enum import Enum
from typing import List, Dict, Any

# Ensure graceful fallback if missing
try:
    from ollama import AsyncClient
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

from .planner import TaskPlanner
from .tool_rag import ToolRAG
from .approval import ApprovalBroker, RiskLevel
# Assume these are available or will be
# from ..config import Settings, PersonaManager
# from ..tools import ToolRegistry

class IntentCategory(Enum):
    TOOL_CALL = "tool_call"
    CONVERSATION = "conversation"
    REFLECTIVE_CHAT = "reflective_chat"
    SYSTEM_COMMAND = "system_command"

class IntentJudge:
    """Classifies user intent into one of the IntentCategory enum values."""
    def __init__(self):
        if HAS_OLLAMA:
            self.client = AsyncClient()
            
    async def classify(self, user_input: str) -> IntentCategory:
        # Simple heuristic fallback
        lowered = user_input.lower()
        if any(w in lowered for w in ["search", "run", "do", "execute", "turn on", "find"]):
            return IntentCategory.TOOL_CALL
        if "reflect" in lowered or "talk about my feelings" in lowered or "pi" in lowered:
            return IntentCategory.REFLECTIVE_CHAT
        if "system" in lowered or "shutdown" in lowered:
            return IntentCategory.SYSTEM_COMMAND
        return IntentCategory.CONVERSATION

class Orchestrator:
    def __init__(self, settings=None, persona_manager=None, tool_registry=None):
        self.settings = settings
        self.persona_manager = persona_manager
        self.tool_registry = tool_registry
        
        self.intent_judge = IntentJudge()
        self.tool_rag = ToolRAG()
        self.approval_broker = ApprovalBroker()
        self.planner = TaskPlanner(tool_registry, self.approval_broker)
        
        self.history: List[Dict[str, str]] = []
        self.logger = logging.getLogger(__name__)
        
        if HAS_OLLAMA:
            self.llm = AsyncClient()
            
    async def process(self, text: str) -> str:
        """Main entry point for user text/transcribed voice."""
        self.history.append({"role": "user", "content": text})
        
        intent = await self.intent_judge.classify(text)
        self.logger.info(f"Classified intent as: {intent.value}")
        
        response_text = ""
        
        if intent == IntentCategory.TOOL_CALL:
            response_text = await self._handle_tool_call(text)
        elif intent == IntentCategory.REFLECTIVE_CHAT:
            response_text = await self._handle_reflective_chat(text)
        elif intent == IntentCategory.SYSTEM_COMMAND:
            response_text = await self._handle_system_command(text)
        else:
            response_text = await self._handle_conversation(text)
            
        self.history.append({"role": "assistant", "content": response_text})
        return response_text
    
    async def process_input(self, text: str) -> str:
        """Alias for process() for backward compatibility."""
        return await self.process(text)
        
    async def _handle_tool_call(self, text: str) -> str:
        # 1. RAG to find tools
        tools = await self.tool_rag.retrieve_tools(text)
        # 2. Plan
        plan = await self.planner.create_plan(text, tools)
        if not plan:
            return "I couldn't figure out how to do that with my tools."
        # 3. Execute
        results = await self.planner.execute_plan(plan)
        return f"I executed a plan. Results: {results}"
        
    async def _handle_reflective_chat(self, text: str) -> str:
        # Switch to PI-like persona
        system_prompt = "You are Pi, a gentle, reflective, and empathetic AI."
        return await self._generate_response(text, system_prompt)
        
    async def _handle_conversation(self, text: str) -> str:
        # Use active persona
        system_prompt = "You are a helpful AI."
        if self.persona_manager:
            system_prompt = self.persona_manager.get_current_persona().system_prompt
        return await self._generate_response(text, system_prompt)
        
    async def _handle_system_command(self, text: str) -> str:
        return "System command received."
        
    async def _generate_response(self, text: str, system_prompt: str) -> str:
        if not HAS_OLLAMA:
            return "Ollama is not available to generate a response."
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.history[-5:])
        
        try:
            # Query installed models dynamically
            models_resp = await self.llm.list()
            available = [m.model for m in models_resp.models]
            chosen = "llama3.2:1b"
            for candidate in ["llama3.2:1b", "llama3.2:3b", "llama3.2", "llama3.1", "phi3"]:
                if any(candidate in m for m in available):
                    chosen = next(m for m in available if candidate in m)
                    break
            if not chosen and available:
                chosen = available[0]

            response = await self.llm.chat(model=chosen, messages=messages)
            return response['message']['content']
        except Exception as e:
            self.logger.error(f"LLM Error: {e}")
            return "I'm having trouble connecting to my brain right now."
