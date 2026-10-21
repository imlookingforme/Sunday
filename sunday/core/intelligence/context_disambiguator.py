"""Context Disambiguator - Resolves ambiguous user turns using memory and conversation history."""

import logging
from typing import Any

from sunday.core.operators.base import ConversationMode

logger = logging.getLogger(__name__)


class ContextDisambiguator:
    """Disambiguates vague queries ('run it', 'do the thing', 'check') using memory and turn history."""

    AMBIGUOUS_PATTERNS = [
        "run it",
        "do it",
        "do the thing",
        "start it",
        "stop it",
        "check",
        "check it",
        "what about that",
        "again",
        "repeat",
        "show me",
    ]

    def __init__(self, titans_memory: Any | None = None, vector_store: Any | None = None):
        self.titans_memory = titans_memory
        self.vector_store = vector_store

    def is_ambiguous(self, text: str, confidence: float) -> bool:
        """Determines whether a query is ambiguous and requires contextual resolution."""
        lowered = text.lower().strip()
        if lowered in self.AMBIGUOUS_PATTERNS:
            return True
        if len(lowered.split()) <= 3 and confidence < 0.65:
            return True
        return False

    async def disambiguate(
        self,
        text: str,
        initial_mode: ConversationMode,
        confidence: float,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[ConversationMode, str]:
        """Resolves intent by inspecting conversational history and Titans memory episodes.

        Returns:
            Tuple of (resolved_mode, context_hint)
        """
        if not self.is_ambiguous(text, confidence):
            return initial_mode, "Direct classification"

        # 1. Check immediate conversational history (last 5 turns)
        if history:
            for turn in reversed(history[-5:]):
                content = turn.get("content", "").lower()
                if any(w in content for w in ["script", "code", "file", "test", "build", "debug"]):
                    return (
                        ConversationMode.AUTOMATION,
                        f"Resolved from conversation topic: '{content[:30]}...'",
                    )
                if any(w in content for w in ["volume", "window", "brightness", "screen", "music"]):
                    return (
                        ConversationMode.DEVICE_CONTROL,
                        f"Resolved from media topic: '{content[:30]}...'",
                    )
                if any(w in content for w in ["paper", "research", "search", "explain", "learn"]):
                    return (
                        ConversationMode.RESEARCH,
                        f"Resolved from research topic: '{content[:30]}...'",
                    )
                if any(w in content for w in ["deadline", "todo", "task", "focus", "study"]):
                    return (
                        ConversationMode.ALERTING,
                        f"Resolved from task topic: '{content[:30]}...'",
                    )

        # 2. Check Titans Memory recent episodes
        if self.titans_memory and hasattr(self.titans_memory, "recall"):
            try:
                episodes = await self.titans_memory.recall(text, top_k=2)
                if episodes:
                    top_ep = episodes[0]
                    content = top_ep.content.lower()
                    if "automation" in content or "script" in content:
                        return ConversationMode.AUTOMATION, "Resolved from recent episodic memory"
                    if "research" in content or "scout" in content:
                        return ConversationMode.RESEARCH, "Resolved from memory recall"
            except Exception as e:
                logger.debug(f"Error querying Titans memory for disambiguation: {e}")

        # Default fallback
        return initial_mode, "Kept initial mode"
