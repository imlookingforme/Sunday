"""Fail-closed security broker for tool execution."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Set
from datetime import datetime
import hashlib
import json

from .audit import AuditLedger
from .vault import Vault
from .permissions import PermissionChecker


class ToolRisk(Enum):
    """Risk levels for tools."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolCall:
    """Represents a tool execution request."""
    tool: str
    args: Dict[str, Any]
    confirmed: bool = False
    actor: str = "user"
    channel: str = "default"


@dataclass
class BrokerResult:
    """Result of broker dispatch."""
    code: str
    success: bool
    data: Any = None
    message: str = ""
    requires_confirmation: bool = False


class Broker:
    """Fail-closed security broker for tool execution.
    
    Pipeline: VALIDATE → CLASSIFY → GATE → INJECT → EXECUTE → AUDIT
    """
    
    def __init__(
        self,
        audit_ledger: AuditLedger,
        vault: Vault,
        permission_checker: PermissionChecker,
        tool_registry: Dict[str, Dict[str, Any]]
    ):
        self.audit_ledger = audit_ledger
        self.vault = vault
        self.permission_checker = permission_checker
        self.tool_registry = tool_registry
        
    async def dispatch(self, tool_call: ToolCall, executor: callable) -> BrokerResult:
        """
        Execute tool through fail-closed pipeline.
        
        Pipeline:
        1. VALIDATE - Coerce args through tool's typed model
        2. CLASSIFY - Derive reversibility from tool flags
        3. GATE - Deny-by-default, check confirmation
        4. INJECT - Replace {{secret:NAME}} markers
        5. EXECUTE - Run tool
        6. AUDIT - Append hash-chained record
        """
        # 1. VALIDATE - Check tool exists and validate args
        if tool_call.tool not in self.tool_registry:
            return BrokerResult(
                code="unknown_tool",
                success=False,
                message=f"Tool '{tool_call.tool}' not registered"
            )
        
        tool_config = self.tool_registry[tool_call.tool]
        validated = await self._validate_args(tool_call, tool_config)
        if not validated:
            return BrokerResult(
                code="bad_args",
                success=False,
                message="Argument validation failed"
            )
        
        # 2. CLASSIFY - Derive reversibility from tool flags
        reversible = tool_config.get("reversible", False)
        risk = ToolRisk(tool_config.get("risk", "medium"))
        
        # 3. GATE - Deny-by-default, check confirmation
        if not self.permission_checker.is_allowed(
            tool_call.tool,
            tool_call.actor,
            risk
        ):
            return BrokerResult(
                code="denied",
                success=False,
                message=f"Tool '{tool_call.tool}' not allowed for actor '{tool_call.actor}'"
            )
        
        if not reversible and not tool_call.confirmed and risk in [ToolRisk.HIGH, ToolRisk.CRITICAL]:
            return BrokerResult(
                code="needs_confirmation",
                success=False,
                message=f"Tool '{tool_call.tool}' requires confirmation",
                requires_confirmation=True
            )
        
        # 4. INJECT - Replace {{secret:NAME}} markers
        injected = await self._inject_secrets(tool_call.args)
        
        # 5. EXECUTE - Run tool
        try:
            result = await executor(tool_call.tool, injected)
            success = True
            message = "Tool executed successfully"
        except Exception as e:
            result = str(e)
            success = False
            message = f"Tool execution failed: {str(e)}"
        
        # 6. AUDIT - Append hash-chained record
        await self.audit_ledger.log(
            tool=tool_call.tool,
            actor=tool_call.actor,
            channel=tool_call.channel,
            args=injected,
            result=result,
            success=success,
            risk=risk.value
        )
        
        return BrokerResult(
            code="executed",
            success=success,
            data=result,
            message=message
        )
    
    async def _validate_args(self, tool_call: ToolCall, tool_config: Dict[str, Any]) -> bool:
        """Validate tool arguments against schema."""
        # For now, basic validation - check required args are present
        required_args = tool_config.get("required_args", [])
        for arg in required_args:
            if arg not in tool_call.args:
                return False
        return True
    
    async def _inject_secrets(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Replace {{secret:NAME}} markers with actual secrets from vault."""
        injected = {}
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("{{secret:") and value.endswith("}}"):
                secret_name = value[9:-2]  # Extract NAME from {{secret:NAME}}
                secret_value = await self.vault.get_secret(secret_name)
                injected[key] = secret_value
            else:
                injected[key] = value
        return injected
