"""FastAPI backend for Sunday dashboard."""

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Create a dummy app for when FastAPI is not installed
    class DummyApp:
        def __init__(self, *args, **kwargs):
            pass
        def add_middleware(self, *args, **kwargs):
            pass
        def include_router(self, *args, **kwargs):
            pass
        def get(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def post(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    FastAPI = DummyApp
    HTTPException = Exception
    CORSMiddleware = None
    StreamingResponse = None
    # Create a dummy BaseModel
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

from typing import Optional, Dict, Any
from .sse import sse_event_generator
from .routes import router as additional_routes
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from sunday.tools.registry import ToolRegistry
from sunday.core.orchestrator import Orchestrator

app = FastAPI(title="Sunday Dashboard API")

# CORS middleware
if FASTAPI_AVAILABLE:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include additional routes
if FASTAPI_AVAILABLE:
    app.include_router(additional_routes, prefix="/api", tags=["system"])

    # Static file mounts for Multi-Form GUI
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path
    static_root = Path(__file__).parent.parent / "static"
    if static_root.exists():
        app.mount("/static", StaticFiles(directory=str(static_root)), name="static")
        if (static_root / "mobile").exists():
            app.mount("/mobile", StaticFiles(directory=str(static_root / "mobile"), html=True), name="mobile")
        if (static_root / "sidecar").exists():
            app.mount("/sidecar", StaticFiles(directory=str(static_root / "sidecar"), html=True), name="sidecar")
        if (static_root / "immersion").exists():
            app.mount("/immersion", StaticFiles(directory=str(static_root / "immersion"), html=True), name="immersion")

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    persona: Optional[str] = "sunday"

class ToolExecutionRequest(BaseModel):
    tool_name: str
    args: Dict[str, Any]

class IntelligenceModuleData(BaseModel):
    module: str
    data: Dict[str, Any]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State management
class DashboardState:
    """Shared state for dashboard."""
    def __init__(self):
        self.orb_state = "idle"
        self.intelligence_data = {}
        self.connected_clients = 0
    
    def set_orb_state(self, state: str):
        """Set orb state."""
        self.orb_state = state
    
    def update_intelligence(self, module: str, data: dict):
        """Update intelligence module data."""
        self.intelligence_data[module] = data
    
    def add_client(self):
        """Add connected client."""
        self.connected_clients += 1
    
    def remove_client(self):
        """Remove connected client."""
        self.connected_clients = max(0, self.connected_clients - 1)

dashboard_state = DashboardState()

@app.get("/")
async def root():
    """Root endpoint - Serves Fullscreen Immersion Dashboard or redirects."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    immersion_file = Path(__file__).parent.parent / "static" / "immersion" / "index.html"
    if immersion_file.exists():
        return FileResponse(str(immersion_file))
    return {"message": "Sunday Dashboard API", "status": "online"}

@app.get("/api/state")
async def get_state():
    """Get current dashboard state."""
    return {
        "orb_state": dashboard_state.orb_state,
        "intelligence_data": dashboard_state.intelligence_data,
        "connected_clients": dashboard_state.connected_clients
    }

@app.post("/api/orb/state")
async def set_orb_state(state: str):
    """Set orb state."""
    valid_states = ["idle", "listening", "thinking", "speaking", "searching", "coding"]
    if state not in valid_states:
        return {"error": f"Invalid state. Must be one of: {valid_states}"}
    
    dashboard_state.set_orb_state(state)
    return {"orb_state": state}

@app.get("/api/events")
async def events():
    """SSE event stream for real-time updates."""
    if not FASTAPI_AVAILABLE:
        return {"error": "FastAPI not installed"}
    return StreamingResponse(
        sse_event_generator(dashboard_state),
        media_type="text/event-stream"
    )

@app.post("/api/intelligence/{module}")
async def update_intelligence_module(module: str, data: dict):
    """Update intelligence module data."""
    dashboard_state.update_intelligence(module, data)
    return {"module": module, "status": "updated"}

@app.get("/api/intelligence/{module}")
async def get_intelligence_module(module: str):
    """Get intelligence module data."""
    return dashboard_state.intelligence_data.get(module, {})

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Process chat message through orchestrator."""
    try:
        # Placeholder - would use actual orchestrator
        response = f"Response to: {request.message}"
        return {"message": response, "persona": request.persona}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools")
async def list_tools():
    """List all available tools."""
    tools = ToolRegistry.get_all()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "risk": t.risk.value,
                "approval_required": t.approval_required
            }
            for t in tools
        ],
        "count": len(tools)
    }

@app.get("/api/tools/{category}")
async def list_tools_by_category(category: str):
    """List tools by category."""
    tools = ToolRegistry.list_by_category(category)
    return {
        "category": category,
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "risk": t.risk.value
            }
            for t in tools
        ],
        "count": len(tools)
    }

@app.post("/api/tools/execute")
async def execute_tool(request: ToolExecutionRequest):
    """Execute a tool."""
    try:
        tool = ToolRegistry.get(request.tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{request.tool_name}' not found")
        
        # Execute tool
        result = await tool.func(**request.args)
        return {
            "tool": request.tool_name,
            "success": result.success,
            "data": result.data,
            "error": result.error
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/stats")
async def get_memory_stats():
    """Get memory statistics."""
    try:
        # Placeholder - would use actual memory system
        return {
            "total_episodes": 0,
            "avg_surprise": 0.0,
            "high_surprise_count": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks")
async def get_tasks(status: Optional[str] = None):
    """Get tasks."""
    try:
        # Placeholder - would use actual task store
        return {"tasks": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
