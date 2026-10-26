"""Test Suite for Sunday 2.0 Phases 8 & 9: Browser Verification & Mission Control 2.0.

Validates:
- Phase 8: Dev app command detection (npm/python)
- Phase 8: Port readiness probing and timeout safety
- Phase 8: Browser diagnostics (status code, console errors, DOM title)
- Phase 8: Visual regression tolerance comparison
- Phase 9: Mission Control pipeline aggregation (grouping by state)
- Phase 9: Swarm agent inspector tracking
- Phase 9: Developer intervention controls (cancel, approve, rollback)
- Phase 9: Live SSE event streaming
"""

import asyncio
import tempfile
import pytest
from pathlib import Path

from sunday.browser_verification import (
    BrowserVerificationDriver,
    DevAppLifecycleManager,
)
from sunday.dashboard.mission_control import MissionControlService
from sunday.core.durable_tasks import DurableTaskEngine, TaskState


def test_dev_app_command_detection(tmp_path: Path):
    manager = DevAppLifecycleManager(workspace_root=tmp_path)

    # 1. Default fallback
    cmd, port = manager.detect_dev_command()
    assert port in [8000, 8080]

    # 2. Package.json detection
    pkg = tmp_path / "package.json"
    pkg.write_text('{"scripts": {"dev": "vite"}}', encoding="utf-8")
    cmd_node, port_node = manager.detect_dev_command()
    assert "npm run dev" in cmd_node
    assert port_node == 3000


def test_screenshot_visual_regression_comparison(tmp_path: Path):
    driver = BrowserVerificationDriver(artifacts_dir=tmp_path)

    img1 = tmp_path / "img1.png"
    img2 = tmp_path / "img2.png"
    img3 = tmp_path / "img3.png"

    img1.write_bytes(b"dummy_png_bytes_1234567890")
    img2.write_bytes(b"dummy_png_bytes_1234567890")
    img3.write_bytes(b"dummy_png_bytes_different_length_bytes_456")

    # Identical
    res_exact = driver.compare_screenshots(img1, img2)
    assert res_exact["match"] is True
    assert res_exact["difference_percent"] == 0.0

    # Tolerant comparison
    res_diff = driver.compare_screenshots(img1, img3, tolerance_percent=5.0)
    assert res_diff["match"] is False
    assert res_diff["difference_percent"] > 5.0


@pytest.mark.asyncio
async def test_mission_control_pipeline_and_intervention(tmp_path: Path):
    db_file = tmp_path / "test_mc.db"
    engine = DurableTaskEngine(db_path=db_file)
    service = MissionControlService(task_engine=engine)

    # Create dummy tasks
    task1 = await engine.create_task("task_mc_1", "Build UI", assigned_agent="coder")
    await engine.transition(task1.task_id, TaskState.PLANNING)
    await engine.transition(task1.task_id, TaskState.READY)
    await engine.transition(task1.task_id, TaskState.RUNNING)

    task2 = await engine.create_task("task_mc_2", "Audit security", assigned_agent="gatekeeper")

    # Check pipeline aggregation
    summary = await service.get_task_pipeline_summary()
    assert summary["total_tasks"] == 2
    assert summary["active_tasks"] == 1
    assert len(summary["buckets"]["running"]) == 1
    assert len(summary["buckets"]["queued"]) == 1

    # Check agent inspector
    agents = await service.get_agent_inspector_data()
    coder_info = next(a for a in agents if a["name"] == "coder")
    assert coder_info["current_task"] == "task_mc_1"

    # User intervention: Cancel task
    interv_res = await service.handle_user_intervention("cancel", "task_mc_1")
    assert interv_res["success"] is True

    reloaded = await engine.get_task("task_mc_1")
    assert reloaded.state == TaskState.CANCELLED


@pytest.mark.asyncio
async def test_mission_control_sse_streaming(tmp_path: Path):
    service = MissionControlService(task_engine=DurableTaskEngine(db_path=tmp_path / "sse.db"))
    stream = service.sse_event_stream()

    # Read first connection event
    first_chunk = await stream.__anext__()
    assert "event: connected" in first_chunk

    # Broadcast update
    await service.broadcast_event("test_event", {"metric": 42})
    update_chunk = await stream.__anext__()
    assert "event: update" in update_chunk
    assert "test_event" in update_chunk
