"""Sub-Agent Manager for running autonomous background scripts."""

import asyncio
import logging
import os
import tempfile
import sys
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SubAgent:
    """Represents an autonomous background script executed by Sunday."""

    def __init__(self, name: str, code: str):
        self.name = name
        self.code = code
        self.task_id = f"subagent_{id(self)}"
        self._process: Optional[asyncio.subprocess.Process] = None
        self._temp_file: Optional[str] = None

    async def execute(self) -> Dict[str, Any]:
        """Write the code to a temp file and execute it asynchronously."""
        # Create temp python file
        fd, temp_path = tempfile.mkstemp(suffix=".py", prefix=f"sunday_{self.name}_")
        with os.fdopen(fd, "w") as f:
            f.write(self.code)
        
        self._temp_file = temp_path
        logger.info(f"SubAgent [{self.name}] starting execution: {temp_path}")

        try:
            # Execute it via asyncio subprocess
            self._process = await asyncio.create_subprocess_exec(
                sys.executable,
                temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await self._process.communicate()
            
            return {
                "name": self.name,
                "success": self._process.returncode == 0,
                "return_code": self._process.returncode,
                "stdout": stdout.decode("utf-8").strip(),
                "stderr": stderr.decode("utf-8").strip()
            }
        except Exception as e:
            logger.error(f"SubAgent [{self.name}] execution failed: {e}")
            return {
                "name": self.name,
                "success": False,
                "error": str(e)
            }
        finally:
            # Clean up the temp file
            if self._temp_file and os.path.exists(self._temp_file):
                try:
                    os.remove(self._temp_file)
                except Exception as e:
                    logger.debug(f"Failed to cleanup SubAgent temp file: {e}")

class SubAgentManager:
    """Manages spawning and tracking of SubAgents."""
    
    def __init__(self):
        self.active_agents: Dict[str, SubAgent] = {}

    async def spawn_agent(self, name: str, code: str) -> Dict[str, Any]:
        """Spawn a new sub-agent."""
        agent = SubAgent(name, code)
        self.active_agents[agent.task_id] = agent
        
        # In a real scenario we might wrap this in a task, but for the prompt
        # we'll execute it and return the result.
        result = await agent.execute()
        
        if agent.task_id in self.active_agents:
            del self.active_agents[agent.task_id]
            
        return result
