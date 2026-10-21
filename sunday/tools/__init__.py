from .registry import ToolRegistry, Tool, ToolResult, ToolRisk, tool
from .base import BaseTool

_SUBMODULES = [
    "voice", "tasks", "memory_tools", "writing", "web", "system",
    "productivity", "scheduling", "vision", "research", "browser",
    "coding", "artifacts", "custom_agents", "home"
]

def __getattr__(name: str):
    if name in _SUBMODULES:
        import importlib
        module = importlib.import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ToolRegistry",
    "Tool",
    "ToolResult",
    "ToolRisk",
    "tool",
    "BaseTool",
    *_SUBMODULES
]

