"""Tests for Custom Agent Builder tools and SQLite persistence."""

import os
import pytest
from pathlib import Path
from sunday.tools.custom_agents import (
    create_custom_agent,
    run_custom_agent,
    list_custom_agents,
    delete_custom_agent,
    export_custom_agent,
    import_custom_agent,
)


@pytest.mark.asyncio
async def test_custom_agent_lifecycle():
    """Verify creating, listing, running, exporting, and deleting a custom agent."""
    agent_name = "Test Research Specialist"
    prompt = "You are a specialist research agent that analyzes academic papers."

    # 1. Create agent
    create_res = await create_custom_agent(
        name=agent_name,
        system_prompt=prompt,
        description="Handles arXiv paper evaluations",
        allowed_tools=["web_search", "academic_search"],
    )
    assert create_res.success is True
    agent_id = create_res.data["agent_id"]
    yaml_path = create_res.data["yaml_path"]
    assert os.path.exists(yaml_path)

    # 2. List agents
    list_res = await list_custom_agents()
    assert list_res.success is True
    assert any(a["id"] == agent_id for a in list_res.data["agents"])

    # 3. Run agent
    run_res = await run_custom_agent(
        agent_name_or_id=agent_id,
        task="Summarize latest quantum computing breakthroughs",
    )
    assert run_res.success is True
    assert run_res.data["status"] == "completed"
    assert "quantum computing" in run_res.data["task"]

    # 4. Export agent
    export_path = "sunday/data/agents/exported_test_agent.yaml"
    export_res = await export_custom_agent(agent_name_or_id=agent_id, file_path=export_path)
    assert export_res.success is True
    assert os.path.exists(export_path)

    # 5. Delete agent
    del_res = await delete_custom_agent(agent_name_or_id=agent_id)
    assert del_res.success is True

    # Verify deletion
    list_after = await list_custom_agents()
    assert not any(a["id"] == agent_id for a in list_after.data["agents"])

    # Clean up test export
    if os.path.exists(export_path):
        os.unlink(export_path)
    if os.path.exists(yaml_path):
        os.unlink(yaml_path)
