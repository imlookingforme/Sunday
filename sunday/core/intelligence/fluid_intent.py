"""Fluid Intent Engine - Neural intent understanding via semantic embeddings and zero-shot reasoning."""

import logging
from typing import Any

import numpy as np

from sunday.core.intelligence.hf_model_loader import HFModelLoader
from sunday.core.intent_judge import IntentJudge
from sunday.core.operators.base import ConversationMode

logger = logging.getLogger(__name__)


class FluidIntentEngine:
    """Neural NLU Intent Engine that understands semantic meaning, context and intent."""

    INTENT_EXEMPLARS: dict[ConversationMode, list[str]] = {
        ConversationMode.RESEARCH: [
            "what is the latest news on quantum computing",
            "search the web for python best practices",
            "explain how attention mechanisms work in transformers",
            "look up documentation on asyncio queues",
            "who invented the fast fourier transform",
            "find recent papers about machine learning",
        ],
        ConversationMode.AUTOMATION: [
            "run the test suite and build the package",
            "execute script to clean up temporary files",
            "automate daily report generation",
            "launch my development workspace",
            "schedule a backup job every hour",
            "deploy the build to the server",
        ],
        ConversationMode.DEVICE_CONTROL: [
            "turn up the volume please",
            "mute the audio output",
            "dim the display brightness",
            "switch to the next active window",
            "pause the music playback",
            "minimize all windows on the desktop",
        ],
        ConversationMode.ALERTING: [
            "remind me to take a break in 30 minutes",
            "give me my daily briefing and status update",
            "what deadlines do I have coming up today",
            "notify me if server load exceeds ninety percent",
            "check my calendar for upcoming events",
            "nudge me if I pass time browsing",
        ],
        ConversationMode.SECURITY_LOCKDOWN: [
            "lockdown system access and revoke permissions",
            "block unauthorized network connections immediately",
            "audit security access logs for suspicious activity",
            "scan system for potential vulnerabilities and threats",
            "emergency stop all running background tasks",
        ],
        ConversationMode.CONVERSATION: [
            "hey sunday how is your day going",
            "tell me a joke or something funny",
            "i am feeling kinda bored today",
            "what do you think about artificial intelligence",
            "let's chat for a while",
            "good morning, hope you're ready",
        ],
    }

    def __init__(self, enable_neural: bool = True):
        self.enable_neural = enable_neural
        self.loader = HFModelLoader()
        self._keyword_judge = IntentJudge()
        self._exemplar_embeddings: dict[ConversationMode, np.ndarray] = {}
        self._initialized_embeddings = False

    def _init_exemplars(self):
        """Pre-compute embeddings for canonical intent exemplar clusters."""
        if self._initialized_embeddings or not self.enable_neural:
            return

        embedder = self.loader.get_embedding_model()
        if embedder is None:
            return

        try:
            for mode, sentences in self.INTENT_EXEMPLARS.items():
                embeddings = embedder.encode(sentences, convert_to_numpy=True, show_progress_bar=False)
                # Normalize embeddings
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = embeddings / np.maximum(norms, 1e-12)
                self._exemplar_embeddings[mode] = embeddings
            self._initialized_embeddings = True
            logger.info("FluidIntentEngine: Canonical exemplar embeddings initialized.")
        except Exception as e:
            logger.warning(f"FluidIntentEngine failed to pre-compute exemplars: {e}")

    def classify(self, text: str, context: dict[str, Any] | None = None) -> ConversationMode:
        """Classify user turn into ConversationMode using semantic vectors or zero-shot inference."""
        res, _ = self.classify_with_confidence(text, context)
        return res

    def classify_with_confidence(
        self, text: str, context: dict[str, Any] | None = None
    ) -> tuple[ConversationMode, float]:
        """Classify with calibrated confidence score."""
        text_clean = text.strip()
        if not text_clean:
            return ConversationMode.CONVERSATION, 0.5

        # 1. Neural classification via embeddings
        if self.enable_neural:
            self._init_exemplars()
            embedder = self.loader.get_embedding_model()
            if embedder is not None and self._initialized_embeddings:
                try:
                    query_emb = embedder.encode([text_clean], convert_to_numpy=True, show_progress_bar=False)
                    query_emb = query_emb / np.maximum(np.linalg.norm(query_emb), 1e-12)

                    best_mode = ConversationMode.CONVERSATION
                    highest_sim = -1.0

                    for mode, exemplars in self._exemplar_embeddings.items():
                        sims = np.dot(exemplars, query_emb.T).flatten()
                        max_sim = float(np.max(sims))
                        if max_sim > highest_sim:
                            highest_sim = max_sim
                            best_mode = mode

                    # Context prior boost
                    if context:
                        recent_mode = context.get("recent_mode")
                        if recent_mode and recent_mode == best_mode.value:
                            highest_sim = min(1.0, highest_sim + 0.1)

                    if highest_sim >= 0.55:
                        return best_mode, float(highest_sim)

                    # If ambiguous between 0.35 and 0.55, try zero-shot MNLI pipeline if available
                    zero_shot_pipe = self.loader.get_zero_shot_pipeline()
                    if zero_shot_pipe is not None:
                        try:
                            labels_map = {
                                "academic research or web query": ConversationMode.RESEARCH,
                                "running an automation script or system command": ConversationMode.AUTOMATION,
                                "adjusting audio, screen, or device controls": ConversationMode.DEVICE_CONTROL,
                                "setting a reminder, alarm, or checking schedule": ConversationMode.ALERTING,
                                "emergency security lockdown or revoking permissions": ConversationMode.SECURITY_LOCKDOWN,
                                "casual conversational chat": ConversationMode.CONVERSATION,
                            }
                            res = zero_shot_pipe(
                                text_clean, candidate_labels=list(labels_map.keys())
                            )
                            if (
                                res
                                and "labels" in res
                                and "scores" in res
                                and len(res["labels"]) > 0
                            ):
                                top_label = res["labels"][0]
                                top_score = float(res["scores"][0])
                                if top_score >= 0.4:
                                    return labels_map[top_label], top_score
                        except Exception as e:
                            logger.debug(f"Zero-shot pipeline evaluation skipped: {e}")

                    if highest_sim >= 0.40:
                        return best_mode, float(highest_sim)

                except Exception as e:
                    logger.debug(f"Neural embedding classification error: {e}")

        # 2. Heuristic fallback (fast keyword matching)
        kw_mode = self._keyword_judge.classify(text_clean, context)
        confidence = self._keyword_judge.get_confidence(text_clean, kw_mode)
        return kw_mode, confidence

    def explain_classification(self, text: str, mode: ConversationMode) -> str:
        """Provide transparent human-readable explanation of intent classification."""
        return f"Classified intent as {mode.name} using Fluid Neural Intent Engine with semantic similarity matching."
