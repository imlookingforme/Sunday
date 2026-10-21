"""Typed event definitions for the Sunday Swarm Mesh."""

import time
import uuid
from enum import IntEnum, Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventPriority(IntEnum):
    """Event priority levels (lower integer = higher processing priority)."""
    CRITICAL = 1      # System alerts, safety emergency, immediate interrupt
    HIGH = 2          # Status nudges to conversational voice, approval requests
    NORMAL = 3        # Standard task delegation and execution steps
    LOW = 4           # Background telemetry, logging, cache warmups


class EventTopic(str, Enum):
    """Standard Swarm event topics."""
    TASK_ASSIGN = "task_assign"
    TASK_PATCH = "task_patch"           # Live steering / mid-flight parameter change
    TASK_CANCEL = "task_cancel"
    STATUS_NUDGE = "status_nudge"       # Milestone or completion notice for voice conductor
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    AGENT_HEARTBEAT = "agent_heartbeat"
    BROADCAST = "broadcast"
    TOKEN_EXHAUSTED = "token_exhausted"  # Signal to gatekeeper to rotate account/key


class SwarmEvent(BaseModel):
    """Base Swarm Event envelope."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_agent: str
    target_agent: Optional[str] = None  # None indicates broadcast to all subscribers
    topic: EventTopic
    priority: EventPriority = EventPriority.NORMAL
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    correlation_id: Optional[str] = None  # Groups related events (e.g. initial task + patches)


class TaskAssignEvent(SwarmEvent):
    """Event dispatched to assign a new task to a specialist."""
    topic: EventTopic = EventTopic.TASK_ASSIGN
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    instruction: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        if not self.correlation_id:
            self.correlation_id = self.task_id


class TaskPatchEvent(SwarmEvent):
    """Event dispatched for live steering mid-flight task updates."""
    topic: EventTopic = EventTopic.TASK_PATCH
    task_id: str
    patch_instruction: str
    patch_params: Dict[str, Any] = Field(default_factory=dict)


class StatusNudgeEvent(SwarmEvent):
    """Milestone or progress nudge sent to Conductor to weave into conversation."""
    topic: EventTopic = EventTopic.STATUS_NUDGE
    priority: EventPriority = EventPriority.HIGH
    task_id: str
    status: str                         # "progress", "completed", "failed", "blocked"
    summary: str                        # Human-readable summary for voice speech
    details: Dict[str, Any] = Field(default_factory=dict)


class ApprovalRequestEvent(SwarmEvent):
    """High-risk action requiring approval via UI or voice confirmation."""
    topic: EventTopic = EventTopic.APPROVAL_REQUEST
    priority: EventPriority = EventPriority.CRITICAL
    ticket_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "HIGH"
    rationale: str = ""
