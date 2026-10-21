"""Proactive Suggestion Engine - Generates unprompted, habit-aligned suggestions as Conductor nudges."""

import logging
from datetime import datetime
from typing import Any

from sunday.core.intelligence.pattern_learner import PatternLearner

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """Proactively anticipates user intentions and crafts tailored suggestions."""

    def __init__(self, pattern_learner: PatternLearner | None = None, swarm_bus: Any | None = None):
        self.pattern_learner = pattern_learner or PatternLearner()
        self.swarm_bus = swarm_bus
        self.last_suggestion: dict[str, Any] | None = None
        self.cooldown_seconds = 300  # 5 min between proactive nudges
        self.last_suggested_at: datetime | None = None

    async def generate_suggestion(
        self,
        recent_intent: str | None = None,
        context: dict[str, Any] | None = None,
        force: bool = False,
    ) -> dict[str, Any] | None:
        """Evaluates temporal and sequential habits to formulate a suggestion."""
        now = datetime.now()

        # Check cooldown (unless force is requested)
        if not force and self.last_suggested_at:
            delta = (now - self.last_suggested_at).total_seconds()
            if delta < self.cooldown_seconds:
                return None

        # 1. Sequential Suggestion: "You just checked deadlines... want to start a 25m Focus Sprint?"
        if recent_intent:
            next_habit = await self.pattern_learner.get_sequential_pattern(recent_intent)
            if next_habit:
                suggestion = self._craft_sequential_suggestion(recent_intent, next_habit)
                if suggestion:
                    self._record_suggestion(suggestion)
                    return suggestion

        # 2. Temporal Suggestion: "It's morning / evening..."
        frequent = await self.pattern_learner.get_frequent_intents_by_time(now.hour)
        if frequent:
            top = frequent[0]
            if top["frequency"] >= 2:
                suggestion = self._craft_temporal_suggestion(top["final_intent"], now.hour)
                if suggestion:
                    self._record_suggestion(suggestion)
                    return suggestion

        # 3. Contextual / Idle Suggestion fallback
        if context and context.get("idle_minutes", 0) > 20:
            suggestion = {
                "type": "IDLE",
                "text": "Notice you've been idle for a bit. Want to review your active sprint or todo items?",
                "suggested_action": "review_tasks",
                "confidence": 0.75,
                "created_at": now.isoformat(),
            }
            self._record_suggestion(suggestion)
            return suggestion

        return None

    def _craft_sequential_suggestion(self, current: str, next_intent: str) -> dict[str, Any] | None:
        mapping = {
            (
                "ALERTING",
                "AUTOMATION",
            ): "You reviewed your reminders — ready to run your build/deploy scripts?",
            (
                "ALERTING",
                "RESEARCH",
            ): "Deadlines checked! Want me to pull research papers for your study topic?",
            (
                "RESEARCH",
                "AUTOMATION",
            ): "Research done! Should I generate and test a script for this?",
            ("CONVERSATION", "ALERTING"): "Checking in: want a quick rundown of today's schedule?",
        }
        text = mapping.get((current.upper(), next_intent.upper()))
        if not text:
            text = (
                f"Based on your workflow, you usually move to {next_intent} next. Ready to proceed?"
            )

        return {
            "type": "SEQUENTIAL",
            "text": text,
            "suggested_action": next_intent.lower(),
            "confidence": 0.82,
            "created_at": datetime.now().isoformat(),
        }

    def _craft_temporal_suggestion(self, intent: str, hour: int) -> dict[str, Any] | None:
        if 6 <= hour <= 10:
            return {
                "type": "TEMPORAL",
                "text": "Good morning! Ready for your daily news digest and focus briefing?",
                "suggested_action": "morning_briefing",
                "confidence": 0.85,
                "created_at": datetime.now().isoformat(),
            }
        elif 21 <= hour <= 23:
            return {
                "type": "TEMPORAL",
                "text": "Evening wrap-up: Want to save your progress and review tomorrow's priority tasks?",
                "suggested_action": "evening_wrapup",
                "confidence": 0.80,
                "created_at": datetime.now().isoformat(),
            }
        return {
            "type": "TEMPORAL",
            "text": f"You frequently check {intent.lower()} around this time. Would you like me to pull that up?",
            "suggested_action": intent.lower(),
            "confidence": 0.70,
            "created_at": datetime.now().isoformat(),
        }

    def _record_suggestion(self, suggestion: dict[str, Any]):
        self.last_suggestion = suggestion
        self.last_suggested_at = datetime.now()

    async def broadcast_suggestion_to_swarm(self, suggestion: dict[str, Any]):
        """Publish status nudge event to SwarmBus so Conductor can mention it in conversation."""
        if not self.swarm_bus:
            return
        try:
            from sunday.core.swarm.events import EventPriority, EventType, SwarmEvent

            evt = SwarmEvent(
                event_type=EventType.STATUS_NUDGE,
                source_agent="suggestion_engine",
                target_agent="conductor",
                payload={
                    "task_id": "proactive_suggestion",
                    "status": "ready",
                    "summary": suggestion["text"],
                    "action": suggestion.get("suggested_action"),
                },
                priority=EventPriority.NORMAL,
            )
            await self.swarm_bus.publish(evt)
        except Exception as e:
            logger.warning(f"Failed to broadcast proactive suggestion to SwarmBus: {e}")
