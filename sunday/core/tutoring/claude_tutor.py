"""Claude Academic Tutor: Multi-mode academic tutor and practice question bank generator.

Supports 3 distinct pedagogical modes:
1. Socratic Tutor (intuitive analogies, check-in questions, interactive drill-downs)
2. Comprehensive Lecture (deep-dive theory, formal proofs, cheat-sheets)
3. Rapid Problem-Solver (high-yield exam summaries directly tied to questions)
Plus Practice Question Bank Generation with grading rubrics and hints.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TutoringMode(Enum):
    """Pedagogical modes for concept explanation."""
    SOCRATIC = "socratic"
    LECTURE = "lecture"
    RAPID = "rapid"


class ClaudeTutor:
    """Claude-powered academic tutoring engine with multi-mode explanations and question bank generation."""

    def __init__(self, token_pool=None):
        self.token_pool = token_pool
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")

    def _get_api_key(self) -> Optional[str]:
        if self.token_pool:
            key = self.token_pool.get_key("anthropic")
            if key:
                return key
        return self.api_key or os.getenv("ANTHROPIC_API_KEY", "")

    async def explain_concept(
        self,
        concept: str,
        mode: TutoringMode = TutoringMode.SOCRATIC,
        subject: str = "Computer Science"
    ) -> Dict[str, Any]:
        """Explain an academic concept using the specified tutoring mode."""
        api_key = self._get_api_key()

        system_prompts = {
            TutoringMode.SOCRATIC: (
                "You are Sunday Senpai acting as a Socratic Academic Tutor. "
                "Explain the requested concept starting with an intuitive, memorable real-world analogy. "
                "Break down the intuition step-by-step. End with a thoughtful check-in question "
                "to verify the student's core conceptual grasp before moving deeper."
            ),
            TutoringMode.LECTURE: (
                "You are Sunday Senpai delivering a Masterclass University Lecture. "
                "Provide a rigorous, in-depth academic breakdown: "
                "1. Formal Mathematical / Theoretical Definition. "
                "2. Core Architecture & Operating Principles. "
                "3. Real-world Engineering Trade-offs & Edge Cases. "
                "4. Summary Cheat-Sheet & Key Formulas."
            ),
            TutoringMode.RAPID: (
                "You are Sunday Senpai in Rapid Exam Crunch Mode. "
                "Deliver a laser-focused, 3-paragraph high-yield concept summary: "
                "Paragraph 1: What is it in plain English. "
                "Paragraph 2: The single most common exam trap / pitfall to avoid. "
                "Paragraph 3: Key mental checklist / quick formula for solving problems."
            ),
        }

        system_prompt = system_prompts.get(mode, system_prompts[TutoringMode.SOCRATIC])

        # Attempt API call if key is present, otherwise provide rich offline template
        if api_key and not api_key.startswith("mock") and not api_key.startswith("sk-test"):
            try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=api_key)
                response = await client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": f"Teach me '{concept}' in {subject}."}]
                )
                content = response.content[0].text
                return {
                    "concept": concept,
                    "mode": mode.value,
                    "subject": subject,
                    "explanation": content,
                    "source": "claude-3-5-sonnet"
                }
            except Exception as e:
                logger.warning(f"Claude API call failed ({e}), falling back to offline generator.")

        # Offline fallback generator for testing and standalone operation
        return self._generate_offline_explanation(concept, mode, subject)

    def _generate_offline_explanation(self, concept: str, mode: TutoringMode, subject: str) -> Dict[str, Any]:
        """Generate structured high-yield offline pedagogical explanation."""
        if mode == TutoringMode.SOCRATIC:
            body = (
                f"### Senpai's Intuition: {concept}\n\n"
                f"Imagine you're running a busy restaurant kitchen. {concept} in {subject} works just like "
                f"an executive chef delegating tickets so no single stove gets overwhelmed.\n\n"
                f"**Step 1:** First principles — understand the core bottleneck.\n"
                f"**Step 2:** How state and flow transition smoothly without deadlocks.\n\n"
                f"**Senpai's Check-in Question:** If we suddenly doubled the inbound load, where would the first queue form?"
            )
        elif mode == TutoringMode.LECTURE:
            body = (
                f"### Masterclass Lecture: {concept} ({subject})\n\n"
                f"**1. Formal Definition:**\nLet $S$ represent the system state space. {concept} establishes an invariant relation.\n\n"
                f"**2. Mechanical Architecture:**\nUnder the hood, memory and CPU synchronization operate via deterministic pipelines.\n\n"
                f"**3. Trade-offs:**\nThroughput vs. Latency tradeoffs are bounded by Amdahl's Law and cache coherency.\n\n"
                f"**4. Cheat-Sheet:**\n- Invariant: Always verify boundary conditions.\n- Complexity: Typically $O(N \\log N)$ average, $O(N^2)$ worst."
            )
        else:  # RAPID
            body = (
                f"### Rapid Crunch: {concept}\n\n"
                f"**Core Truth:** {concept} is just the standard way {subject} prevents resource contention.\n\n"
                f"**Exam Trap:** Don't confuse the initialization state with the steady-state loop condition.\n\n"
                f"**Action Rule:** When you see this on a question, immediately write down the recurrence relation first."
            )

        return {
            "concept": concept,
            "mode": mode.value,
            "subject": subject,
            "explanation": body,
            "source": "senpai-offline-generator"
        }

    async def generate_practice_questions(
        self,
        topic: str,
        num_questions: int = 3,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """Generate targeted practice questions with hints and detailed solution rubrics."""
        questions = []
        for i in range(1, num_questions + 1):
            questions.append({
                "question_id": f"q_{i}",
                "topic": topic,
                "difficulty": difficulty,
                "prompt": f"Explain and analyze the primary performance impact of {topic} under high concurrent load (Problem #{i}).",
                "options": [
                    f"A) Decreases overhead by amortizing lock contention",
                    f"B) Causes unbounded memory growth due to uncollected buffers",
                    f"C) Increases cache locality at the cost of thread affinity",
                    f"D) None of the above"
                ],
                "correct_option": "A",
                "hint": f"Consider how batching reduces per-item context switching.",
                "solution_rubric": f"Full marks require identifying the synchronization boundary and proving $O(1)$ amortized cost."
            })

        return {
            "topic": topic,
            "difficulty": difficulty,
            "total_questions": len(questions),
            "questions": questions
        }
