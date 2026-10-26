import pytest
import asyncio
from sunday.workflow_engine import (
    WorkflowEngine,
    WorkflowStep,
    WorkflowTrigger,
    TriggerType,
    StepStatus,
    build_test_autodiagnosis_recipe,
)
from sunday.evaluation import (
    EvaluationFramework,
    BenchmarkScenario,
    BenchmarkCategory,
    BenchmarkScorecard,
    get_standard_benchmark_suite,
)


# === Phase 10: Event-Driven Automation & Idempotent Workflow Engine Tests ===

@pytest.mark.asyncio
async def test_workflow_engine_basic_execution():
    engine = WorkflowEngine()

    step1 = WorkflowStep(
        step_id="step_a",
        name="Step A",
        action=lambda ctx: ctx.get("trigger", {}).get("num", 0) * 2,
    )
    step2 = WorkflowStep(
        step_id="step_b",
        name="Step B",
        dependencies={"step_a"},
        action=lambda ctx: ctx["step_a"] + 10,
    )

    trigger = WorkflowTrigger(
        trigger_type=TriggerType.MANUAL,
        source="test_runner",
        payload={"num": 5},
    )

    result = await engine.execute_workflow("math_pipeline", [step1, step2], trigger)

    assert result.success is True
    assert result.step_outputs["step_a"] == 10
    assert result.step_outputs["step_b"] == 20
    assert result.idempotent_cached is False


@pytest.mark.asyncio
async def test_workflow_engine_conditional_and_dependencies():
    engine = WorkflowEngine()

    step1 = WorkflowStep(
        step_id="step_check",
        name="Check Condition",
        action=lambda ctx: False,
    )
    step_conditional = WorkflowStep(
        step_id="step_cond",
        name="Run If True",
        condition=lambda ctx: ctx.get("step_check") is True,
        action=lambda ctx: "ran_conditional",
    )
    step_dep = WorkflowStep(
        step_id="step_dep",
        name="Depends On Conditional",
        dependencies={"step_cond"},
        action=lambda ctx: "ran_dependent",
    )

    trigger = WorkflowTrigger(
        trigger_type=TriggerType.FILE_CHANGE,
        source="src/main.py",
        payload={},
    )

    result = await engine.execute_workflow("cond_pipeline", [step1, step_conditional, step_dep], trigger)

    assert result.success is True
    assert step_conditional.status == StepStatus.SKIPPED
    assert step_dep.status == StepStatus.SKIPPED
    assert "step_cond" not in result.step_outputs
    assert "step_dep" not in result.step_outputs


@pytest.mark.asyncio
async def test_workflow_engine_retry_and_failure():
    engine = WorkflowEngine()

    attempts = {"count": 0}

    def flaky_action(ctx):
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ValueError("Temporary glitch")
        return "recovered"

    step = WorkflowStep(
        step_id="flaky_step",
        name="Flaky Step",
        action=flaky_action,
        max_retries=2,
    )

    trigger = WorkflowTrigger(
        trigger_type=TriggerType.TASK_EVENT,
        source="task_scheduler",
        payload={"id": "job_1"},
    )

    res = await engine.execute_workflow("retry_workflow", [step], trigger)
    assert res.success is True
    assert res.step_outputs["flaky_step"] == "recovered"
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_workflow_engine_idempotency_caching():
    engine = WorkflowEngine(idempotency_ttl_seconds=10.0)

    call_count = {"calls": 0}

    def counting_action(ctx):
        call_count["calls"] += 1
        return f"result_{call_count['calls']}"

    step = WorkflowStep(
        step_id="counting_step",
        name="Counting Step",
        action=counting_action,
    )

    trigger1 = WorkflowTrigger(
        trigger_type=TriggerType.GIT_EVENT,
        source="git_hook",
        payload={"commit": "abc1234"},
    )

    # First run: should execute
    res1 = await engine.execute_workflow("idemp_wf", [step], trigger1)
    assert res1.success is True
    assert res1.idempotent_cached is False
    assert call_count["calls"] == 1

    # Second run with identical payload: should return cached result without re-executing
    step_copy = WorkflowStep(
        step_id="counting_step",
        name="Counting Step",
        action=counting_action,
    )
    res2 = await engine.execute_workflow("idemp_wf", [step_copy], trigger1)
    assert res2.success is True
    assert res2.idempotent_cached is True
    assert call_count["calls"] == 1
    assert res2.step_outputs["counting_step"] == "result_1"

    # Third run with different payload: executes freshly
    trigger2 = WorkflowTrigger(
        trigger_type=TriggerType.GIT_EVENT,
        source="git_hook",
        payload={"commit": "def5678"},
    )
    res3 = await engine.execute_workflow("idemp_wf", [step_copy], trigger2)
    assert res3.success is True
    assert res3.idempotent_cached is False
    assert call_count["calls"] == 2


@pytest.mark.asyncio
async def test_workflow_test_autodiagnosis_recipe():
    recipe_steps = build_test_autodiagnosis_recipe()
    engine = WorkflowEngine()

    trigger = WorkflowTrigger(
        trigger_type=TriggerType.TASK_EVENT,
        source="pytest_runner",
        payload={"errors": ["AssertionError: expected 5 got 4", "IndexError: list index out of range"]},
    )

    result = await engine.execute_workflow("test_autodiagnosis", recipe_steps, trigger)
    assert result.success is True
    assert len(result.step_outputs["extract_failures"]) == 2
    assert "2 failure signatures" in result.step_outputs["generate_diagnosis"]


# === Phase 12: Autonomous Evaluation & Standardized Benchmark Framework Tests ===

@pytest.mark.asyncio
async def test_evaluation_framework_scenario_execution():
    framework = EvaluationFramework()

    scenario = BenchmarkScenario(
        scenario_id="bench_test_dummy",
        name="Dummy Verification Scenario",
        category=BenchmarkCategory.BUG_FIXING,
        prompt="Fix the syntax error",
        acceptance_criteria=["Correct syntax", "Tests pass"],
        expected_files=["dummy.py"],
        verify_fn=lambda: True,
    )
    framework.register_scenario(scenario)

    card = await framework.run_scenario("bench_test_dummy")
    assert card.passed is True
    assert card.criteria_score == 1.0
    assert card.scenario_id == "bench_test_dummy"
    assert card.category == BenchmarkCategory.BUG_FIXING
    assert card.duration_seconds >= 0.0


@pytest.mark.asyncio
async def test_evaluation_framework_suite_and_standard_suite():
    suite = get_standard_benchmark_suite()
    assert len(suite.scenarios) >= 3

    # Run the full standard benchmark suite
    summary = await suite.run_suite()
    assert summary["total_scenarios"] >= 3
    assert summary["passed_scenarios"] == summary["total_scenarios"]
    assert summary["pass_rate_percent"] == 100.0
    assert summary["average_criteria_score"] == 1.0
    assert len(summary["scorecards"]) >= 3

    # Filtered run by category
    sub_summary = await suite.run_suite(category=BenchmarkCategory.REPO_EXPLORATION)
    assert sub_summary["total_scenarios"] == 1
    assert sub_summary["passed_scenarios"] == 1
    assert sub_summary["scorecards"][0]["id"] == "bench_ast_symbol_lookup"
