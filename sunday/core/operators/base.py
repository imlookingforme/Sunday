"""Base class for specialist operators."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Set, Dict, Any, Optional


class ConversationMode(Enum):
    """Conversation modes for routing."""
    CONVERSATION = "conversation"
    RESEARCH = "research"
    AUTOMATION = "automation"
    DEVICE_CONTROL = "device_control"
    ALERTING = "alerting"
    SECURITY_LOCKDOWN = "security_lockdown"
    CLARIFY = "clarify"


@dataclass
class Context:
    """Context for operator execution."""
    user_input: str
    conversation_history: list
    user_profile: dict
    current_state: dict


@dataclass
class Response:
    """Response from operator."""
    text: str
    tool_calls: list = None
    metadata: dict = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []
        if self.metadata is None:
            self.metadata = {}


class SpecialistOperator(ABC):
    """Base class for specialist operators with least-privilege tool slices."""

    def __init__(
        self,
        name: str,
        allowed_tools: Set[str],
        system_prompt: str,
        llm_client=None
    ):
        """Initialize specialist operator.

        Args:
            name: Operator name
            allowed_tools: Set of tools this operator can use (least-privilege)
            system_prompt: System prompt for this operator
            llm_client: LLM client for generation
        """
        self.name = name
        self.allowed_tools = allowed_tools
        self.system_prompt = system_prompt
        self.llm_client = llm_client
        self.memory_namespace = f"memory_{name}"

    @abstractmethod
    async def handle_turn(self, input: str, context: Context) -> Response:
        """Handle a conversation turn.

        Args:
            input: User input
            context: Execution context

        Returns:
            Response with text and optional tool calls
        """
        pass

    async def _get_llm_response(
        self,
        prompt: str,
        tools: Optional[list] = None
    ) -> str:
        """Get LLM response with tool access restricted to allowed_tools.

        Args:
            prompt: Full prompt including system prompt
            tools: Tool schemas to include

        Returns:
            LLM response text
        """
        if not self.llm_client:
            return "LLM client not configured"

        # Filter tools to only allowed tools
        if tools:
            allowed_tool_schemas = [
                t for t in tools
                if t.get("name") in self.allowed_tools
            ]
        else:
            allowed_tool_schemas = None

        try:
            response = await self.llm_client.generate(
                model="llama3.1",
                prompt=prompt,
                tools=allowed_tool_schemas
            )
            return response.get("response", "")
        except Exception as e:
            return f"Error getting LLM response: {str(e)}"

    def can_use_tool(self, tool_name: str) -> bool:
        """Check if operator is allowed to use a tool."""
        return tool_name in self.allowed_tools

    def get_tool_schemas(self, tool_registry: Dict[str, Any]) -> list:
        """Get tool schemas for allowed tools only."""
        schemas = []
        for tool_name in self.allowed_tools:
            if tool_name in tool_registry:
                schemas.append(tool_registry[tool_name])
        return schemas
