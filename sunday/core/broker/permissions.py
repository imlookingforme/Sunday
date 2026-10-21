"""Permission checker for tool access control."""

from typing import Set, Dict
from enum import Enum


class ToolRisk(Enum):
    """Risk levels for tools."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PermissionChecker:
    """Check if an actor is allowed to use a tool."""
    
    def __init__(self, permission_rules: Dict[str, Dict[str, Set[str]]]):
        """
        Initialize permission checker.
        
        Args:
            permission_rules: Dict mapping actors to their allowed tools per risk level
                {
                    "user": {"low": {"*"}, "medium": {"tool1", "tool2"}, ...},
                    "automation": {"low": {"*"}, "medium": {"*"}, ...}
                }
        """
        self.permission_rules = permission_rules
    
    def is_allowed(self, tool: str, actor: str, risk: ToolRisk) -> bool:
        """Check if actor is allowed to use tool at given risk level."""
        actor_rules = self.permission_rules.get(actor, {})
        risk_rules = actor_rules.get(risk.value, set())
        
        # Wildcard means all tools allowed at this risk level
        if "*" in risk_rules:
            return True
        
        return tool in risk_rules
    
    def get_allowed_tools(self, actor: str, risk: ToolRisk) -> Set[str]:
        """Get all tools allowed for actor at given risk level."""
        actor_rules = self.permission_rules.get(actor, {})
        risk_rules = actor_rules.get(risk.value, set())
        return risk_rules.copy()


def default_permission_rules() -> Dict[str, Dict[str, Set[str]]]:
    """Default permission rules for Sunday."""
    return {
        "user": {
            "low": {"*"},  # All low-risk tools
            "medium": {
                "reschedule_task",
                "organize_inbox",
                "write_file",
                "set_clipboard",
                "open_application",
                "switch_window",
                "set_volume",
                "browser_navigate",
                "browser_download",
                "create_project",
                "run_tests",
                "create_artifact",
                "run_artifact",
                "schedule_task",
                "set_protocol",
                "set_recurring_prompt",
                "monitor_inbox",
            },
            "high": {
                "send_email",
                "create_event",
                "send_slack_message",
                "send_teams_message",
                "send_discord_message",
                "notion_create_page",
                "google_docs_write",
                "close_application",
                "type_text",
                "click_at",
                "browser_click",
                "browser_type",
                "browser_fill_form",
                "git_commit",
                "delegate_coding_task",
                "docker_run",
                "office_automation",
            },
            "critical": {
                "run_shell",
            },
        },
        "automation": {
            "low": {"*"},
            "medium": {"*"},
            "high": {
                "close_application",
                "type_text",
                "click_at",
                "browser_click",
                "browser_type",
                "browser_fill_form",
                "git_commit",
                "docker_run",
            },
            "critical": {
                "run_shell",
                "run_shell_sandboxed",
            },
        },
        "conversation": {
            "low": {"*"},
            "medium": set(),
            "high": set(),
            "critical": set(),
        },
        "research": {
            "low": {"*"},
            "medium": {"scrape_page"},
            "high": set(),
            "critical": set(),
        },
    }
