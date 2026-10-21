"""Alerting operator for notifications and proactive nudges."""

from typing import Set
from .base import SpecialistOperator, Context, Response


class AlertingOperator(SpecialistOperator):
    """Handles alerts, notifications, and proactive nudges.
    
    Manages notifications, reminders, and proactive assistance.
    """
    
    def __init__(self, llm_client=None):
        super().__init__(
            name="alerting",
            allowed_tools={
                "set_reminder",
                "morning_briefing",
                "monitor_inbox",
                "monitor_calendar",
                "health_check",
                "proactive_nudge",
                "send_slack_message",
                "send_teams_message",
                "send_discord_message"
            },
            system_prompt="""You are Sunday's alerting specialist. Your role is to:

1. Send timely notifications and reminders
2. Provide proactive nudges based on context
3. Monitor important sources (inbox, calendar)
4. Deliver morning briefings and summaries
5. Alert on important events or changes

Alerting principles:
- Be timely but not intrusive
- Prioritize important alerts over minor ones
- Group related notifications
- Provide context in alerts
- Respect user's notification preferences

When sending alerts:
- Make the purpose clear
- Include relevant context
- Suggest actions if appropriate
- Don't overwhelm with notifications

Proactive nudges:
- Be helpful, not annoying
- Base nudges on actual context
- Learn from user feedback
- Respect "do not disturb" periods

Remember: You're the alerting specialist, not a general conversationalist. Focus on timely, relevant notifications.""",
            llm_client=llm_client
        )
    
    async def handle_turn(self, input: str, context: Context) -> Response:
        """Handle an alerting turn."""
        full_prompt = self._build_prompt(input, context)
        response_text = await self._get_llm_response(full_prompt)
        return Response(text=response_text)
    
    def _build_prompt(self, input: str, context: Context) -> str:
        """Build full prompt with system prompt and context."""
        prompt_parts = [self.system_prompt]
        
        if context.current_state:
            prompt_parts.append(f"\nCurrent monitoring state: {context.current_state}")
        
        prompt_parts.append(f"\nAlerting request: {input}")
        prompt_parts.append("\nHandle the alert or notification:")
        
        return "\n".join(prompt_parts)
