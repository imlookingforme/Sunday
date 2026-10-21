"""Asynchronous Event Bus for the Sunday Swarm Mesh."""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from collections import defaultdict

from .events import SwarmEvent, EventPriority, EventTopic

logger = logging.getLogger(__name__)

# Type for event handler callback
EventHandler = Callable[[SwarmEvent], Coroutine[Any, Any, None]]


class SwarmBus:
    """Central asynchronous message broker facilitating inter-agent communication."""

    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        self._subscribers: Dict[str, Set[EventHandler]] = defaultdict(set)
        self._agent_subscribers: Dict[str, Set[EventHandler]] = defaultdict(set)
        self._history: List[SwarmEvent] = []
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the background event dispatch loop."""
        if self._running:
            return
        self._running = True
        self._dispatch_task = asyncio.create_task(self._process_queue())
        logger.info("SwarmBus started.")

    async def stop(self) -> None:
        """Stop the background event dispatch loop."""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
            self._dispatch_task = None
        logger.info("SwarmBus stopped.")

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event topic (or '*' for all topics)."""
        self._subscribers[topic].add(handler)

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from a topic."""
        if topic in self._subscribers and handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)

    def register_agent_mailbox(self, agent_name: str, handler: EventHandler) -> None:
        """Register a direct mailbox handler for a specific agent."""
        self._agent_subscribers[agent_name].add(handler)

    def unregister_agent_mailbox(self, agent_name: str, handler: EventHandler) -> None:
        """Unregister a direct mailbox handler for an agent."""
        if agent_name in self._agent_subscribers and handler in self._agent_subscribers[agent_name]:
            self._agent_subscribers[agent_name].remove(handler)

    async def publish(self, event: SwarmEvent) -> None:
        """Enqueue an event for prioritized asynchronous delivery."""
        # Tuple format: (priority, timestamp, event)
        await self._queue.put((int(event.priority), event.timestamp, event))

    async def publish_now(self, event: SwarmEvent) -> None:
        """Immediately dispatch an event without queueing (useful for synchronous tests)."""
        await self._dispatch_event(event)

    async def _process_queue(self) -> None:
        """Main consumer loop dequeuing and dispatching events by priority."""
        while self._running:
            try:
                priority, timestamp, event = await self._queue.get()
                await self._dispatch_event(event)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in SwarmBus dispatch loop: {e}", exc_info=True)

    async def _dispatch_event(self, event: SwarmEvent) -> None:
        """Dispatch event to matching handlers and record in history."""
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self.max_history:
                self._history.pop(0)

        handlers_to_call: Set[EventHandler] = set()

        # Direct targeting
        if event.target_agent and event.target_agent in self._agent_subscribers:
            handlers_to_call.update(self._agent_subscribers[event.target_agent])

        # Topic subscriptions
        topic_key = event.topic.value if hasattr(event.topic, "value") else str(event.topic)
        if topic_key in self._subscribers:
            handlers_to_call.update(self._subscribers[topic_key])

        # Wildcard subscriptions
        if "*" in self._subscribers:
            handlers_to_call.update(self._subscribers["*"])

        # Execute handlers concurrently
        if handlers_to_call:
            coroutines = []
            for handler in handlers_to_call:
                coroutines.append(self._invoke_handler(handler, event))
            await asyncio.gather(*coroutines, return_exceptions=True)

    async def _invoke_handler(self, handler: EventHandler, event: SwarmEvent) -> None:
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Handler {handler} failed on event {event.event_id}: {e}", exc_info=True)

    def get_history(self, topic: Optional[str] = None, agent: Optional[str] = None) -> List[SwarmEvent]:
        """Retrieve recent event history with optional topic or agent filter."""
        filtered = self._history
        if topic:
            filtered = [e for e in filtered if (e.topic.value if hasattr(e.topic, "value") else str(e.topic)) == topic]
        if agent:
            filtered = [e for e in filtered if e.source_agent == agent or e.target_agent == agent]
        return list(filtered)
