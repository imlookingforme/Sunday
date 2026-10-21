"""Unit and Integration Tests for Phase 7 — World-Class Intelligence features."""

import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch

from sunday.core.intelligence.hf_model_loader import HFModelLoader
from sunday.core.intelligence.fluid_intent import FluidIntentEngine
from sunday.core.intelligence.context_disambiguator import ContextDisambiguator
from sunday.core.intelligence.pattern_learner import PatternLearner
from sunday.core.intelligence.suggestion_engine import SuggestionEngine
from sunday.core.intelligence.entity_extractor import EntityExtractor
from sunday.core.intelligence.mood_detector import MoodDetector
from sunday.core.operators.base import ConversationMode


@pytest.mark.asyncio
async def test_hf_model_loader_singleton():
    """Verify HFModelLoader singleton pattern and lazy state."""
    loader1 = HFModelLoader()
    loader2 = HFModelLoader()
    assert loader1 is loader2
    info = loader1.get_loaded_models_info()
    assert isinstance(info, dict)
    assert "embedding_models" in info
    assert "pipelines" in info


@pytest.mark.asyncio
async def test_fluid_intent_keyword_fallback():
    """Verify FluidIntentEngine falls back accurately when neural mode is disabled."""
    engine = FluidIntentEngine(enable_neural=False)

    # Test research
    mode, conf = engine.classify_with_confidence("what is the latest news about quantum computing")
    assert mode == ConversationMode.RESEARCH
    assert conf > 0.0

    # Test device control
    mode, conf = engine.classify_with_confidence("turn down the volume")
    assert mode == ConversationMode.DEVICE_CONTROL
    assert conf > 0.0

    # Test conversation
    mode, conf = engine.classify_with_confidence("hey what's up")
    assert mode == ConversationMode.CONVERSATION


@pytest.mark.asyncio
async def test_context_disambiguator():
    """Verify ContextDisambiguator resolves vague queries using conversational history."""
    disambiguator = ContextDisambiguator()

    history = [
        {"role": "user", "content": "can you check the python test script?"},
        {"role": "assistant", "content": "Sure, looking at test_suite.py"}
    ]

    # "run it" is ambiguous
    mode, reason = await disambiguator.disambiguate(
        text="run it",
        initial_mode=ConversationMode.CONVERSATION,
        confidence=0.3,
        history=history
    )
    assert mode == ConversationMode.AUTOMATION
    assert "conversation topic" in reason.lower()


@pytest.mark.asyncio
async def test_pattern_learner_logging_and_mining(tmp_path):
    """Verify PatternLearner writes and retrieves habits and patterns."""
    db_file = str(tmp_path / "test_patterns.db")
    learner = PatternLearner(db_path=db_file)

    # Log 3 events
    await learner.log_intent_event("search papers", "RESEARCH", 0.9, "RESEARCH")
    await learner.log_intent_event("build scripts", "AUTOMATION", 0.85, "AUTOMATION")
    await learner.log_intent_event("search models", "RESEARCH", 0.92, "RESEARCH")

    count = await learner.get_total_events_count()
    assert count == 3

    patterns = await learner.get_frequent_intents_by_time()
    assert len(patterns) > 0
    top_intent = patterns[0]["final_intent"]
    assert top_intent in ["RESEARCH", "AUTOMATION"]


@pytest.mark.asyncio
async def test_suggestion_engine_sequential():
    """Verify SuggestionEngine generates sequence-aware suggestions."""
    mock_learner = MagicMock()
    mock_learner.get_sequential_pattern = MagicMock()

    # Mock sequential habit: ALERTING -> AUTOMATION
    async def mock_seq(intent):
        if intent == "ALERTING":
            return "AUTOMATION"
        return None
    mock_learner.get_sequential_pattern.side_effect = mock_seq

    engine = SuggestionEngine(pattern_learner=mock_learner)
    suggestion = await engine.generate_suggestion(recent_intent="ALERTING")

    assert suggestion is not None
    assert suggestion["type"] == "SEQUENTIAL"
    assert "automation" in suggestion["suggested_action"].lower()
    assert "ready to run your build/deploy" in suggestion["text"].lower()


@pytest.mark.asyncio
async def test_suggestion_engine_idle():
    """Verify SuggestionEngine suggests review when user is idle."""
    mock_learner = MagicMock()
    async def mock_seq(intent): return None
    async def mock_freq(hour): return []
    mock_learner.get_sequential_pattern.side_effect = mock_seq
    mock_learner.get_frequent_intents_by_time.side_effect = mock_freq

    engine = SuggestionEngine(pattern_learner=mock_learner)
    suggestion = await engine.generate_suggestion(context={"idle_minutes": 25})

    assert suggestion is not None
    assert suggestion["type"] == "IDLE"
    assert "review_tasks" == suggestion["suggested_action"]


def test_entity_extractor():
    """Verify EntityExtractor identifies applications, times, and files."""
    extractor = EntityExtractor(enable_hf=False)
    text = "open Cursor and check main.py in 15 minutes"
    entities = extractor.extract_entities(text)

    assert "cursor" in entities["apps"]
    assert "main.py" in entities["files"]
    assert any("15 minutes" in t for t in entities["time_expressions"])


def test_mood_detector():
    """Verify MoodDetector identifies positive sentiment, frustration, and style tuning."""
    detector = MoodDetector(enable_hf=False)

    res_pos = detector.detect_mood("Awesome, Sunday, that's fire! Great job!")
    assert res_pos["sentiment"] == "positive"
    assert not res_pos["is_frustrated"]
    assert res_pos["recommended_style"] == "genz"

    res_frust = detector.detect_mood("Why isn't this working! Damn it!")
    assert res_frust["is_frustrated"]
    assert res_frust["recommended_style"] == "concise_direct"
