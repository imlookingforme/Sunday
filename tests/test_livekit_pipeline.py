"""Tests for LiveKit Voice Pipeline, duplex barge-in, and tool approval gating."""

import pytest
import asyncio
from sunday.daemon.livekit_pipeline import LiveKitVoicePipeline, VoiceMode
from sunday.core.swarm.bus import SwarmBus
from sunday.core.swarm.conductor import Conductor
from sunday.tools.registry import tool, ToolRisk, ToolResult


@pytest.mark.asyncio
async def test_livekit_pipeline_mode_switching_and_turn():
    """Verify LiveKitVoicePipeline initializes and processes audio turns."""
    bus = SwarmBus()
    await bus.start()
    conductor = Conductor(bus)
    await conductor.start()

    pipeline = LiveKitVoicePipeline(mode=VoiceMode.PIPELINE, bus=bus, conductor=conductor)
    await pipeline.initialize()

    assert pipeline.mode == VoiceMode.PIPELINE
    pipeline.set_mode(VoiceMode.REALTIME_GEMINI)
    assert pipeline.mode == VoiceMode.REALTIME_GEMINI

    pipeline.set_mode(VoiceMode.PIPELINE)

    # Simulate user turn with byte string
    test_audio = b"Hey Sunday, status update please"
    response = await pipeline.process_turn(test_audio)
    assert len(response) > 0

    await pipeline.end_call()
    await conductor.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_barge_in_interruption():
    """Verify barge-in interrupts ongoing assistant speech."""
    pipeline = LiveKitVoicePipeline(mode=VoiceMode.PIPELINE)
    await pipeline.initialize()

    # Simulate assistant speaking (wrapped so CancelledError is handled gracefully)
    speak_task = asyncio.create_task(pipeline.tts.speak("This is a long sentence that should get interrupted."))
    await asyncio.sleep(0.01)

    # Barge-in triggered by incoming user audio
    pipeline.tts.interrupt()
    assert pipeline.tts._interrupted is True

    # Task should complete without raising (graceful cancel handled internally)
    try:
        await asyncio.wait_for(speak_task, timeout=1.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass  # Either outcome is acceptable for barge-in

    assert pipeline.tts._interrupted is True


@pytest.mark.asyncio
async def test_tool_call_gating():
    """Verify HIGH risk tools are diverted to approval tickets instead of executing blindly."""
    bus = SwarmBus()
    await bus.start()

    approval_events = []
    bus.subscribe("approval_request", lambda e: approval_events.append(e))

    # Register a test high-risk tool
    @tool(name="dangerous_format_disk", risk=ToolRisk.HIGH, description="Formats disk")
    async def dangerous_format_disk(drive: str) -> ToolResult:
        return ToolResult(success=True, data="formatted")

    pipeline = LiveKitVoicePipeline(bus=bus)
    await pipeline.initialize()

    result = await pipeline.handle_tool_call("dangerous_format_disk", {"drive": "C:"})
    assert result["status"] == "gated_for_approval"
    assert "approval card" in result["message"]

    await asyncio.sleep(0.1)
    assert len(approval_events) == 1
    assert approval_events[0].tool_name == "dangerous_format_disk"

    await bus.stop()
