import pytest
import asyncio
from sunday.core.sub_agent import SubAgent, SubAgentManager

@pytest.mark.asyncio
async def test_sub_agent_execution():
    manager = SubAgentManager()
    
    code = """
import sys
print("Hello from SubAgent!")
sys.exit(0)
    """
    
    result = await manager.spawn_agent("TestAgent", code)
    
    assert result["success"] is True
    assert result["return_code"] == 0
    assert "Hello from SubAgent!" in result["stdout"]

@pytest.mark.asyncio
async def test_sub_agent_failure():
    manager = SubAgentManager()
    
    code = """
import sys
print("Failing...")
sys.exit(1)
    """
    
    result = await manager.spawn_agent("FailAgent", code)
    
    assert result["success"] is False
    assert result["return_code"] == 1
    assert "Failing..." in result["stdout"]
