import inspect
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any, Optional

class ToolRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ToolResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Tool:
    name: str
    description: str
    func: Callable
    risk: ToolRisk
    approval_required: bool
    persona: str
    category: str
    reversible: bool = True
    idempotent: bool = True
    allowed_personas: List[str] = None
    required_args: List[str] = None

    def __post_init__(self):
        if self.allowed_personas is None:
            self.allowed_personas = ["sunday", "jarvis", "friday"]
        if self.required_args is None:
            self.required_args = []

class ToolRegistry:
    _tools: Dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool):
        cls._tools[tool.name] = tool

    @classmethod
    def get(cls, name: str) -> Optional[Tool]:
        return cls._tools.get(name)

    @classmethod
    def list_by_category(cls, category: str) -> List[Tool]:
        return [t for t in cls._tools.values() if t.category == category]

    @classmethod
    def list_by_risk(cls, risk: ToolRisk) -> List[Tool]:
        return [t for t in cls._tools.values() if t.risk == risk]

    @classmethod
    def search_tools(cls, query: str) -> List[Tool]:
        query = query.lower()
        return [t for t in cls._tools.values() if query in t.name.lower() or query in t.description.lower()]

    @classmethod
    def get_all(cls) -> List[Tool]:
        return list(cls._tools.values())

def tool(name: str, risk: ToolRisk = ToolRisk.LOW, category: str = 'general', description: str = '', approval: bool = False, persona: str = 'both', reversible: bool = True, idempotent: bool = True, allowed_personas: List[str] = None, required_args: List[str] = None):
    def decorator(func):
        t = Tool(
            name=name,
            description=description or func.__doc__ or "",
            func=func,
            risk=risk,
            approval_required=approval,
            persona=persona,
            category=category,
            reversible=reversible,
            idempotent=idempotent,
            allowed_personas=allowed_personas,
            required_args=required_args
        )
        ToolRegistry.register(t)
        return func
    return decorator
