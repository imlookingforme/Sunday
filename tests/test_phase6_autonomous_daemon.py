"""Comprehensive test suite for Phase 6: Insomnia, Scout, Self-Authoring, Healer, and Universal Controller."""

import pytest
import asyncio
from pathlib import Path

from sunday.daemon.insomnia import InsomniaEngine
from sunday.core.scout.newsletter_scout import NewsletterScout, KnowledgeDigestItem
from sunday.core.authoring.self_authoring import SelfAuthoringEngine
from sunday.core.debug.recursive_healer import RecursiveSelfHealingEngine
from sunday.core.controller.universal_controller import UniversalController
from sunday.tools.registry import ToolRegistry


# ─────────────────────────────────────────────────────────────
# 1. Windows Insomnia Engine Tests
# ─────────────────────────────────────────────────────────────

def test_insomnia_activation_and_safety():
    engine = InsomniaEngine(min_battery_threshold=20.0)

    # Activation & Status
    activated = engine.activate()
    assert activated is True
    status = engine.get_status()
    assert status["is_active"] is True
    assert "safe" in status

    # Deactivation
    deactivated = engine.deactivate()
    assert deactivated is True
    assert engine.is_active is False


# ─────────────────────────────────────────────────────────────
# 2. Autonomous Newsletter & arXiv Scout Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_newsletter_scout_digestion(tmp_path):
    scout = NewsletterScout(cache_dir=tmp_path / "scout_cache")

    # Simulated cycle run
    discoveries = await scout.run_scout_cycle()
    assert len(discoveries) >= 1
    d1 = discoveries[0]
    assert d1.title
    assert d1.source
    assert len(d1.tags) > 0

    # Cache persistence verification
    seen_file = tmp_path / "scout_cache" / "seen_urls.txt"
    assert seen_file.exists()


# ─────────────────────────────────────────────────────────────
# 3. Self-Authoring Tool Plugin Engine Tests
# ─────────────────────────────────────────────────────────────

def test_self_authoring_engine(tmp_path):
    engine = SelfAuthoringEngine(plugins_dir=tmp_path / "plugins")

    tool_func = """
def test_calc_metric_handler(x: int = 10) -> ToolResult:
    return ToolResult(success=True, data={"result": x * 42})
"""

    res = engine.author_new_tool(
        tool_name="test_calc_metric",
        category="system",
        description="Calculates a test metric autonomously",
        function_code=tool_func,
        risk_level="low",
        required_args=["x"]
    )

    assert res["success"] is True
    assert res["registered"] is True
    assert ToolRegistry.get("test_calc_metric") is not None

    # Verify tool execution
    tool = ToolRegistry.get("test_calc_metric")
    run_res = tool.func(x=2)
    assert run_res.success is True
    assert run_res.data["result"] == 84


# ─────────────────────────────────────────────────────────────
# 4. Recursive Self-Healing Code Engine (Tree-of-Thought) Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recursive_self_healing_tot():
    healer = RecursiveSelfHealingEngine(max_recursion_depth=3)

    # 1. Synthetically broken code with missing import
    broken_code = """
import sys
# Missing module call
res = non_existent_library.calculate()
print("Success:", res)
"""

    # Heal the broken code
    heal_result = await healer.recursively_heal_code(broken_code)
    assert heal_result["healed"] is True
    assert heal_result["iterations"] >= 1
    assert "MockModule" in heal_result["code"] or "try" in heal_result["code"]


# ─────────────────────────────────────────────────────────────
# 5. Universal IDE & Web AI App Controller Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_universal_controller_failover():
    controller = UniversalController()

    # 1. Test IDE command dispatch
    ide_res = await controller.send_command_to_ide("cursor", "format_document")
    assert ide_res["success"] is True
    assert ide_res["ide"] == "cursor"

    # 2. Test Web AI turn with 429 rate-limit failover
    turn_res = await controller.execute_web_ai_turn_with_failover(
        provider="anthropic",
        prompt="Explain transformers",
        simulate_rate_limit=True
    )
    assert turn_res["success"] is True
    assert turn_res["failover_triggered"] is True
    assert turn_res["new_profile"] != turn_res["old_profile"]

    # Diagnostic status
    diag = controller.get_controller_status()
    assert "detected_apps" in diag
    assert "token_pool_status" in diag
