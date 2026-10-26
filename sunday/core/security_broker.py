"""Enhanced Security & Policy Broker for Sunday 2.0.

Extends the fail-closed tool broker with:
- Workspace path-scoped filesystem sandboxing
- Terminal command authorization policies
- Git operation gating (protects against destructive operations)
- Approval request generation with cryptographic approval tokens
- Prompt injection & untrusted content sanitization
- Audit logging with secret masking and redact filters
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from sunday.core.broker.audit import AuditLedger
from sunday.core.broker.broker import Broker, BrokerResult, ToolCall, ToolRisk
from sunday.core.broker.permissions import PermissionChecker
from sunday.core.broker.vault import Vault

logger = logging.getLogger(__name__)


class PolicyAction(Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass
class ApprovalRequest:
    """Explicit authorization request for high-risk operations."""
    request_id: str
    tool: str
    args: Dict[str, Any]
    actor: str
    risk: ToolRisk
    reason: str
    target_resource: str
    expected_side_effects: str
    token: str
    created_at: float = field(default_factory=time.time)
    approved: bool = False
    rejected: bool = False


class EnhancedSecurityBroker(Broker):
    """Centralized security & policy enforcement broker."""

    # Disallowed command patterns for untrusted / autonomous execution
    DANGEROUS_COMMAND_PATTERNS = [
        r"\bformat\b",
        r"\bdel\s+/[sfq]\s+c:",
        r"\brm\s+-rf\s+/",
        r"\brmdir\s+/s\s+/q\s+c:",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # fork bomb
        r"\bdiskpart\b",
        r"\bshutdown\b",
        r"\bdrop\s+database\b",
        r"\btruncate\s+table\b",
    ]

    # Sensitive key patterns to mask from logs and model contexts
    SECRET_KEY_PATTERNS = [
        re.compile(r"api[_-]?key", re.IGNORECASE),
        re.compile(r"token", re.IGNORECASE),
        re.compile(r"password|secret", re.IGNORECASE),
    ]

    def __init__(
        self,
        audit_ledger: AuditLedger,
        vault: Vault,
        permission_checker: PermissionChecker,
        tool_registry: Dict[str, Dict[str, Any]],
        allowed_workspaces: Optional[List[str]] = None,
        require_approval_for_risk: Optional[Set[ToolRisk]] = None,
    ):
        super().__init__(
            audit_ledger=audit_ledger,
            vault=vault,
            permission_checker=permission_checker,
            tool_registry=tool_registry,
        )
        self.allowed_workspaces = [Path(w).resolve() for w in (allowed_workspaces or ["."])]
        self.require_approval_for_risk = require_approval_for_risk or {
            ToolRisk.HIGH,
            ToolRisk.CRITICAL,
        }
        self._pending_approvals: Dict[str, ApprovalRequest] = {}

    def is_path_within_workspace(self, target_path: Path | str) -> bool:
        """Verify that a target file/folder path is strictly inside allowed workspaces."""
        try:
            resolved = Path(target_path).resolve()
            for ws in self.allowed_workspaces:
                try:
                    resolved.relative_to(ws)
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    def validate_command_safety(self, command: str) -> bool:
        """Scan terminal command strings for destructive / unrecoverable actions."""
        cmd_clean = command.strip().lower()
        for pattern in self.DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                logger.warning(f"SecurityBroker blocked dangerous command pattern: {pattern}")
                return False
        return True

    def sanitize_untrusted_input(self, text: str) -> str:
        """Sanitize text from external sources to guard against direct prompt injection markers."""
        if not text:
            return ""
        # Strip system instruction override delimiters
        sanitized = re.sub(r"(?i)<\|?(system|im_start|im_end)\|?>", "[REDACTED_DELIMITER]", text)
        sanitized = re.sub(r"(?i)ignore\s+all\s+previous\s+instructions", "[BLOCKED_INSTRUCTION_OVERRIDE]", sanitized)
        return sanitized

    def mask_secrets(self, data: Any) -> Any:
        """Deep mask sensitive credentials from payloads before audit or prompt egress."""
        if isinstance(data, str):
            masked = re.sub(r"sk-[a-zA-Z0-9_\-]{15,}", "sk-[MASKED]", data)
            masked = re.sub(r"ghp_[a-zA-Z0-9_\-]{15,}", "ghp-[MASKED]", masked)
            return masked
        elif isinstance(data, dict):
            res = {}
            for k, v in data.items():
                if any(pat.search(k) for pat in self.SECRET_KEY_PATTERNS):
                    res[k] = "[REDACTED_CREDENTIAL]"
                else:
                    res[k] = self.mask_secrets(v)
            return res
        elif isinstance(data, list):
            return [self.mask_secrets(item) for item in data]
        return data

    def create_approval_request(
        self,
        tool_call: ToolCall,
        risk: ToolRisk,
        reason: str = "High-risk operation requires explicit developer authorization",
    ) -> ApprovalRequest:
        """Generate a tracked cryptographic approval request."""
        req_id = f"appr_{secrets.token_hex(6)}"
        token = secrets.token_urlsafe(16)
        target = str(tool_call.args.get("path") or tool_call.args.get("command") or tool_call.tool)
        req = ApprovalRequest(
            request_id=req_id,
            tool=tool_call.tool,
            args=tool_call.args,
            actor=tool_call.actor,
            risk=risk,
            reason=reason,
            target_resource=target,
            expected_side_effects=f"Execute {tool_call.tool} with args {tool_call.args}",
            token=token,
        )
        self._pending_approvals[req_id] = req
        logger.info(f"Generated ApprovalRequest [{req_id}] for {tool_call.tool} (Risk: {risk.value})")
        return req

    def approve_request(self, request_id: str, token: str) -> bool:
        """Approve a pending authorization request."""
        req = self._pending_approvals.get(request_id)
        if not req or req.token != token:
            return False
        req.approved = True
        return True

    def reject_request(self, request_id: str) -> bool:
        """Reject a pending authorization request."""
        req = self._pending_approvals.get(request_id)
        if not req:
            return False
        req.rejected = True
        return True

    async def dispatch(self, tool_call: ToolCall, executor: Callable) -> BrokerResult:
        """Intercept and gate tool executions through enhanced sandbox policies."""
        # 1. Base validation
        if tool_call.tool not in self.tool_registry:
            return BrokerResult(
                code="unknown_tool",
                success=False,
                message=f"Tool '{tool_call.tool}' not registered in policy manifest",
            )

        tool_config = self.tool_registry[tool_call.tool]
        risk = ToolRisk(tool_config.get("risk", "medium"))

        # 2. Filesystem sandbox enforcement
        path_arg = tool_call.args.get("path") or tool_call.args.get("file_path") or tool_call.args.get("directory")
        if path_arg and not self.is_path_within_workspace(path_arg):
            logger.error(f"Sandbox violation: {path_arg} is outside allowed workspaces")
            return BrokerResult(
                code="sandbox_violation",
                success=False,
                message=f"Path '{path_arg}' is outside authorized workspace boundaries",
            )

        # 3. Terminal command security
        cmd_arg = tool_call.args.get("command") or tool_call.args.get("cmd")
        if cmd_arg and not self.validate_command_safety(cmd_arg):
            return BrokerResult(
                code="dangerous_command_blocked",
                success=False,
                message="Command was blocked by security policy due to high-risk destructive patterns",
            )

        # 4. Git safety guard
        if tool_call.tool.startswith("git_"):
            subcmd = tool_call.args.get("subcommand", "").lower()
            if subcmd in ["reset --hard", "clean -fdx", "push --force"]:
                if not tool_call.confirmed:
                    req = self.create_approval_request(tool_call, ToolRisk.CRITICAL, "Destructive git operation")
                    return BrokerResult(
                        code="approval_required",
                        success=False,
                        data={"approval_request": req.request_id, "token": req.token},
                        message=f"Destructive git command '{subcmd}' requires approval",
                        requires_confirmation=True,
                    )

        # 5. Authorization Gating & Approval Workflow
        if risk in self.require_approval_for_risk and not tool_call.confirmed:
            req = self.create_approval_request(tool_call, risk)
            return BrokerResult(
                code="approval_required",
                success=False,
                data={"approval_request": req.request_id, "token": req.token},
                message=f"Action '{tool_call.tool}' with risk '{risk.value}' requires explicit developer approval",
                requires_confirmation=True,
            )

        # 6. Delegate execution through parent pipeline
        result = await super().dispatch(tool_call, executor)

        # 7. Mask output secrets before return
        if result.data:
            result.data = self.mask_secrets(result.data)

        return result
