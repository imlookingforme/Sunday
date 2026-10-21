"""Gatekeeper Agent: Security broker gateway, approval management, and multi-account token rotator."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from .base_agent import SwarmAgent
from .bus import SwarmBus
from .events import SwarmEvent, EventTopic, EventPriority, ApprovalRequestEvent
from sunday.core.broker.token_pool import TokenPool

logger = logging.getLogger(__name__)


class Gatekeeper(SwarmAgent):
    """Security broker gateway and credential pool manager in the Sunday Swarm."""

    def __init__(self, bus: SwarmBus):
        super().__init__(
            name="gatekeeper",
            role="Security Broker & Token/Session Rotator",
            bus=bus,
            system_prompt="You are Sunday's Gatekeeper. You gate dangerous actions, manage approval tickets, and rotate API keys and session tokens upon rate limits.",
            allowed_tools=["audit_log", "vault_access", "permission_check"],
            memory_namespace="swarm:gatekeeper",
        )
        self.pending_approvals: Dict[str, ApprovalRequestEvent] = {}
        # Credential pool backed by TokenPool for automatic rotation upon 429 rate limits
        self.token_pool = TokenPool()
        self.token_pool.add_keys('browser_profiles', ['profile_default', 'profile_secondary'])

    async def start(self) -> None:
        await super().start()
        self.bus.subscribe(EventTopic.TOKEN_EXHAUSTED.value, self._handle_token_exhausted)
        self.bus.subscribe(EventTopic.APPROVAL_RESPONSE.value, self._handle_approval_response)
        logger.info("Gatekeeper initialized with token rotation and approval gates.")

    def add_keys_to_pool(self, provider: str, keys: List[str]) -> None:
        """Register multiple API keys or tokens for a provider."""
        self.token_pool.add_keys(provider, keys)
        logger.info(f"Added {len(keys)} credentials to pool for provider [{provider}].")

    def get_current_key(self, provider: str) -> Optional[str]:
        """Fetch the currently active key for a provider."""
        return self.token_pool.get_key(provider)

    def rotate_key(self, provider: str) -> Optional[str]:
        """Rotate to the next available credential in the pool."""
        return self.token_pool.rotate(provider)

    async def _handle_token_exhausted(self, event: SwarmEvent) -> None:
        """Handle 429 / quota exhaustion notification and auto-swap credentials."""
        provider = event.payload.get("provider", "openai")
        new_key = self.token_pool.mark_exhausted(provider)
        await self.publish_nudge(
            task_id=event.payload.get("task_id", "auth_rotation"),
            status="completed",
            summary=f"Rate limit detected for {provider}. Successfully rotated to secondary account in pool.",
            details={"provider": provider, "has_alternate": bool(new_key)},
        )

    async def request_approval(self, tool_name: str, tool_args: Dict[str, Any], risk_level: str = "HIGH") -> ApprovalRequestEvent:
        """Create and broadcast an approval ticket for high-risk operations."""
        ticket = ApprovalRequestEvent(
            source_agent=self.name,
            tool_name=tool_name,
            tool_args=tool_args,
            risk_level=risk_level,
            rationale=f"Tool '{tool_name}' requires user confirmation before execution.",
        )
        self.pending_approvals[ticket.ticket_id] = ticket
        await self.bus.publish(ticket)
        return ticket

    async def _handle_approval_response(self, event: SwarmEvent) -> None:
        ticket_id = event.payload.get("ticket_id")
        approved = event.payload.get("approved", False)
        if ticket_id in self.pending_approvals:
            ticket = self.pending_approvals.pop(ticket_id)
            logger.info(f"Ticket {ticket_id} ({ticket.tool_name}) resolved: approved={approved}")

    async def execute_task(self, task_id: str, instruction: str, context: Dict[str, Any]) -> Any:
        provider = context.get("provider", "openai")
        key = self.token_pool.get_key(provider)
        return {
            "provider": provider,
            "active_key_available": bool(key),
            "pool_status": self.token_pool.get_pool_status(provider),
        }

    def get_pool_status(self) -> Dict[str, Dict[str, Any]]:
        """Return status for all registered credential providers."""
        return self.token_pool.get_all_status()
