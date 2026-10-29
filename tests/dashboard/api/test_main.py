import pytest
from fastapi.testclient import TestClient
from sunday.dashboard.api.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200

def test_execute_tool_success():
    from sunday.tools.registry import tool, ToolRegistry

    # Register a dummy tool
    @tool(name="dummy_tool")
    async def dummy_tool(x, y):
        class DummyResult:
            def __init__(self, success, data, error=None):
                self.success = success
                self.data = data
                self.error = error
        return DummyResult(True, {"result": x + y})

    try:
        response = client.post("/api/tools/execute", json={"tool_name": "dummy_tool", "args": {"x": 1, "y": 2}})
        assert response.status_code == 200
        assert response.json() == {"tool": "dummy_tool", "success": True, "data": {"result": 3}, "error": None}
    finally:
        ToolRegistry._tools.pop("dummy_tool", None)


def test_execute_tool_not_found():
    response = client.post("/api/tools/execute", json={"tool_name": "non_existent_tool", "args": {}})
    assert response.status_code == 404
    assert response.json() == {"detail": "Tool 'non_existent_tool' not found"}

def test_execute_tool_exception():
    from sunday.tools.registry import tool, ToolRegistry

    # Register a tool that raises an exception
    @tool(name="error_tool")
    async def error_tool():
        raise ValueError("Simulated error")

    try:
        response = client.post("/api/tools/execute", json={"tool_name": "error_tool", "args": {}})
        assert response.status_code == 500
        assert response.json() == {"detail": "Simulated error"}
    finally:
        ToolRegistry._tools.pop("error_tool", None)
