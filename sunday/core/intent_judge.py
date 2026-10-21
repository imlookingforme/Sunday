"""Intent judge for deterministic routing (LakshyaBadjatya/Friday pattern)."""

from typing import Optional
from .operators.base import ConversationMode


class IntentJudge:
    """Deterministic intent classification before LLM call.
    
    Routes requests to appropriate specialist operators based on
    heuristic classification without LLM dependency.
    """
    
    def __init__(self):
        """Initialize intent judge with keyword patterns."""
        self._research_keywords = [
            "search", "find", "look up", "research", "what is", "who is",
            "when did", "where is", "how does", "explain", "tell me about",
            "wikipedia", "google", "information", "learn about"
        ]
        
        self._automation_keywords = [
            "run", "execute", "start", "stop", "launch", "open", "close",
            "schedule", "automate", "script", "command", "shell", "terminal",
            "batch", "macro", "workflow", "pipeline"
        ]
        
        self._device_control_keywords = [
            "volume", "mute", "play", "pause", "next", "previous", "skip",
            "window", "tab", "screen", "display", "monitor", "brightness",
            "turn on", "turn off", "switch", "device", "smart home", "light"
        ]
        
        self._alert_keywords = [
            "remind", "notify", "alert", "nudge", "check", "monitor",
            "briefing", "summary", "digest", "status", "health", "inbox",
            "calendar", "schedule", "upcoming", "deadline"
        ]
        
        self._security_keywords = [
            "security", "lockdown", "block", "unblock", "audit", "verify",
            "scan", "threat", "attack", "breach", "emergency", "safety",
            "protect", "secure", "permissions", "access"
        ]
    
    def classify(self, input: str, context: Optional[dict] = None) -> ConversationMode:
        """Classify conversation mode (deterministic, no LLM).
        
        Args:
            input: User input text
            context: Optional context for classification
            
        Returns:
            ConversationMode for routing
        """
        input_lower = input.lower()
        
        # Check security concerns first (highest priority)
        if self._is_security_concern(input_lower):
            return ConversationMode.SECURITY_LOCKDOWN
        
        # Check automation commands
        if self._is_automation_command(input_lower):
            return ConversationMode.AUTOMATION
        
        # Check device control
        if self._is_device_control(input_lower):
            return ConversationMode.DEVICE_CONTROL
        
        # Check alerting
        if self._is_alert(input_lower):
            return ConversationMode.ALERTING
        
        # Check research query
        if self._is_research_query(input_lower):
            return ConversationMode.RESEARCH
        
        # Default to conversation
        return ConversationMode.CONVERSATION
    
    def _is_research_query(self, input: str) -> bool:
        """Check if input is a research query."""
        return any(kw in input for kw in self._research_keywords)
    
    def _is_automation_command(self, input: str) -> bool:
        """Check if input is an automation command."""
        return any(kw in input for kw in self._automation_keywords)
    
    def _is_device_control(self, input: str) -> bool:
        """Check if input is device control."""
        return any(kw in input for kw in self._device_control_keywords)
    
    def _is_alert(self, input: str) -> bool:
        """Check if input is alert-related."""
        return any(kw in input for kw in self._alert_keywords)
    
    def _is_security_concern(self, input: str) -> bool:
        """Check if input is a security concern."""
        return any(kw in input for kw in self._security_keywords)
    
    def get_confidence(self, input: str, mode: ConversationMode) -> float:
        """Get confidence score for classification.
        
        Args:
            input: User input
            mode: Classified mode
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        input_lower = input.lower()
        
        if mode == ConversationMode.RESEARCH:
            matches = sum(1 for kw in self._research_keywords if kw in input_lower)
            return min(1.0, matches / 3.0)
        
        elif mode == ConversationMode.AUTOMATION:
            matches = sum(1 for kw in self._automation_keywords if kw in input_lower)
            return min(1.0, matches / 2.0)
        
        elif mode == ConversationMode.DEVICE_CONTROL:
            matches = sum(1 for kw in self._device_control_keywords if kw in input_lower)
            return min(1.0, matches / 2.0)
        
        elif mode == ConversationMode.ALERTING:
            matches = sum(1 for kw in self._alert_keywords if kw in input_lower)
            return min(1.0, matches / 2.0)
        
        elif mode == ConversationMode.SECURITY_LOCKDOWN:
            matches = sum(1 for kw in self._security_keywords if kw in input_lower)
            return min(1.0, matches / 1.0)
        
        else:  # CONVERSATION
            # Low confidence for default
            return 0.3
    
    def explain_classification(self, input: str, mode: ConversationMode) -> str:
        """Explain why a classification was made.
        
        Args:
            input: User input
            mode: Classified mode
            
        Returns:
            Explanation string
        """
        input_lower = input.lower()
        
        if mode == ConversationMode.RESEARCH:
            found = [kw for kw in self._research_keywords if kw in input_lower]
            return f"Classified as RESEARCH because it contains: {', '.join(found)}"
        
        elif mode == ConversationMode.AUTOMATION:
            found = [kw for kw in self._automation_keywords if kw in input_lower]
            return f"Classified as AUTOMATION because it contains: {', '.join(found)}"
        
        elif mode == ConversationMode.DEVICE_CONTROL:
            found = [kw for kw in self._device_control_keywords if kw in input_lower]
            return f"Classified as DEVICE_CONTROL because it contains: {', '.join(found)}"
        
        elif mode == ConversationMode.ALERTING:
            found = [kw for kw in self._alert_keywords if kw in input_lower]
            return f"Classified as ALERTING because it contains: {', '.join(found)}"
        
        elif mode == ConversationMode.SECURITY_LOCKDOWN:
            found = [kw for kw in self._security_keywords if kw in input_lower]
            return f"Classified as SECURITY_LOCKDOWN because it contains: {', '.join(found)}"
        
        else:
            return "Classified as CONVERSATION (default - no specific keywords detected)"
