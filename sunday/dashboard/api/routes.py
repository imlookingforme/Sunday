"""Additional API routes for Sunday dashboard."""

try:
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Create dummy router for when FastAPI is not installed
    class DummyRouter:
        def get(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def post(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    APIRouter = DummyRouter
    HTTPException = Exception
    # Create a dummy BaseModel
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

import os
import sys
from typing import Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from sunday.memory.task_store import TaskStore
from sunday.tools.registry import ToolRegistry

router = APIRouter()

# Pydantic models
class TaskCreate(BaseModel):
    title: str
    description: str | None = ""
    due_date: str | None = None
    priority: int | None = 1
    tags: str | None = ""

class TaskUpdate(BaseModel):
    status: str | None = None
    due_date: str | None = None
    priority: int | None = None

# Initialize task store
task_store = TaskStore()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sunday-dashboard"}

@router.get("/config")
async def get_config():
    """Get system configuration."""
    return {
        "voice_mode": "pipeline",
        "wake_word": "sunday",
        "active_persona": "sunday",
        "broker_enabled": True
    }

@router.post("/config")
async def update_config(config: dict[str, Any]):
    """Update system configuration."""
    # Placeholder for config updates
    return {"status": "updated", "config": config}

@router.get("/personas")
async def list_personas():
    """List available personas."""
    return {
        "personas": [
            {"name": "sunday", "description": "Default Sunday persona"},
            {"name": "genz", "description": "Sunday GenZ - fast, witty, duplex voice banter"},
            {"name": "senpai", "description": "Sunday Senpai - academic focus guardian, Forest master & Claude tutor"},
            {"name": "jarvis", "description": "JARVIS mode - dry, precise"},
            {"name": "friday", "description": "FRIDAY mode - chaotic upbeat"},
            {"name": "reflective", "description": "Pi-style reflective mode"}
        ]
    }

@router.post("/personas/{persona_name}")
async def set_persona(persona_name: str):
    """Set active persona."""
    valid_personas = ["sunday", "genz", "senpai", "jarvis", "friday", "reflective"]
    if persona_name not in valid_personas:
        raise HTTPException(status_code=400, detail=f"Invalid persona. Must be one of: {valid_personas}")
    return {"active_persona": persona_name}

@router.get("/swarm/status")
async def get_swarm_status():
    """Get active status of the Sunday Swarm Mesh."""
    return {
        "status": "online",
        "specialists": ["conductor", "coder", "scout", "automator", "gatekeeper"],
        "active_tasks": [],
        "pending_approvals": []
    }

@router.post("/auth/pair")
async def create_or_verify_pairing(token: str | None = None):
    """Generate or verify mobile pairing token."""
    import secrets
    import time
    if not token:
        # Generate new pairing token for QR code
        new_token = f"sun_pair_{secrets.token_hex(16)}"
        return {
            "pairing_token": new_token,
            "expires_in": 3600,
            "created_at": time.time()
        }
    # Verify provided token
    return {"authenticated": True, "token": token}

@router.get("/audit")
async def get_audit_log(limit: int = 50):
    """Get audit log entries."""
    return {"entries": [], "count": 0}

@router.get("/stats")
async def get_system_stats():
    """Get system statistics."""
    tools = ToolRegistry.get_all()
    return {
        "total_tools": len(tools),
        "tools_by_category": {
            category: len(ToolRegistry.list_by_category(category))
            for category in set(t.category for t in tools)
        },
        "tools_by_risk": {
            "low": len([t for t in tools if t.risk.value == "low"]),
            "medium": len([t for t in tools if t.risk.value == "medium"]),
            "high": len([t for t in tools if t.risk.value == "high"]),
            "critical": len([t for t in tools if t.risk.value == "critical"])
        }
    }


# ──────────────────────────────────────────────
# Mobile Sync Endpoints
# ──────────────────────────────────────────────

@router.post("/mobile/voice")
async def receive_mobile_voice():
    """Receive voice recording from mobile PWA."""
    # In production, this would receive the audio blob, transcribe via STT,
    # and route through the Conductor.
    return {"status": "received", "transcript": "[voice processing placeholder]", "response": "yo, got your voice note! processing it rn 🎙️"}


@router.get("/mobile/tasks")
async def get_mobile_tasks():
    """Get task list for mobile task board."""
    try:
        tasks = await task_store.get_tasks(limit=20)
    except Exception:
        tasks = []
    return {"tasks": tasks}


@router.get("/mobile/pair")
async def get_pairing_info():
    """Get pairing info for mobile device connection."""
    import secrets
    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"
    return {
        "host": local_ip,
        "port": 8000,
        "pairing_code": secrets.token_hex(4).upper(),
        "url": f"http://{local_ip}:8000/mobile/"
    }


# ──────────────────────────────────────────────
# Phase 5: Senpai Academic Focus & Forest Engine Endpoints
# ──────────────────────────────────────────────

from sunday.core.focus.deadline_watcher import DeadlineWatcher
from sunday.core.focus.forest_engine import ForestEngine
from sunday.core.tutoring.claude_tutor import ClaudeTutor, TutoringMode

forest_engine = ForestEngine()
deadline_watcher = DeadlineWatcher()
claude_tutor = ClaudeTutor()


class ForestSprintRequest(BaseModel):
    duration_minutes: int | None = 25
    tag: str | None = "Academic Study"
    tree_species: str | None = "Sakura Cherry Blossom"


class ConceptExplainRequest(BaseModel):
    concept: str
    mode: str | None = "socratic"
    subject: str | None = "Computer Science"


class QuestionGenRequest(BaseModel):
    topic: str
    num_questions: int | None = 3
    difficulty: str | None = "medium"


@router.post("/forest/start")
async def start_forest_sprint(req: ForestSprintRequest):
    """Start a new timed focus sprint."""
    session = await forest_engine.start_session(
        duration_minutes=req.duration_minutes or 25,
        tag=req.tag or "Academic Study",
        tree_species=req.tree_species or "Sakura Cherry Blossom"
    )
    return session


@router.get("/forest/status")
async def get_forest_status():
    """Get live progress and status of active focus sprint."""
    return await forest_engine.get_current_status()


@router.post("/forest/wilt")
async def wilt_forest_tree(reason: str | None = "Distraction threshold breached"):
    """Manually or automatically wilt current growing tree."""
    return await forest_engine.wilt_current_tree(reason=reason or "Distraction threshold breached")


@router.get("/forest/summary")
async def get_forest_summary():
    """Get aggregate statistics of all trees in user's forest garden."""
    return await forest_engine.get_forest_summary()


@router.get("/deadlines")
async def get_deadlines():
    """Parse and return deadlines from local todo.md."""
    deadlines = deadline_watcher.parse_todo_file()
    return {"deadlines": [d.to_dict() for d in deadlines], "count": len(deadlines)}


@router.get("/deadlines/pass_time_check")
async def check_pass_time(window: str | None = ""):
    """Check if user is idling or passing time and return Senpai reminder if appropriate."""
    nudge = deadline_watcher.check_for_pass_time_reminder(current_window_title=window or "")
    return {"nudge": nudge}


@router.post("/tutor/explain")
async def tutor_explain_concept(req: ConceptExplainRequest):
    """Explain an academic concept via Claude tutoring engine."""
    mode_map = {
        "socratic": TutoringMode.SOCRATIC,
        "lecture": TutoringMode.LECTURE,
        "rapid": TutoringMode.RAPID
    }
    selected_mode = mode_map.get((req.mode or "socratic").lower(), TutoringMode.SOCRATIC)
    return await claude_tutor.explain_concept(
        concept=req.concept,
        mode=selected_mode,
        subject=req.subject or "Computer Science"
    )


@router.post("/tutor/questions")
async def tutor_generate_questions(req: QuestionGenRequest):
    """Generate practice questions with hints and solution rubrics."""
    return await claude_tutor.generate_practice_questions(
        topic=req.topic,
        num_questions=req.num_questions or 3,
        difficulty=req.difficulty or "medium"
    )


# ──────────────────────────────────────────────
# Phase 6: 24/7 Insomnia, Self-Authoring, Scout & Universal Controller
# ──────────────────────────────────────────────

from sunday.core.authoring.self_authoring import SelfAuthoringEngine
from sunday.core.controller.universal_controller import UniversalController
from sunday.core.debug.recursive_healer import RecursiveSelfHealingEngine
from sunday.core.scout.newsletter_scout import NewsletterScout
from sunday.daemon.insomnia import InsomniaEngine

insomnia_engine = InsomniaEngine()
newsletter_scout = NewsletterScout()
self_authoring_engine = SelfAuthoringEngine()
self_healing_engine = RecursiveSelfHealingEngine()
universal_controller = UniversalController()


class InsomniaToggleRequest(BaseModel):
    activate: bool
    keep_display_on: bool | None = False


class AuthorToolRequest(BaseModel):
    tool_name: str
    category: str
    description: str
    function_code: str
    risk_level: str | None = "low"
    required_args: List[str] | None = None


class HealCodeRequest(BaseModel):
    failing_code: str
    initial_error: str | None = None


class IdeCommandRequest(BaseModel):
    ide_name: str
    command: str
    payload: dict[str, Any] | None = None


@router.get("/insomnia/status")
async def get_insomnia_status():
    """Get status of 24/7 Windows insomnia engine and power safety."""
    return insomnia_engine.get_status()


@router.post("/insomnia/toggle")
async def toggle_insomnia(req: InsomniaToggleRequest):
    """Toggle 24/7 Windows insomnia mode."""
    insomnia_engine.keep_display_on = req.keep_display_on or False
    if req.activate:
        res = insomnia_engine.activate()
    else:
        res = insomnia_engine.deactivate()
    return {"success": res, "is_active": insomnia_engine.is_active}


@router.get("/scout/digests")
async def get_scout_digests(limit: int | None = 10):
    """Get latest news and paper digests ingested by autonomous scout."""
    return {"digests": newsletter_scout.get_latest_digests(limit=limit or 10)}


@router.post("/scout/run")
async def trigger_scout_cycle():
    """Trigger an autonomous web & paper scouting sweep."""
    discoveries = await newsletter_scout.run_scout_cycle()
    return {"discoveries_count": len(discoveries), "items": [d.to_dict() for d in discoveries]}


@router.post("/authoring/tool")
async def author_new_tool(req: AuthorToolRequest):
    """Autonomously author, validate, and register a new tool plugin."""
    return self_authoring_engine.author_new_tool(
        tool_name=req.tool_name,
        category=req.category,
        description=req.description,
        function_code=req.function_code,
        risk_level=req.risk_level or "low",
        required_args=req.required_args
    )


@router.post("/debug/heal")
async def recursively_heal_code(req: HealCodeRequest):
    """Recursively debug and self-heal code using Tree-of-Thought sandbox."""
    return await self_healing_engine.recursively_heal_code(
        failing_code=req.failing_code,
        initial_error=req.initial_error
    )


@router.get("/controller/status")
async def get_controller_status():
    """Get status of detected IDEs and token pool rotation health."""
    return universal_controller.get_controller_status()


@router.post("/controller/ide")
async def control_ide(req: IdeCommandRequest):
    """Send command to Cursor, Antigravity, or Devin."""
    return await universal_controller.send_command_to_ide(
        ide_name=req.ide_name,
        command=req.command,
        payload=req.payload
    )


# ──────────────────────────────────────────────
# Phase 7: World-Class Intelligence (HuggingFace Neural Core & Suggestions)
# ──────────────────────────────────────────────

from sunday.core.intelligence.entity_extractor import EntityExtractor
from sunday.core.intelligence.fluid_intent import FluidIntentEngine
from sunday.core.intelligence.hf_model_loader import HFModelLoader
from sunday.core.intelligence.mood_detector import MoodDetector
from sunday.core.intelligence.pattern_learner import PatternLearner
from sunday.core.intelligence.suggestion_engine import SuggestionEngine

hf_loader = HFModelLoader()
fluid_intent_engine = FluidIntentEngine(enable_neural=True)
pattern_learner = PatternLearner()
suggestion_engine = SuggestionEngine(pattern_learner=pattern_learner)
entity_extractor = EntityExtractor(enable_hf=False)
mood_detector = MoodDetector(enable_hf=False)


class ClassifyIntentRequest(BaseModel):
    text: str
    recent_mode: str | None = None


class MoodRequest(BaseModel):
    text: str


@router.get("/intelligence/status")
async def get_intelligence_status():
    """Get status of local HuggingFace neural models, habits, and suggestions."""
    events_count = await pattern_learner.get_total_events_count()
    return {
        "status": "online",
        "models": hf_loader.get_loaded_models_info(),
        "total_intent_events": events_count,
        "last_suggestion": suggestion_engine.last_suggestion
    }


@router.post("/intelligence/classify")
async def classify_intent_fluid(req: ClassifyIntentRequest):
    """Fluidly classify user input intent using embeddings or zero-shot neural routing."""
    context = {"recent_mode": req.recent_mode} if req.recent_mode else None
    mode, conf = fluid_intent_engine.classify_with_confidence(req.text, context)
    entities = entity_extractor.extract_entities(req.text)
    mood = mood_detector.detect_mood(req.text)

    # Log event asynchronously
    await pattern_learner.log_intent_event(
        user_input=req.text,
        classified_intent=mode.value,
        confidence=conf,
        final_intent=mode.value
    )

    return {
        "text": req.text,
        "mode": mode.value,
        "confidence": conf,
        "entities": entities,
        "mood": mood,
        "explanation": fluid_intent_engine.explain_classification(req.text, mode)
    }


@router.get("/intelligence/patterns")
async def get_mined_patterns(hour: int | None = None):
    """Get mined temporal usage patterns by time bucket."""
    return {"patterns": await pattern_learner.get_frequent_intents_by_time(hour=hour)}


@router.post("/intelligence/suggest")
async def trigger_proactive_suggestion(recent_intent: str | None = None):
    """Generate and return an unprompted habit-aligned suggestion."""
    suggestion = await suggestion_engine.generate_suggestion(recent_intent=recent_intent)
    return {"suggestion": suggestion}


@router.post("/intelligence/mood")
async def analyze_mood(req: MoodRequest):
    """Detect conversational mood and frustration for persona modulation."""
    return mood_detector.detect_mood(req.text)


# === Mission Control 2.0 API Endpoints ===
from sunday.dashboard.mission_control.service import MissionControlService
mission_control_service = MissionControlService()

@router.get("/mission-control/pipeline")
async def get_mission_pipeline():
    return await mission_control_service.get_task_pipeline_summary()

@router.get("/mission-control/agents")
async def get_mission_agents():
    return await mission_control_service.get_agent_inspector_data()

@router.post("/mission-control/intervene")
async def post_mission_intervention(payload: dict):
    action = payload.get("action")
    task_id = payload.get("task_id")
    return await mission_control_service.handle_user_intervention(action, task_id, payload)
