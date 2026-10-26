"""Dependency-Aware Multi-Agent DAG Scheduler for Sunday 2.0.

Provides:
- Directed Acyclic Graph (DAG) task scheduling
- Parallel execution of independent subtasks
- Cyclic dependency detection
- Role-based specialization (Architect, Implementer, Test Engineer, Verifier)
- Shared task reporting and non-destructive integration
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    ARCHITECT = "architect"
    IMPLEMENTER = "implementer"
    TEST_ENGINEER = "test_engineer"
    CODE_REVIEWER = "code_reviewer"
    SECURITY_REVIEWER = "security_reviewer"
    VERIFIER = "verifier"


@dataclass
class SubTaskNode:
    """Node in the multi-agent dependency execution graph."""
    node_id: str
    title: str
    role: AgentRole
    dependencies: Set[str] = field(default_factory=set)
    action: Optional[Callable[[], Any]] = None
    output: Any = None
    completed: bool = False
    failed: bool = False
    error: Optional[str] = None


class DAGScheduler:
    """Coordinates execution of multi-agent subtasks respecting dependencies."""

    def __init__(self):
        self.nodes: Dict[str, SubTaskNode] = {}

    def add_node(
        self,
        node_id: str,
        title: str,
        role: AgentRole,
        dependencies: Optional[Set[str]] = None,
        action: Optional[Callable[[], Any]] = None,
    ) -> SubTaskNode:
        """Add a subtask node to the execution graph."""
        node = SubTaskNode(
            node_id=node_id,
            title=title,
            role=role,
            dependencies=dependencies or set(),
            action=action,
        )
        self.nodes[node_id] = node
        return node

    def detect_cycles(self) -> bool:
        """Detect circular dependencies via topological DFS."""
        visited = set()
        rec_stack = set()

        def _dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for dep in self.nodes.get(node_id, SubTaskNode("", "", AgentRole.IMPLEMENTER)).dependencies:
                if dep not in visited:
                    if _dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.remove(node_id)
            return False

        for nid in self.nodes:
            if nid not in visited:
                if _dfs(nid):
                    return True
        return False

    async def execute_dag(self, max_concurrency: int = 4) -> Dict[str, Any]:
        """Execute independent nodes concurrently as dependencies resolve."""
        if self.detect_cycles():
            raise ValueError("Cyclic dependency detected in multi-agent DAG")

        completed_nodes = set()
        active_tasks: Dict[str, asyncio.Task] = {}
        sem = asyncio.Semaphore(max_concurrency)

        async def _run_node(node: SubTaskNode):
            async with sem:
                try:
                    logger.info(f"DAG Node [{node.node_id}] starting (Role: {node.role.value})")
                    if node.action:
                        if asyncio.iscoroutinefunction(node.action):
                            node.output = await node.action()
                        else:
                            node.output = await asyncio.to_thread(node.action)
                    node.completed = True
                    completed_nodes.add(node.node_id)
                    logger.info(f"DAG Node [{node.node_id}] completed successfully.")
                except Exception as e:
                    node.failed = True
                    node.error = str(e)
                    logger.error(f"DAG Node [{node.node_id}] failed: {e}")

        while len(completed_nodes) < len(self.nodes):
            ready_to_launch = []
            for nid, node in self.nodes.items():
                if not node.completed and not node.failed and nid not in active_tasks:
                    if node.dependencies.issubset(completed_nodes):
                        ready_to_launch.append(node)

            if not ready_to_launch and not active_tasks:
                # Deadlock or unresolvable failure
                break

            for node in ready_to_launch:
                active_tasks[node.node_id] = asyncio.create_task(_run_node(node))

            done, pending = await asyncio.wait(
                active_tasks.values(),
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Clean finished tasks
            for nid in list(active_tasks.keys()):
                if active_tasks[nid] in done:
                    del active_tasks[nid]

        return {
            "total_nodes": len(self.nodes),
            "completed_nodes": len(completed_nodes),
            "failed_nodes": sum(1 for n in self.nodes.values() if n.failed),
            "results": {nid: {"completed": n.completed, "failed": n.failed, "error": n.error} for nid, n in self.nodes.items()},
        }
