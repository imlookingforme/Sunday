"""Dashboard API module for Sunday."""

from .main import app
from .sse import sse_event_generator

__all__ = ["app", "sse_event_generator"]
