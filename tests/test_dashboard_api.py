import pytest
from fastapi.testclient import TestClient
from sunday.dashboard.api.main import app, ToolExecutionRequest
from sunday.tools.registry import ToolRegistry, Tool, ToolRisk, ToolResult
import inspect

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_tools():
    # Clear tools before each test
    original_tools = dict(ToolRegistry._tools)
    ToolRegistry._tools = {}

    async def dummy_func(arg1, arg2="default"):
        if arg1 == "error":
            raise ValueError("Test error")
        if arg1 == "fail":
            return ToolResult(success=False, error="Test failure")
        return ToolResult(success=True, data={"arg1": arg1, "arg2": arg2})

    ToolRegistry.register(Tool(
        name="test_tool",
        description="A test tool",
        func=dummy_func,
        risk=ToolRisk.LOW,
        approval_required=False,
        persona="both",
        category="test"
    ))
    yield
    ToolRegistry._tools = original_tools

def test_execute_tool_success():
    response = client.post(
        "/api/tools/execute",
        json={"tool_name": "test_tool", "args": {"arg1": "value1"}}
    )
    assert response.status_code == 200
    assert response.json() == {
        "tool": "test_tool",
        "success": True,
        "data": {"arg1": "value1", "arg2": "default"},
        "error": None
    }

def test_execute_tool_not_found():
    response = client.post(
        "/api/tools/execute",
        json={"tool_name": "nonexistent_tool", "args": {}}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_execute_tool_failure_result():
    response = client.post(
        "/api/tools/execute",
        json={"tool_name": "test_tool", "args": {"arg1": "fail"}}
    )
    assert response.status_code == 200
    assert response.json() == {
        "tool": "test_tool",
        "success": False,
        "data": None,
        "error": "Test failure"
    }

def test_execute_tool_exception():
    response = client.post(
        "/api/tools/execute",
        json={"tool_name": "test_tool", "args": {"arg1": "error"}}
    )
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]

def test_execute_tool_invalid_args():
    response = client.post(
        "/api/tools/execute",
        json={"tool_name": "test_tool", "args": {"invalid_arg": "value"}}
    )
    # The dummy_func doesn't accept invalid_arg, it should raise TypeError which becomes 500
    assert response.status_code == 500
    assert "unexpected keyword argument" in response.json()["detail"]
