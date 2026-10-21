"""Socratic Academic Tutor and Senpai Focus Manager for Sunday AI."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SocraticTutor:
    """Academic tutor implementing the Socratic method and Senpai persona guidance."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (Path("sunday") / "data" / "study_progress.db")
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database for tracking study metrics."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS study_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    score REAL NOT NULL,
                    notes TEXT,
                    timestamp REAL NOT NULL
                )
                """
            )
            conn.commit()

    def generate_prompt(self, topic: str, style: str = "socratic") -> str:
        """Generate structured pedagogical prompt for LLMs."""
        if style == "socratic":
            return (
                f"You are Sunday Senpai, an encouraging but rigorous academic mentor. "
                f"The student is studying '{topic}'. Do not give raw solutions immediately. "
                "Instead, ask targeted, thought-provoking guiding questions to lead them to the answer."
            )
        elif style == "quiz":
            return (
                f"You are evaluating the student's mastery in '{topic}'. "
                "Generate a short 3-question diagnostic quiz with multiple choices or short answers."
            )
        else:
            return (
                f"Explain the fundamentals of '{topic}' with crystal clear real-world analogies, "
                "breaking complex concepts into first principles."
            )

    def create_study_plan(self, subject: str, duration_hours: int = 2) -> Dict[str, Any]:
        """Create structured pomodoro-style study session plan."""
        blocks = []
        num_sessions = max(1, duration_hours * 2)  # 25 min blocks
        for i in range(1, num_sessions + 1):
            blocks.append({
                "block": i,
                "focus_minutes": 25,
                "break_minutes": 5 if i < num_sessions else 15,
                "objective": f"Sprint {i}: Deep dive on {subject} subtopic {i}"
            })

        return {
            "subject": subject,
            "total_hours": duration_hours,
            "total_blocks": len(blocks),
            "schedule": blocks,
            "senpai_advice": "Hydrate, close distracting browser tabs, and let our focus tree grow!"
        }

    async def track_progress(self, subject: str, duration_minutes: int, score: float, notes: str = "") -> None:
        """Record study session performance."""
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO study_logs (subject, duration_minutes, score, notes, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (subject, duration_minutes, score, notes, time.time()),
                )
                conn.commit()

    async def get_progress_report(self, subject: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate study statistics and progress."""
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if subject:
                    cursor.execute(
                        "SELECT COUNT(*), SUM(duration_minutes), AVG(score) FROM study_logs WHERE subject = ?",
                        (subject,),
                    )
                else:
                    cursor.execute("SELECT COUNT(*), SUM(duration_minutes), AVG(score) FROM study_logs")
                row = cursor.fetchone()

            total_sessions = row[0] or 0
            total_minutes = row[1] or 0
            avg_score = round(row[2] or 0.0, 2)

            return {
                "subject": subject or "All Subjects",
                "total_sessions": total_sessions,
                "total_study_minutes": total_minutes,
                "average_mastery_score": avg_score,
            }

    def get_encouragement(self, performance_score: float) -> str:
        """Provide motivational feedback based on performance score."""
        if performance_score >= 0.85:
            return "Sugoi! Outstanding work! You've grasped this concept deeply."
        elif performance_score >= 0.60:
            return "Good progress! A little more practice on the edges and you'll master this."
        else:
            return "Don't sweat it — mistakes are just learning data. Let's tackle it from another angle!"
