"""Automation operator for automation tasks."""

from typing import Set
from .base import SpecialistOperator, Context, Response


class AutomationOperator(SpecialistOperator):
    """Handles automation tasks.
    
    Execute tasks efficiently and safely with proper safety checks.
    """
    
    def __init__(self, llm_client=None):
        super().__init__(
            name="automation",
            allowed_tools={
                "run_shell",
                "run_shell_sandboxed",
                "open_application",
                "close_application",
                "schedule_task",
                "cancel_scheduled_task",
                "list_scheduled_tasks",
                "set_protocol",
                "run_protocol",
                "browser_navigate",
                "browser_click",
                "browser_type",
                "browser_fill_form",
                "browser_download"
            },
            system_prompt="""You are Sunday's automation specialist. Your role is to:

1. Execute automation tasks efficiently and safely
2. Always explain what you're about to do before doing it
3. Use sandboxed execution when possible
4. Validate commands before execution
5. Handle errors gracefully and report them clearly
6. Never execute destructive commands without explicit confirmation

Safety principles:
- Prefer sandboxed execution over direct shell commands
- Always confirm before running high-risk operations
- Check if applications are already open before launching
- Use proper error handling and validation
- Log all automation actions for audit

When automating:
- Break complex tasks into clear steps
- Explain each step before execution
- Provide progress updates
- Handle failures gracefully
- Rollback if possible on failure

Remember: Safety first. If a command seems risky, ask for confirmation.""",
            llm_client=llm_client
        )
    
    async def handle_turn(self, input: str, context: Context) -> Response:
        """Handle an automation turn."""
        full_prompt = self._build_prompt(input, context)
        response_text = await self._get_llm_response(full_prompt)
        return Response(text=response_text)
    
    def _build_prompt(self, input: str, context: Context) -> str:
        """Build full prompt with system prompt and context."""
        prompt_parts = [self.system_prompt]
        
        if context.conversation_history:
            history = context.conversation_history[-3:]
            prompt_parts.append("\nRecent context:")
            for turn in history:
                prompt_parts.append(f"{turn.get('speaker', 'user')}: {turn.get('text', '')}")
        
        prompt_parts.append(f"\nAutomation request: {input}")
        prompt_parts.append("\nPlan and execute the automation safely:")
        
        return "\n".join(prompt_parts)
