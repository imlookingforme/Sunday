"""Mood Detector - Analyzes user sentiment and frustration to adjust persona style."""

import logging
from typing import Any

from sunday.core.intelligence.hf_model_loader import HFModelLoader

logger = logging.getLogger(__name__)


class MoodDetector:
    """Detects conversational tone, sentiment, and user frustration for dynamic persona modulation."""

    def __init__(self, enable_hf: bool = False):
        self.enable_hf = enable_hf
        self.loader = HFModelLoader()

    def detect_mood(self, text: str) -> dict[str, Any]:
        """Detects sentiment score, tone, and frustration flag."""
        lowered = text.lower().strip()

        # Heuristic frustration indicators
        frustration_words = [
            "why isn't this working",
            "damn",
            "wrong",
            "stop it",
            "broken",
            "useless",
            "ugh",
            "fail",
        ]
        is_frustrated = any(w in lowered for w in frustration_words) or (
            "!" in text and len(text.split()) < 4
        )

        sentiment_label = "neutral"
        sentiment_score = 0.5

        if self.enable_hf:
            pipe = self.loader.get_sentiment_pipeline()
            if pipe:
                try:
                    res = pipe(text)
                    if res and len(res) > 0:
                        top = res[0]
                        sentiment_label = top.get("label", "neutral").lower()
                        sentiment_score = float(top.get("score", 0.5))
                except Exception as e:
                    logger.debug(f"HF sentiment evaluation error: {e}")

        # Fallback sentiment heuristics if neutral
        if sentiment_label == "neutral":
            positive_words = [
                "great",
                "awesome",
                "thanks",
                "perfect",
                "love",
                "cool",
                "fire",
                "bet",
                "legend",
            ]
            negative_words = ["bad", "terrible", "awful", "hate", "slow", "horrible", "annoying"]

            pos_matches = sum(1 for w in positive_words if w in lowered)
            neg_matches = sum(1 for w in negative_words if w in lowered)

            if pos_matches > neg_matches:
                sentiment_label = "positive"
                sentiment_score = 0.8
            elif neg_matches > pos_matches or is_frustrated:
                sentiment_label = "negative"
                sentiment_score = 0.8

        recommended_style = "genz"
        if is_frustrated or sentiment_label == "negative":
            recommended_style = "concise_direct"
        elif "study" in lowered or "exam" in lowered:
            recommended_style = "senpai"

        return {
            "sentiment": sentiment_label,
            "confidence": sentiment_score,
            "is_frustrated": is_frustrated,
            "recommended_style": recommended_style,
        }
