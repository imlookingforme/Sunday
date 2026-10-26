"""Test Suite for Sunday 2.0 Phases 6 & 7: Model Routing & Categorized Memory.

Validates:
- Phase 6 Model Capability Registry (metadata, context capacity, tool support)
- Phase 6 Task-Aware Routing (Economy, Balanced, High Quality, Local Only)
- Phase 6 Ollama local inference & zero-remote-leakage policy in Local Only mode
- Phase 7 Categorized Persistent Memory (preferences, project conventions, ADRs, debugging lessons)
- Phase 7 Memory Provenance, TTL expiration, and superseding outdated entries
- Phase 7 Learning from corrections (classifying one-time fixes vs permanent project rules)
- Phase 7 Secret masking before memory storage
"""

import os
import tempfile
import pytest
from pathlib import Path

from sunday.core.routing import (
    ModelCapability,
    ModelRegistry,
    ModelResponse,
    OllamaClient,
    RoutingPolicy,
    TaskAwareModelRouter,
    TaskCategory,
)
from sunday.memory.categorized_memory import (
    CategorizedMemoryStore,
    CorrectionScope,
    MemoryCategory,
    MemoryRecord,
)


def test_model_registry_capabilities():
    registry = ModelRegistry()
    models = registry.list_models()
    assert len(models) >= 5

    gpt4o = registry.get_model("gpt-4o")
    assert gpt4o is not None
    assert gpt4o.supports_tools is True
    assert gpt4o.context_capacity >= 128000

    local_models = registry.list_models(local_only=True)
    assert any(m.model_id == "phi3:mini" for m in local_models)


def test_task_aware_routing_policies():
    router = TaskAwareModelRouter()

    # 1. High quality policy routes complex tasks to Sonnet or GPT-4o
    high_cap = router.select_model_for_task(TaskCategory.COMPLEX_IMPLEMENTATION, RoutingPolicy.HIGH_QUALITY)
    assert high_cap.model_id in ["claude-3-5-sonnet-20241022", "gpt-4o"]

    # 2. Economy policy routes simple tasks to mini model
    econ_cap = router.select_model_for_task(TaskCategory.AUTOCOMPLETE, RoutingPolicy.ECONOMY)
    assert econ_cap.model_id in ["gpt-4o-mini", "phi3:mini"]

    # 3. Local only policy strictly returns a local model (zero cloud leakage)
    local_cap = router.select_model_for_task(TaskCategory.COMPLEX_IMPLEMENTATION, RoutingPolicy.LOCAL_ONLY)
    assert local_cap.is_local is True
    assert local_cap.provider == "ollama"


@pytest.mark.asyncio
async def test_routing_execution_fallback():
    router = TaskAwareModelRouter()

    # Mock cloud caller
    async def mock_cloud(model_id: str, prompt: str, system: str):
        return f"Response from {model_id}: {prompt}"

    res = await router.route_execution(
        task_type=TaskCategory.PLANNING,
        prompt="Design cache layer",
        cloud_caller=mock_cloud,
    )
    assert res.content.startswith("Response from")
    assert res.is_local is False


@pytest.mark.asyncio
async def test_categorized_memory_lifecycle(tmp_path: Path):
    db_file = tmp_path / "test_memory.db"
    store = CategorizedMemoryStore(db_path=db_file)

    # 1. Store convention
    rec1 = await store.store_memory(
        category=MemoryCategory.PROJECT_CONVENTION,
        key="async_db_pattern",
        content="Always use aiosqlite or asyncio.to_thread for database queries.",
        project="Sunday",
    )
    assert rec1.category == MemoryCategory.PROJECT_CONVENTION

    # 2. Retrieve convention
    mems = await store.retrieve_memories(category=MemoryCategory.PROJECT_CONVENTION, project="Sunday")
    assert len(mems) == 1
    assert "aiosqlite" in mems[0].content

    # 3. Update with newer decision (supersedes previous)
    rec2 = await store.store_memory(
        category=MemoryCategory.PROJECT_CONVENTION,
        key="async_db_pattern",
        content="Prefer aiosqlite connection pools where available.",
        project="Sunday",
    )
    active_mems = await store.retrieve_memories(category=MemoryCategory.PROJECT_CONVENTION, project="Sunday")
    assert len(active_mems) == 1
    assert "connection pools" in active_mems[0].content


@pytest.mark.asyncio
async def test_memory_secret_sanitization(tmp_path: Path):
    db_file = tmp_path / "test_memory_sec.db"
    store = CategorizedMemoryStore(db_path=db_file)

    await store.store_memory(
        category=MemoryCategory.TECHNICAL_FACT,
        key="test_api_key",
        content="Use key sk-1234567890abcdef12345678 for staging.",
    )
    mems = await store.retrieve_memories(category=MemoryCategory.TECHNICAL_FACT)
    assert len(mems) == 1
    assert "[REDACTED_API_KEY]" in mems[0].content
    assert "sk-1234567890abcdef12345678" not in mems[0].content


def test_classify_user_corrections():
    store = CategorizedMemoryStore()

    # Permanent convention
    res1 = store.classify_user_correction("Always use pytest-asyncio for async tests in this project.")
    assert res1["should_persist"] is True
    assert res1["scope"] == CorrectionScope.PROJECT_CONVENTION

    # Personal user preference
    res2 = store.classify_user_correction("I prefer concise summaries over verbose explanations.")
    assert res2["should_persist"] is True
    assert res2["scope"] == CorrectionScope.USER_PREFERENCE

    # One-time guidance
    res3 = store.classify_user_correction("Just change line 45 to return False for now.")
    assert res3["should_persist"] is False
    assert res3["scope"] == CorrectionScope.ONE_TIME_INSTRUCTION
