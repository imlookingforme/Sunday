"""Specialist operators module for least-privilege tool slices."""

from .base import SpecialistOperator, ConversationMode
from .conversation import ConversationOperator
from .research import ResearchOperator
from .automation import AutomationOperator
from .device_control import DeviceControlOperator
from .alerting import AlertingOperator
from .security import SecurityOperator

__all__ = [
    "SpecialistOperator",
    "ConversationMode",
    "ConversationOperator",
    "ResearchOperator",
    "AutomationOperator",
    "DeviceControlOperator",
    "AlertingOperator",
    "SecurityOperator",
]
