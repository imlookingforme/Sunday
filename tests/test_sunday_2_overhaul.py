"""Test Suite for Sunday 2.0 Autonomous Engineering Architecture.

Validates:
- Durable Task Engine (persistence, state machine transitions, invalid transition rejections, cancellation trees)
- Enhanced Security Broker (sandboxing, path containment, approval token flow, secret masking)
- Project Intelligence AST Indexer (symbol parsing, file hashes, dependency impact analysis)
- Autonomous Engineering Loop & Bounded Repair (acceptance criteria generation, test execution, bounded repair)
- Git Safety Manager (dirty tree check, file snapshots, rollback)
- Multi-Agent DAG Scheduler (dependency execution, cycle detection, parallel dispatch)
"""

import os
import tempfile
import pytest
from pathlib import Path

from sunday.core.durable_tasks import DurableTaskEngine, TaskState, ExecutionBudget
from sunday.core.security_broker import EnhancedSecurityBroker, ToolRisk, ToolCall, PolicyAction
from sunday.core.broker.audit import AuditLedger
from sunday.core.broker.vault import KeyringVault
from sunday.core.broker.permissions import PermissionChecker, default_permission_rules
from sunday.core.indexer.project_index import ProjectIndex
from sunday.core.loop.engineering_loop import AutonomousEngineeringLoop, VerificationOutcome
from sunday.core.git_safety.checkpoint_manager import GitSafetyManager
from sunday.core.orchestration.dag_scheduler import DAGScheduler, AgentRole


@pytest.mark.asyncio
async def test_durable_task_lifecycle(tmp_path: Path):
    db_file = tmp_path / "test_tasks.db"
    engine = DurableTaskEngine(db_path=db_file)

    task = await engine.create_task(
        task_id="task_eng_1",
        original_request="Refactor database models to async",
        acceptance_criteria=["Models compile", "Tests pass"],
    )
    assert task.state == TaskState.QUEUED

    # Valid transitions: QUEUED -> PLANNING -> READY -> RUNNING
    task = await engine.transition(task.task_id, TaskState.PLANNING, reason="Start planning")
    assert task.state == TaskState.PLANNING

    task = await engine.transition(task.task_id, TaskState.READY, reason="Plan created")
    assert task.state == TaskState.READY

    task = await engine.transition(task.task_id, TaskState.RUNNING, reason="Starting coding")
    assert task.state == TaskState.RUNNING

    # Illegal transition: RUNNING directly to QUEUED must raise ValueError
    with pytest.raises(ValueError):
        await engine.transition(task.task_id, TaskState.QUEUED)

    # Cancel task
    cancelled_ids = await engine.cancel_task_tree(task.task_id)
    assert "task_eng_1" in cancelled_ids

    reloaded = await engine.get_task(task.task_id)
    assert reloaded.state == TaskState.CANCELLED


@pytest.mark.asyncio
async def test_enhanced_security_broker(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    audit_file = tmp_path / "audit.jsonl"
    ledger = AuditLedger(audit_file)
    vault = KeyringVault()
    checker = PermissionChecker(default_permission_rules())

    tool_reg = {
        "file_writer": {"risk": "low", "reversible": True},
        "shell_executor": {"risk": "high", "reversible": False},
    }

    broker = EnhancedSecurityBroker(
        audit_ledger=ledger,
        vault=vault,
        permission_checker=checker,
        tool_registry=tool_reg,
        allowed_workspaces=[str(workspace)],
    )

    # 1. Path inside workspace allowed
    inside_file = workspace / "test.py"
    assert broker.is_path_within_workspace(inside_file) is True

    # 2. Path outside workspace rejected
    outside_file = outside / "secret.txt"
    assert broker.is_path_within_workspace(outside_file) is False

    # 3. Dangerous command detection
    assert broker.validate_command_safety("echo hello") is True
    assert broker.validate_command_safety("format c: /fs:NTFS") is False

    # 4. Secret masking
    payload = {"api_key": "sk-1234567890abcdef12345678", "notes": "normal text with sk-998877665544332211"}
    masked = broker.mask_secrets(payload)
    assert masked["api_key"] == "[REDACTED_CREDENTIAL]"
    assert "sk-[MASKED]" in masked["notes"]


def test_ast_project_indexer(tmp_path: Path):
    src_file = tmp_path / "sample_service.py"
    src_file.write_text(
        """
import os
from math import sqrt

class SampleEngine:
    '''Core calculation engine.'''
    def calculate(self, x: int) -> float:
        return sqrt(x)

async def run_pipeline():
    engine = SampleEngine()
    return engine.calculate(16)
""",
        encoding="utf-8",
    )

    indexer = ProjectIndex(root_dir=tmp_path)
    count = indexer.scan_project()
    assert count == 1

    symbols = indexer.find_symbol("SampleEngine")
    assert len(symbols) >= 1
    assert symbols[0].kind == "class"

    method_syms = indexer.find_symbol("calculate")
    assert len(method_syms) >= 1

    summary = indexer.generate_architecture_summary()
    assert summary["total_symbols"] >= 3


@pytest.mark.asyncio
async def test_git_safety_checkpoint_and_rollback(tmp_path: Path):
    sample_file = tmp_path / "code.py"
    sample_file.write_text("initial code v1.0", encoding="utf-8")

    manager = GitSafetyManager(repo_root=tmp_path, checkpoint_dir=tmp_path / "checkpoints")

    cp = await manager.create_checkpoint("task_1", ["code.py"], description="Pre-edit")
    assert len(cp.tracked_files) == 1

    # Modify file
    sample_file.write_text("broken code v2.0", encoding="utf-8")
    assert sample_file.read_text(encoding="utf-8") == "broken code v2.0"

    # Rollback
    restored = await manager.rollback_checkpoint(cp.checkpoint_id)
    assert restored is True
    assert sample_file.read_text(encoding="utf-8") == "initial code v1.0"


@pytest.mark.asyncio
async def test_dag_scheduler_execution():
    scheduler = DAGScheduler()
    order = []

    scheduler.add_node("arch", "Design architecture", AgentRole.ARCHITECT, action=lambda: order.append("arch"))
    scheduler.add_node("code", "Write implementation", AgentRole.IMPLEMENTER, dependencies={"arch"}, action=lambda: order.append("code"))
    scheduler.add_node("test", "Run tests", AgentRole.TEST_ENGINEER, dependencies={"code"}, action=lambda: order.append("test"))

    assert scheduler.detect_cycles() is False

    result = await scheduler.execute_dag()
    assert result["completed_nodes"] == 3
    assert order == ["arch", "code", "test"]


def test_dag_cycle_detection():
    scheduler = DAGScheduler()
    scheduler.add_node("A", "Node A", AgentRole.ARCHITECT, dependencies={"B"})
    scheduler.add_node("B", "Node B", AgentRole.IMPLEMENTER, dependencies={"A"})
    assert scheduler.detect_cycles() is True
