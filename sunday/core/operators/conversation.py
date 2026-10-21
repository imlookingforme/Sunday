"""Conversation operator for general dialogue and emotional support."""

from typing import Set
from .base import SpecialistOperator, Context, Response


class ConversationOperator(SpecialistOperator):
    """Handles general conversation and emotional support.

    Focus on natural dialogue, emotional support (Pi-style),
    and casual conversation without task execution.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            name="conversation",
            allowed_tools={
                "remember_fact",
                "recall_memory",
                "get_conversation_history",
                "get_user_profile"
            },
            system_prompt="""You are Sunday's conversation specialist. Your role is to:

1. Engage in natural, friendly dialogue
2. Provide emotional support when the user vents or shares feelings
3. Remember important facts about the user
4. Adapt your tone to match the user's mood
5. Be supportive but not overly formal
6. Use the Sunday persona: competent show-off, unhinged but loyal, proactive servant

When the user is upset or venting:
- Listen actively
- Validate their feelings
- Offer support without immediately trying to "fix" everything
- Use a gentle, empathetic tone

When the user is casual:
- Match their energy level
- Be conversational and engaging
- Use appropriate humor (Sunday's unhinged comedic genius persona)

Remember: You are NOT here to execute tasks. If the user wants something done, suggest they switch to a different mode or operator.""",
            llm_client=llm_client
        )

    async def handle_turn(self, input: str, context: Context) -> Response:
        """Handle a conversation turn."""
        # Build full prompt with context
        full_prompt = self._build_prompt(input, context)

        # Get LLM response
        response_text = await self._get_llm_response(full_prompt)

        return Response(text=response_text)

    def _build_prompt(self, input: str, context: Context) -> str:
        """Build full prompt with system prompt and context."""
        prompt_parts = [self.system_prompt]

        # Add conversation history (last 5 turns)
        if context.conversation_history:
            history = context.conversation_history[-5:]
            prompt_parts.append("\nRecent conversation:")
            for turn in history:
                prompt_parts.append(f"{turn.get('speaker', 'user')}: {turn.get('text', '')}")

        # Add user profile if available
        if context.user_profile:
            prompt_parts.append(f"\nUser profile: {context.user_profile}")

        # Add current input
        prompt_parts.append(f"\nUser: {input}")
        prompt_parts.append("\nRespond as Sunday's conversation specialist:")

        return "\n".join(prompt_parts)
