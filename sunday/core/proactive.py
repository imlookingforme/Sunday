"""
ProactiveEngine for Sunday.
Runs periodic checks (inbox, calendar, tasks) and generates notifications.
"""
import asyncio
import logging
from datetime import datetime

class ProactiveEngine:
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.is_running = False
        self.logger = logging.getLogger(__name__)

    async def start(self):
        self.is_running = True
        asyncio.create_task(self._proactive_loop())
        self.logger.info("Proactive engine started.")

    async def stop(self):
        self.is_running = False
        self.logger.info("Proactive engine stopped.")

    async def _proactive_loop(self):
        while self.is_running:
            await asyncio.sleep(60 * 60) # Check every hour
            if not self.is_running:
                break
            await self._run_checks()

    async def _run_checks(self):
        now = datetime.now()
        if now.hour == 8 and now.minute < 60:
            await self._generate_morning_briefing()

    async def _generate_morning_briefing(self):
        if self.orchestrator:
            # In a real setup, fetch weather, calendar, etc.
            briefing = "Good morning! You have 3 meetings today and your first task is pending."
            # Route through orchestrator or TTS
            print(f"[PROACTIVE] {briefing}")
