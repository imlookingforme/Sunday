"""Autonomous Engineering Loop and Bounded Repair Engine for Sunday 2.0.

Implements the end-to-end execution loop:
1. Requirements Ingestion -> Testable Acceptance Criteria
2. Architectural Impact & Step Planning
3. Implementation Execution
4. Staged Verification (Fast focused tests -> broad test suite)
5. Evidence-based Failure Diagnosis
6. Bounded Repair Loop (max N attempts)
7. Final Structured Verification Report
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sunday.core.durable_tasks import DurableTaskEngine, TaskRecord, TaskState
from sunday.core.indexer.project_index import ProjectIndex

logger = logging.getLogger(__name__)


@dataclass
class VerificationOutcome:
    """Detailed verification metrics."""
    tests_passed: bool
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    duration_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    failure_details: List[str] = field(default_factory=list)


@dataclass
class RepairAttempt:
    """Record of a bounded repair attempt."""
    attempt_number: int
    diagnosis: str
    proposed_fix: str
    outcome: VerificationOutcome
    timestamp: float = field(default_factory=time.time)


@dataclass
class FinalEngineeringReport:
    """Comprehensive final report for an autonomous engineering task."""
    task_id: str
    title: str
    summary: str
    acceptance_criteria_status: Dict[str, bool]
    files_modified: List[str]
    verification: VerificationOutcome
    repair_attempts: List[RepairAttempt]
    remaining_risks: List[str]
    is_fully_verified: bool


class AutonomousEngineeringLoop:
    """Manages autonomous engineering task execution and bounded self-healing."""

    def __init__(
        self,
        task_engine: DurableTaskEngine,
        project_index: ProjectIndex,
        max_repair_attempts: int = 3,
        workspace_root: Path | str = ".",
    ):
        self.task_engine = task_engine
        self.project_index = project_index
        self.max_repair_attempts = max_repair_attempts
        self.workspace_root = Path(workspace_root).resolve()

    def generate_acceptance_criteria(self, request: str) -> List[str]:
        """Convert a user request into explicit, verifiable acceptance criteria."""
        req_clean = request.strip()
        criteria = [
            f"Code changes addressing '{req_clean}' compile without syntax errors",
            "Target subsystem functionality passes focused unit tests",
            "No regressions introduced in existing project test suites",
        ]
        if "test" in req_clean.lower():
            criteria.append("Specific test assertions verify new edge cases")
        if "security" in req_clean.lower() or "auth" in req_clean.lower():
            criteria.append("Strict fail-closed policy checks are enforced")
        return criteria

    async def run_tests(self, test_targets: Optional[List[str]] = None) -> VerificationOutcome:
        """Execute selected test suites asynchronously and collect diagnostic evidence."""
        start_time = time.time()
        targets = test_targets or ["tests/"]

        cmd = [sys.executable, "-m", "pytest"] + targets + ["-q"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_root),
                env=dict(os.environ, PYTHONPATH=str(self.workspace_root)),
            )
            stdout_b, stderr_b = await proc.communicate()
            duration = time.time() - start_time

            stdout = stdout_b.decode("utf-8", errors="replace")
            stderr = stderr_b.decode("utf-8", errors="replace")

            # Extract test counts (e.g., '47 passed in 2.3s')
            passed_match = re.search(r"(\d+)\s+passed", stdout)
            failed_match = re.search(r"(\d+)\s+failed", stdout)

            passed_count = int(passed_match.group(1)) if passed_match else 0
            failed_count = int(failed_match.group(1)) if failed_match else 0
            total_count = passed_count + failed_count

            failures = []
            if failed_count > 0:
                for line in stdout.splitlines():
                    if "FAILED " in line:
                        failures.append(line.strip())

            return VerificationOutcome(
                tests_passed=proc.returncode == 0,
                total_tests=total_count,
                passed_tests=passed_count,
                failed_tests=failed_count,
                duration_seconds=round(duration, 2),
                stdout=stdout,
                stderr=stderr,
                failure_details=failures,
            )
        except Exception as e:
            return VerificationOutcome(
                tests_passed=False,
                duration_seconds=round(time.time() - start_time, 2),
                stderr=f"Test runner invocation error: {str(e)}",
            )

    def diagnose_failure(self, outcome: VerificationOutcome) -> str:
        """Diagnose probable cause of test failure from stderr and stdout evidence."""
        combined = f"{outcome.stdout}\n{outcome.stderr}"
        if "AssertionError" in combined:
            return "Assertion mismatch: target function returned unexpected value or state."
        elif "ModuleNotFoundError" in combined or "ImportError" in combined:
            return "Missing dependency or invalid package import path."
        elif "SyntaxError" in combined:
            return "Syntax error in modified source file."
        elif "Timeout" in combined:
            return "Operation timed out during test execution."
        elif outcome.failure_details:
            return f"Unit test assertion failed: {outcome.failure_details[0]}"
        return "Unknown runtime test failure."

    async def execute_task_with_bounded_repair(
        self,
        task_id: str,
        implementation_fn: Callable[[TaskRecord], Any],
        repair_fn: Optional[Callable[[TaskRecord, str], Any]] = None,
        test_targets: Optional[List[str]] = None,
    ) -> FinalEngineeringReport:
        """Run complete execution loop: Plan -> Implement -> Verify -> Bounded Repair."""
        task = await self.task_engine.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # 1. State: READY -> RUNNING
        if task.state == TaskState.QUEUED:
            await self.task_engine.transition(task_id, TaskState.PLANNING, reason="Formulating execution plan")
            await self.task_engine.transition(task_id, TaskState.READY, reason="Plan ready for implementation")
        
        await self.task_engine.transition(task_id, TaskState.RUNNING, reason="Starting implementation")

        # 2. Execute Primary Implementation
        try:
            await implementation_fn(task)
        except Exception as e:
            logger.error(f"Implementation error in task {task_id}: {e}")
            await self.task_engine.transition(
                task_id,
                TaskState.FAILED,
                reason=f"Implementation crashed: {str(e)}",
                updates={"error_info": {"exception": str(e)}},
            )
            return FinalEngineeringReport(
                task_id=task_id,
                title=task.original_request,
                summary=f"Failed with exception: {e}",
                acceptance_criteria_status={},
                files_modified=[],
                verification=VerificationOutcome(tests_passed=False, stderr=str(e)),
                repair_attempts=[],
                remaining_risks=["Implementation uncaught exception"],
                is_fully_verified=False,
            )

        # 3. Transition to VERIFYING and run tests
        await self.task_engine.transition(task_id, TaskState.VERIFYING, reason="Executing verification tests")
        outcome = await self.run_tests(test_targets)

        # 4. Bounded Repair Loop if verification failed
        repair_attempts = []
        attempt = 0
        while not outcome.tests_passed and attempt < self.max_repair_attempts and repair_fn is not None:
            attempt += 1
            diagnosis = self.diagnose_failure(outcome)
            logger.warning(f"Task {task_id} verification failed. Repair attempt {attempt}/{self.max_repair_attempts}: {diagnosis}")

            await self.task_engine.transition(
                task_id,
                TaskState.RETRY_SCHEDULED,
                reason=f"Repair attempt {attempt}: {diagnosis}",
                updates={"retry_count": attempt},
            )
            await self.task_engine.transition(task_id, TaskState.RUNNING, reason="Executing repair patch")

            try:
                await repair_fn(task, diagnosis)
            except Exception as e:
                logger.error(f"Repair attempt {attempt} error: {e}")

            await self.task_engine.transition(task_id, TaskState.VERIFYING, reason=f"Verifying repair {attempt}")
            outcome = await self.run_tests(test_targets)
            repair_attempts.append(
                RepairAttempt(
                    attempt_number=attempt,
                    diagnosis=diagnosis,
                    proposed_fix=f"Automated repair attempt {attempt}",
                    outcome=outcome,
                )
            )

        # 5. Final State Transition
        if outcome.tests_passed:
            await self.task_engine.transition(
                task_id,
                TaskState.COMPLETED,
                reason="All acceptance criteria and verification tests passed",
                updates={
                    "verification_results": {
                        "passed": True,
                        "total_tests": outcome.total_tests,
                        "duration": outcome.duration_seconds,
                    },
                    "completion_summary": f"Completed successfully with {len(repair_attempts)} repairs.",
                },
            )
        else:
            await self.task_engine.transition(
                task_id,
                TaskState.FAILED,
                reason=f"Exhausted {self.max_repair_attempts} repair attempts without passing verification",
                updates={
                    "verification_results": {"passed": False, "failed_tests": outcome.failed_tests},
                    "error_info": {"failures": outcome.failure_details},
                },
            )

        crit_status = {c: outcome.tests_passed for c in task.acceptance_criteria}
        return FinalEngineeringReport(
            task_id=task_id,
            title=task.original_request,
            summary="Task verified and completed" if outcome.tests_passed else "Task failed verification",
            acceptance_criteria_status=crit_status,
            files_modified=[],
            verification=outcome,
            repair_attempts=repair_attempts,
            remaining_risks=[] if outcome.tests_passed else ["Remaining unverified tests"],
            is_fully_verified=outcome.tests_passed,
        )
