import pytest
from sunday.core.swarm.sub_agent_executor import SubAgentExecutor


@pytest.mark.asyncio
async def test_sub_agent_executor_script():
    executor = SubAgentExecutor()
    script = "print('Hello from SubAgent'); import sys; sys.exit(0)"

    res = await executor.execute_script(script, language="python")
    assert res["success"] is True
    assert "Hello from SubAgent" in res["stdout"]
    assert res["return_code"] == 0


@pytest.mark.asyncio
async def test_sub_agent_background_lifecycle():
    executor = SubAgentExecutor()
    bg_script = "import time; print('running'); time.sleep(5)"

    agent_id = await executor.spawn_background_agent("worker_test", bg_script)
    assert agent_id.startswith("agent_")

    running = await executor.list_running_agents()
    assert any(a["agent_id"] == agent_id for a in running)

    killed = await executor.kill_agent(agent_id)
    assert killed is True
