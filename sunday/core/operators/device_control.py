"""Device control operator for smart home and device management."""

from typing import Set
from .base import SpecialistOperator, Context, Response


class DeviceControlOperator(SpecialistOperator):
    """Handles device control and smart home automation.

    Manage devices, smart home integration, and hardware control.
    """

    def __init__(self, llm_client=None):
        super().__init__(
            name="device_control",
            allowed_tools={
                "set_volume",
                "play_sound_effect",
                "system_stats",
                "get_active_window",
                "switch_window",
                "screenshot_window",
                "home_assistant_call",
                "home_assistant_get_state",
                "media_play",
                "media_pause",
                "media_next",
                "media_previous"
            },
            system_prompt="""You are Sunday's device control specialist. Your role is to:

1. Control devices and smart home systems
2. Manage media playback
3. Monitor system status
4. Handle window management
5. Provide feedback on device states

Device control principles:
- Always confirm state changes before executing
- Check current state before making changes
- Provide clear feedback on what changed
- Handle device unavailability gracefully
- Group related actions for efficiency

When controlling devices:
- Describe what you're doing
- Confirm the action completed
- Report any issues
- Suggest alternatives if something fails

Remember: You control devices, not execute arbitrary commands. Use the specific device control tools available.""",
            llm_client=llm_client
        )

    async def handle_turn(self, input: str, context: Context) -> Response:
        """Handle a device control turn."""
        full_prompt = self._build_prompt(input, context)
        response_text = await self._get_llm_response(full_prompt)
        return Response(text=response_text)

    def _build_prompt(self, input: str, context: Context) -> str:
        """Build full prompt with system prompt and context."""
        prompt_parts = [self.system_prompt]

        if context.current_state:
            prompt_parts.append(f"\nCurrent device states: {context.current_state}")

        prompt_parts.append(f"\nDevice control request: {input}")
        prompt_parts.append("\nExecute the device control:")

        return "\n".join(prompt_parts)
