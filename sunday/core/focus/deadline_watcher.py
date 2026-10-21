"""Markdown Deadline Watcher & Contextual Idle Pass-Time Detector for Sunday Senpai.

Reads deadlines from user `todo.md` files, monitors idle time and distraction windows,
and triggers random, encouraging reminders from Senpai.
"""

import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class TaskDeadline:
    """Represents a single parsed deadline item."""

    def __init__(self, title: str, due_date: Optional[str] = None, priority: str = "normal", raw: str = ""):
        self.title = title
        self.due_date = due_date
        self.priority = priority
        self.raw = raw
        self.parsed_due: Optional[float] = None
        self._parse_due_timestamp()

    def _parse_due_timestamp(self):
        if not self.due_date:
            return
        # Support common formats: YYYY-MM-DD HH:MM or YYYY-MM-DD
        formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y"]
        for fmt in formats:
            try:
                dt = datetime.strptime(self.due_date.strip(), fmt)
                self.parsed_due = dt.timestamp()
                return
            except ValueError:
                continue

    @property
    def hours_remaining(self) -> Optional[float]:
        if self.parsed_due is None:
            return None
        return round((self.parsed_due - time.time()) / 3600.0, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "due_date": self.due_date,
            "priority": self.priority,
            "hours_remaining": self.hours_remaining
        }


class DeadlineWatcher:
    """Watches local todo.md, tracks deadlines, and provides context-aware reminders."""

    def __init__(
        self,
        todo_file: Optional[Path] = None,
        idle_threshold_seconds: float = 300.0,  # 5 minutes idle
        min_reminder_interval: float = 1200.0  # At least 20 minutes between random reminders
    ):
        self.todo_file = todo_file or Path("todo.md")
        self.idle_threshold_seconds = idle_threshold_seconds
        self.min_reminder_interval = min_reminder_interval
        self.last_reminder_time: float = 0.0

    def parse_todo_file(self) -> List[TaskDeadline]:
        """Parse markdown checkboxes and deadlines from todo.md."""
        if not self.todo_file.exists():
            return []

        deadlines = []
        try:
            with open(self.todo_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                line_str = line.strip()
                # Match uncompleted markdown task: - [ ] Task title (due: YYYY-MM-DD ...)
                match = re.match(r"^-\s*\[\s*\]\s+(.+)$", line_str)
                if match:
                    content = match.group(1)
                    # Extract due date if present: (due: ...) or due: ...
                    due_match = re.search(r"\(?due:\s*([^\)#\)]+)\)?", content, re.IGNORECASE)
                    due_date = due_match.group(1).strip() if due_match else None

                    # Extract priority if present: #high, #urgent
                    priority = "normal"
                    if "#urgent" in content.lower() or "#high" in content.lower():
                        priority = "high"

                    clean_title = re.sub(r"\(?due:[^\)]+\)?", "", content, flags=re.IGNORECASE)
                    clean_title = re.sub(r"#[a-zA-Z0-9_-]+", "", clean_title).strip()

                    deadlines.append(TaskDeadline(
                        title=clean_title,
                        due_date=due_date,
                        priority=priority,
                        raw=line_str
                    ))
        except Exception as e:
            logger.error(f"Error reading todo file {self.todo_file}: {e}")

        # Sort deadlines: items with due dates first, ordered by closest deadline
        deadlines.sort(key=lambda d: d.parsed_due if d.parsed_due is not None else float("inf"))
        return deadlines

    def get_user_idle_seconds(self) -> float:
        """Measure keyboard/mouse idle time via Windows API."""
        if not WIN32_AVAILABLE:
            return 0.0
        try:
            last_input_ms = win32api.GetLastInputInfo()
            current_tick = win32api.GetTickCount()
            idle_seconds = max(0.0, (current_tick - last_input_ms) / 1000.0)
            return idle_seconds
        except Exception as e:
            logger.debug(f"Could not fetch win32 idle info: {e}")
            return 0.0

    def check_for_pass_time_reminder(self, current_window_title: str = "") -> Optional[Dict[str, Any]]:
        """Check if user is passing time and generate a timely Senpai nudge."""
        now = time.time()
        if (now - self.last_reminder_time) < self.min_reminder_interval:
            return None

        idle_seconds = self.get_user_idle_seconds()
        is_idle = idle_seconds >= self.idle_threshold_seconds

        # Check if passing time in empty desktop / neutral app
        is_passing_time = is_idle or any(w in current_window_title.lower() for w in ["reddit", "youtube", "twitter", "feedly", "new tab"])

        if not is_passing_time:
            return None

        deadlines = self.parse_todo_file()
        if not deadlines:
            return None

        # Pick the most urgent deadline
        urgent = deadlines[0]
        self.last_reminder_time = now

        hours = urgent.hours_remaining
        time_hint = f"in {hours} hours" if hours and hours > 0 else "very soon"

        message = (
            f"Hey, while you're taking a breather, remember '{urgent.title}' is due {time_hint}! "
            f"Let's plant a quick 25-minute focus tree and knock out a piece of it together."
        )

        return {
            "trigger": "idle_pass_time" if is_idle else "window_distraction",
            "idle_seconds": idle_seconds,
            "task": urgent.to_dict(),
            "senpai_message": message
        }
