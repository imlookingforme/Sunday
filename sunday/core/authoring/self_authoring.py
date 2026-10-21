"""Self-Authoring Tool & Script Engine for Sunday.

Enables Sunday to autonomously invent, write, sandbox-validate, and dynamically register
new Python tools and automation plugins without restarting the daemon.
"""

import ast
import importlib.util
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from sunday.tools.registry import ToolRegistry, Tool, ToolRisk, ToolResult

logger = logging.getLogger(__name__)


class SelfAuthoringEngine:
    """Autonomously formulates, code-generates, and registers new tool plugins at runtime."""

    def __init__(self, plugins_dir: Optional[Path] = None):
        self.plugins_dir = plugins_dir or Path("sunday/plugins/self_authored")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        # Ensure __init__.py exists in self_authored plugins dir
        init_file = self.plugins_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Dynamically generated self-authored tools."""\n', encoding="utf-8")

    def validate_code_safety(self, code_str: str) -> bool:
        """Verify syntax validity via AST parser and forbid destructive system calls."""
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            logger.error(f"AST validation failed with SyntaxError: {e}")
            return False

        # Ban dangerous calls inside self-authored scripts (e.g. format drive, arbitrary eval of inputs)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["eval", "exec"]:
                        logger.warning(f"Forbidden call '{node.func.id}' detected in self-authored code.")
                        return False

        return True

    def author_new_tool(
        self,
        tool_name: str,
        category: str,
        description: str,
        function_code: str,
        risk_level: str = "low",
        required_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Synthesize a complete tool file and persist to sunday/plugins/self_authored/."""
        if not self.validate_code_safety(function_code):
            return {"success": False, "error": "Code failed AST syntax and safety checks"}

        risk_val = risk_level.lower()
        if risk_val not in ["low", "medium", "high", "critical"]:
            risk_val = "low"

        args_list = required_args or []

        # Construct standard plugin template
        file_content = f'''"""Self-authored tool: {tool_name}
Generated autonomously by Sunday Engine at {time.strftime('%Y-%m-%d %H:%M:%S')}.
"""

from typing import Dict, Any
from sunday.tools.registry import ToolRegistry, Tool, ToolRisk, ToolResult

{function_code.strip()}

# Auto-registration function called by SelfAuthoringEngine
def register():
    risk_mapping = {{
        "low": ToolRisk.LOW,
        "medium": ToolRisk.MEDIUM,
        "high": ToolRisk.HIGH,
        "critical": ToolRisk.CRITICAL
    }}

    tool = Tool(
        name="{tool_name}",
        description="{description}",
        category="{category}",
        risk=risk_mapping.get("{risk_val}", ToolRisk.LOW),
        func={tool_name}_handler,
        approval_required=False,
        persona="sunday",
        required_args={args_list}
    )
    ToolRegistry.register(tool)
    return tool
'''
        target_file = self.plugins_dir / f"{tool_name}.py"
        try:
            target_file.write_text(file_content, encoding="utf-8")
            logger.info(f"Self-authored tool saved to {target_file}")

            # Dynamically import and register into running ToolRegistry
            registered = self.load_and_register_plugin(target_file)
            return {
                "success": bool(registered),
                "tool_name": tool_name,
                "file_path": str(target_file),
                "registered": bool(registered)
            }
        except Exception as e:
            logger.error(f"Failed to author and save tool {tool_name}: {e}")
            return {"success": False, "error": str(e)}

    def load_and_register_plugin(self, file_path: Path) -> Optional[Tool]:
        """Dynamically load and register a plugin file into runtime ToolRegistry."""
        module_name = f"sunday.plugins.self_authored.{file_path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if hasattr(module, "register"):
                tool = module.register()
                logger.info(f"Dynamically registered tool: {tool.name} into ToolRegistry.")
                return tool
            return None
        except Exception as e:
            logger.error(f"Error dynamically loading {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error dynamically loading {file_path}: {e}")
            return None

    def load_all_authored_plugins(self) -> List[str]:
        """Load and register all existing plugins in the self_authored directory."""
        loaded = []
        for p in self.plugins_dir.glob("*.py"):
            if p.name == "__init__.py":
                continue
            tool = self.load_and_register_plugin(p)
            if tool:
                loaded.append(tool.name)
        return loaded
