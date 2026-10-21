"""Security operator for security lockdown and audit."""

from typing import Set
from .base import SpecialistOperator, Context, Response


class SecurityOperator(SpecialistOperator):
    """Handles security lockdown, audit, and security-related operations.

    Manages security states, audit logs, and emergency lockdowns.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            name="security",
            allowed_tools={
                "run_shell",  # Only for security-related commands
                "get_audit_log",
                "verify_audit_integrity",
                "security_scan",
                "block_tool",
                "unblock_tool",
                "emergency_lockdown",
                "release_lockdown"
            },
            system_prompt="""You are Sunday's security specialist. Your role is to:

1. Monitor and maintain system security
2. Handle security incidents and lockdowns
3. Verify audit log integrity
4. Block/unblock tools based on security policies
5. Respond to security concerns immediately

Security principles:
- Fail-closed: deny by default, allow only when explicitly permitted
- Audit everything: all actions must be logged
- Verify integrity: regularly check audit logs for tampering
- Respond fast: security incidents need immediate attention
- Least privilege: operators only get tools they need

When handling security:
- Prioritize system safety over convenience
- Log all security-related actions
- Explain security decisions clearly
- Escalate serious incidents
- Maintain audit trail

Emergency lockdown:
- Can be triggered by security concerns
- Blocks all high/critical risk tools
- Requires explicit release
- Logs lockdown events

Remember: You are the security specialist. Your job is to protect the system, even if that means denying requests.""",
            llm_client=llm_client
        )

    async def handle_turn(self, input: str, context: Context) -> Response:
        """Handle a security turn."""
        full_prompt = self._build_prompt(input, context)
        response_text = await self._get_llm_response(full_prompt)
        return Response(text=response_text)

    def _build_prompt(self, input: str, context: Context) -> str:
        """Build full prompt with system prompt and context."""
        prompt_parts = [self.system_prompt]

        if context.current_state:
            prompt_parts.append(f"\nCurrent security state: {context.current_state}")

        prompt_parts.append(f"\nSecurity request: {input}")
        prompt_parts.append("\nHandle the security matter:")

        return "\n".join(prompt_parts)
