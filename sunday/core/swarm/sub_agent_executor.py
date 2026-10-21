"""Autonomous Sub-Agent and Background Task Execution Engine for Sunday AI."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SubAgentProcess:
    """Represents a running background script/sub-agent process."""

    def __init__(self, agent_id: str, name: str, process: asyncio.subprocess.Process, script_path: str):
        self.agent_id = agent_id
        self.name = name
        self.process = process
        self.script_path = script_path
        self.start_time = time.time()
        self.logs: List[str] = []
        self._monitor_task: Optional[asyncio.Task] = None

    def is_alive(self) -> bool:
        return self.process.returncode is None


class SubAgentExecutor:
    """Manages spawning, execution, log collection, and lifecycle of sub-agents."""

    def __init__(self):
        self._running_agents: Dict[str, SubAgentProcess] = {}
        self._lock = asyncio.Lock()

    async def execute_script(
        self, script_content: str, language: str = "python", timeout: int = 300
    ) -> Dict[str, Any]:
        """Execute a standalone script synchronously and capture output."""
        start_time = time.time()
        suffix = ".py" if language == "python" else ".bat"

        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as f:
            f.write(script_content)
            temp_path = f.name

        try:
            cmd = [sys.executable, temp_path] if language == "python" else ["cmd.exe", "/c", temp_path]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                duration = time.time() - start_time
                stdout_str = stdout_data.decode("utf-8", errors="replace")
                stderr_str = stderr_data.decode("utf-8", errors="replace")
                return {
                    "success": proc.returncode == 0,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "return_code": proc.returncode,
                    "duration": round(duration, 3),
                }
            except asyncio.TimeoutError:
                proc.kill()
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout} seconds",
                    "return_code": -1,
                    "duration": timeout,
                }
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    async def execute_command(self, command: str, cwd: Optional[str] = None, timeout: int = 60) -> Dict[str, Any]:
        """Execute a shell command asynchronously."""
        start_time = time.time()
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        try:
            stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "success": proc.returncode == 0,
                "stdout": stdout_data.decode("utf-8", errors="replace"),
                "stderr": stderr_data.decode("utf-8", errors="replace"),
                "return_code": proc.returncode,
                "duration": round(time.time() - start_time, 3),
            }
        except asyncio.TimeoutError:
            proc.kill()
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "return_code": -1,
                "duration": timeout,
            }

    async def spawn_background_agent(self, name: str, script_content: str) -> str:
        """Spawn a persistent background worker agent."""
        agent_id = f"agent_{int(time.time())}_{len(self._running_agents)}"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(script_content)
            temp_path = f.name

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        sub_proc = SubAgentProcess(agent_id, name, proc, temp_path)
        sub_proc._monitor_task = asyncio.create_task(self._stream_logs(sub_proc))

        async with self._lock:
            self._running_agents[agent_id] = sub_proc

        logger.info(f"Spawned background agent {name} (id={agent_id})")
        return agent_id

    async def _stream_logs(self, agent: SubAgentProcess) -> None:
        """Read standard output lines asynchronously into agent log buffer."""
        try:
            while agent.is_alive():
                line = await agent.process.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                agent.logs.append(decoded)
                if len(agent.logs) > 200:
                    agent.logs.pop(0)
        except Exception:
            pass
        finally:
            if os.path.exists(agent.script_path):
                try:
                    os.remove(agent.script_path)
                except OSError:
                    pass

    async def list_running_agents(self) -> List[Dict[str, Any]]:
        """List active background sub-agents."""
        async with self._lock:
            # Clean up dead processes
            for aid in list(self._running_agents.keys()):
                if not self._running_agents[aid].is_alive():
                    del self._running_agents[aid]

            return [
                {
                    "agent_id": p.agent_id,
                    "name": p.name,
                    "uptime_seconds": round(time.time() - p.start_time, 1),
                    "alive": p.is_alive(),
                }
                for p in self._running_agents.values()
            ]

    async def kill_agent(self, agent_id: str) -> bool:
        """Terminate a background agent process."""
        async with self._lock:
            agent = self._running_agents.get(agent_id)
            if not agent:
                return False

            try:
                agent.process.kill()
                await agent.process.wait()
            except Exception:
                pass

            if agent._monitor_task and not agent._monitor_task.done():
                agent._monitor_task.cancel()

            if os.path.exists(agent.script_path):
                try:
                    os.remove(agent.script_path)
                except OSError:
                    pass

            del self._running_agents[agent_id]
            logger.info(f"Killed background agent {agent_id}")
            return True

    def get_agent_logs(self, agent_id: str, tail: int = 50) -> List[str]:
        """Fetch collected stdout logs for an agent."""
        agent = self._running_agents.get(agent_id)
        if not agent:
            return []
        return agent.logs[-tail:]
