"""Focus Sentry: Window & process inspection, distraction classifier, and gradual escalation protocol for Sunday Senpai."""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class EscalationStage(Enum):
    """Gradual escalation stages for distractions."""
    NONE = 0
    STAGE_1_VOICE_NUDGE = 1      # Soft verbal sigh / gentle question
    STAGE_2_DESKTOP_WARNING = 2  # Minimal toast / visual warning (tree is in danger)
    STAGE_3_ENFORCEMENT = 3      # Auto-minimize window, wilt / penalize tree


class FocusSentry:
    """Monitors desktop activity, classifies distraction vs academic focus,

    and enforces gradual escalation during study sessions.
    """

    DEFAULT_DISTRACTION_KEYWORDS = [
        "youtube", "reddit", "twitter", "x.com", "instagram", "twitch", "tiktok",
        "netflix", "steam", "discord", "facebook", "hulu", "disney+", "roblox",
        "valorant", "league of legends", "fortnite", "genshin"
    ]

    DEFAULT_ACADEMIC_KEYWORDS = [
        "visual studio code", "vscode", "pycharm", "cursor", "antigravity",
        "arxiv", "scholar.google", "pdf", "notion", "obsidian", "canvas",
        "blackboard", "overleaf", "github", "leetcode", "docs.python.org",
        "stackoverflow", "jupyter", "terminal", "powershell"
    ]

    def __init__(
        self,
        distraction_keywords: Optional[List[str]] = None,
        academic_keywords: Optional[List[str]] = None,
        stage_1_grace_period: float = 15.0,  # seconds before stage 1 triggers
        stage_2_grace_period: float = 30.0,  # seconds before stage 2 triggers
        stage_3_grace_period: float = 45.0,  # seconds before window is minimized & tree wilts
    ):
        self.distraction_keywords = [k.lower() for k in (distraction_keywords or self.DEFAULT_DISTRACTION_KEYWORDS)]
        self.academic_keywords = [k.lower() for k in (academic_keywords or self.DEFAULT_ACADEMIC_KEYWORDS)]
        self.stage_1_grace_period = stage_1_grace_period
        self.stage_2_grace_period = stage_2_grace_period
        self.stage_3_grace_period = stage_3_grace_period

        self.current_distraction_start: Optional[float] = None
        self.current_distraction_title: Optional[str] = None
        self.last_escalation_stage: EscalationStage = EscalationStage.NONE
        self.interventions_count: int = 0
        self.is_active: bool = True

    def classify_window(self, title: str, process_name: str = "") -> Tuple[bool, str]:
        """Classify a window as distracting, academic, or neutral.

        Returns:
            Tuple of (is_distraction, category)
        """
        if not title:
            return False, "neutral"

        combined = f"{title.lower()} {process_name.lower()}"

        # First check if explicitly academic
        for academic in self.academic_keywords:
            if academic in combined:
                return False, "academic"

        # Check for distraction
        for distraction in self.distraction_keywords:
            if distraction in combined:
                return True, distraction

        return False, "neutral"

    def update(self, active_window: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Process current active window and determine escalation stage.

        Returns status dictionary with escalation action needed.
        """
        if not self.is_active or not active_window:
            self._reset_distraction()
            return {"stage": EscalationStage.NONE, "action": "none"}

        title = active_window.get("title", "")
        hwnd = active_window.get("hwnd")
        is_distraction, keyword = self.classify_window(title)

        now = time.time()

        if not is_distraction:
            self._reset_distraction()
            return {
                "stage": EscalationStage.NONE,
                "action": "none",
                "status": "focused",
                "title": title
            }

        # User is in a distracting window
        if self.current_distraction_start is None or self.current_distraction_title != title:
            self.current_distraction_start = now
            self.current_distraction_title = title
            self.last_escalation_stage = EscalationStage.NONE

        elapsed = now - self.current_distraction_start

        # Determine escalation stage
        if elapsed >= self.stage_3_grace_period:
            stage = EscalationStage.STAGE_3_ENFORCEMENT
            action = "minimize_and_wilt"
            message = f"Senpai enforcement: {title} minimized. Tree is wilting!"
        elif elapsed >= self.stage_2_grace_period:
            stage = EscalationStage.STAGE_2_DESKTOP_WARNING
            action = "toast_warning"
            message = f"Warning: Your focus tree will wilt in {int(self.stage_3_grace_period - elapsed)}s! Return to your study task."
        elif elapsed >= self.stage_1_grace_period:
            stage = EscalationStage.STAGE_1_VOICE_NUDGE
            action = "voice_nudge"
            message = f"Hey... isn't that {keyword}? We have a tree growing right now. Let's stay on task."
        else:
            stage = EscalationStage.NONE
            action = "grace_period"
            message = f"Distraction detected ({keyword}), grace period active."

        escalation_triggered = stage != self.last_escalation_stage and stage != EscalationStage.NONE
        if escalation_triggered:
            self.last_escalation_stage = stage
            if stage == EscalationStage.STAGE_3_ENFORCEMENT:
                self.interventions_count += 1

        return {
            "stage": stage,
            "action": action,
            "new_escalation": escalation_triggered,
            "elapsed_distraction": elapsed,
            "keyword": keyword,
            "title": title,
            "hwnd": hwnd,
            "message": message
        }

    def _reset_distraction(self):
        self.current_distraction_start = None
        self.current_distraction_title = None
        self.last_escalation_stage = EscalationStage.NONE

    def get_stats(self) -> Dict[str, Any]:
        return {
            "is_active": self.is_active,
            "interventions_count": self.interventions_count,
            "in_distraction": self.current_distraction_start is not None,
            "current_stage": self.last_escalation_stage.name
        }
