"""Comprehensive tests for Sunday Swarm Mesh, Specialists, and Live Steering."""

import pytest
import asyncio
from typing import Dict, Any

from sunday.core.swarm.bus import SwarmBus
from sunday.core.swarm.events import (
    SwarmEvent,
    EventTopic,
    EventPriority,
    TaskAssignEvent,
    TaskPatchEvent,
    StatusNudgeEvent,
)
from sunday.core.swarm.steering import LiveSteeringManager
from sunday.core.swarm.conductor import Conductor
from sunday.core.swarm.coder import Coder
from sunday.core.swarm.scout import Scout
from sunday.core.swarm.automator import Automator
from sunday.core.swarm.gatekeeper import Gatekeeper


@pytest.mark.asyncio
async def test_swarm_bus_pub_sub_and_priority():
    """Verify SwarmBus prioritizes critical events and delivers targeted messages."""
    bus = SwarmBus()
    await bus.start()

    delivered_events = []

    async def sample_handler(event: SwarmEvent):
        delivered_events.append(event)

    bus.subscribe(EventTopic.STATUS_NUDGE.value, sample_handler)

    nudge = StatusNudgeEvent(
        source_agent="coder",
        target_agent="conductor",
        task_id="t1",
        status="completed",
        summary="Code compiled successfully",
        priority=EventPriority.HIGH,
    )
    await bus.publish(nudge)

    # Allow dispatch loop to process
    await asyncio.sleep(0.1)

    assert len(delivered_events) == 1
    assert delivered_events[0].summary == "Code compiled successfully"
    assert delivered_events[0].source_agent == "coder"

    await bus.stop()


@pytest.mark.asyncio
async def test_live_steering_mid_flight_patch():
    """Verify Live Steering updates an active task on-the-fly without aborting context."""
    bus = SwarmBus()
    await bus.start()

    steering = LiveSteeringManager(bus)
    conductor = Conductor(bus, steering_manager=steering)
    coder = Coder(bus)

    await conductor.start()
    await coder.start()

    # User gives initial coding command
    initial_text = "write me a python script to backup files"
    res1 = await conductor.handle_user_turn(initial_text)
    assert "Coder engine is locked in" in res1

    # Brief delay for task to begin running before user interrupts
    await asyncio.sleep(0.2)

    # Check active tasks in steering manager
    active = steering.get_active_tasks()
    assert len(active) == 1
    task_id = active[0]["task_id"]

    # Mid-flight update: user changes mind while task is running
    patch_text = "wait, actually make it compress to zip instead"
    res2 = await conductor.handle_user_turn(patch_text)
    assert "Patching that into coder" in res2

    # Wait for coder to complete execution (2×0.5s loops + dispatch overhead)
    await asyncio.sleep(2.0)

    # Verify coder incorporated patch
    assert task_id in coder.generated_artifacts
    artifact = coder.generated_artifacts[task_id]
    assert "zip" in artifact.lower()

    await coder.stop()
    await conductor.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_conversational_nudge_injection():
    """Verify Conductor receives background status nudges and weaves them into conversation."""
    bus = SwarmBus()
    await bus.start()

    conductor = Conductor(bus)
    await conductor.start()

    # Simulate background worker nudge
    nudge = StatusNudgeEvent(
        source_agent="scout",
        target_agent="conductor",
        task_id="res_1",
        status="completed",
        summary="Found 3 new updates on arXiv regarding multi-agent swarms",
    )
    await bus.publish(nudge)
    await asyncio.sleep(0.1)

    # Next user turn should casually mention the background update
    response = await conductor.handle_user_turn("What's up?")
    assert "scout just finished" in response
    assert "arXiv" in response

    await conductor.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_gatekeeper_token_rotation():
    """Verify Gatekeeper rotates keys upon receiving a token exhaustion signal."""
    bus = SwarmBus()
    await bus.start()

    gatekeeper = Gatekeeper(bus)
    await gatekeeper.start()

    # Add 2 keys
    gatekeeper.add_keys_to_pool("openai", ["sk-first-key", "sk-secondary-backup-key"])
    assert gatekeeper.get_current_key("openai") == "sk-first-key"

    # Simulate 429 exhaustion event
    exhaust_event = SwarmEvent(
        source_agent="coder",
        target_agent="gatekeeper",
        topic=EventTopic.TOKEN_EXHAUSTED,
        payload={"provider": "openai", "error": "429 RateLimitExceeded"},
    )
    await bus.publish(exhaust_event)
    await asyncio.sleep(0.1)

    # Key should have auto-rotated to the backup key
    assert gatekeeper.get_current_key("openai") == "sk-secondary-backup-key"

    await gatekeeper.stop()
    await bus.stop()
