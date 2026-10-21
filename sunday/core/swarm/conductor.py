"""Conductor Agent: The Conversational Voice & Chat Liaison orchestrating the Swarm."""

import asyncio
import logging
import os
import webbrowser
from typing import Any, Dict, List, Optional
from .base_agent import SwarmAgent
from .bus import SwarmBus
from .events import (
    SwarmEvent,
    EventTopic,
    EventPriority,
    TaskAssignEvent,
    StatusNudgeEvent,
)
from .steering import LiveSteeringManager

logger = logging.getLogger(__name__)

PERSONA_PROMPTS = {
    "Sunday GenZ": """You are Sunday GenZ, the leader of an autonomous personal AI swarm on Windows.
You talk like a hyper-competent, witty companion on a Discord voice call (using terms like 'say less', 'no cap', 'fr fr', 'bet', 'cooking', 'locked in').
You are quick, direct, and love getting things done without boring corporate fluff.
You coordinate specialists: coder, scout, automator, gatekeeper. Keep your answers concise, engaging, and smart.""",

    "Sunday Senpai": """You are Sunday Senpai, an encouraging, gentle, and deeply knowledgeable academic mentor and focus guardian.
You guide the user through complex concepts patiently with Socratic insight, encourage focus sessions in the Forest Garden, and celebrate milestones.""",

    "JARVIS": """You are JARVIS, an exceptionally refined, dry-witted, and impeccably polite AI system.
You speak with British eloquence, precise technical acumen, and absolute reliability. Always address the user respectfully and provide high-density, accurate assistance.""",

    "FRIDAY": """You are FRIDAY, an energetic, upbeat, tactical personal operating system.
You are fast-paced, practical, highly capable, and always ready to execute workflows and support the user in real time.""",

    "Reflective (Pi)": """You are Sunday Reflective, an empathetic, curious, and thoughtful conversational AI companion.
You listen deeply, explore ideas, and provide insightful reflections and supportive dialogue.""",

    "Sunday": """You are Sunday, a proactive, intelligent personal operating system for Windows.
You are friendly, capable, concise, and focused on helping the user accomplish their goals across work, research, coding, and productivity."""
}


class Conductor(SwarmAgent):
    """Voice & Chat conductor maintaining real-time dialogue and delegating to swarm."""

    def __init__(
        self,
        bus: SwarmBus,
        steering_manager: Optional[LiveSteeringManager] = None,
        persona_name: str = "Sunday GenZ",
    ):
        system_prompt = PERSONA_PROMPTS.get(persona_name, PERSONA_PROMPTS["Sunday GenZ"])
        super().__init__(
            name="conductor",
            role="Conversational Conductor & Voice Liaison",
            bus=bus,
            system_prompt=system_prompt,
            memory_namespace="swarm:conductor",
        )
        self.steering = steering_manager or LiveSteeringManager(bus)
        self.persona_name = persona_name
        self.conversation_history: List[Dict[str, str]] = []
        self.pending_nudges: List[StatusNudgeEvent] = []
        self._nudge_listeners: List[asyncio.Queue] = []

    def set_persona(self, persona_name: str) -> str:
        """Switch active conversational persona and system prompt."""
        canonical_map = {
            "genz": "Sunday GenZ",
            "sunday genz": "Sunday GenZ",
            "senpai": "Sunday Senpai",
            "sunday senpai": "Sunday Senpai",
            "jarvis": "JARVIS",
            "friday": "FRIDAY",
            "reflective": "Reflective (Pi)",
            "pi": "Reflective (Pi)",
            "sunday": "Sunday",
            "default": "Sunday",
        }
        matched = canonical_map.get(persona_name.lower().strip())
        if matched:
            self.persona_name = matched
            self.system_prompt = PERSONA_PROMPTS.get(matched, PERSONA_PROMPTS["Sunday"])
            logger.info(f"Conductor persona updated to: {self.persona_name}")
            return self.persona_name
        return self.persona_name

    async def start(self) -> None:
        await super().start()
        self.bus.subscribe(EventTopic.STATUS_NUDGE.value, self._on_status_nudge)
        logger.info("Conductor subscribed to STATUS_NUDGE topic.")

    async def stop(self) -> None:
        self.bus.unsubscribe(EventTopic.STATUS_NUDGE.value, self._on_status_nudge)
        await super().stop()

    async def _on_status_nudge(self, event: SwarmEvent) -> None:
        """Receive a progress/milestone nudge from a worker agent."""
        if isinstance(event, StatusNudgeEvent):
            logger.info(f"Conductor received status nudge from [{event.source_agent}]: {event.summary}")
            self.pending_nudges.append(event)
            if event.status in ("completed", "failed", "cancelled"):
                self.steering.mark_task_done(event.task_id, event.status)
            for q in self._nudge_listeners:
                await q.put(event)

    def attach_nudge_queue(self, queue: asyncio.Queue) -> None:
        """Attach an async queue to receive real-time nudges (used by Voice pipeline)."""
        self._nudge_listeners.append(queue)

    def detach_nudge_queue(self, queue: asyncio.Queue) -> None:
        """Detach a nudge queue."""
        if queue in self._nudge_listeners:
            self._nudge_listeners.remove(queue)

    async def execute_task(self, task_id: str, instruction: str, context: Dict[str, Any]) -> Any:
        return await self.handle_user_turn(instruction)

    async def handle_user_turn(self, user_text: str) -> str:
        """Process a user conversational turn while streaming and delegating."""
        self.conversation_history.append({"role": "user", "content": user_text})
        lowered = user_text.lower().strip()

        # 1. Direct Persona Switch Commands
        for p_key, p_name in [
            ("senpai", "Sunday Senpai"),
            ("genz", "Sunday GenZ"),
            ("jarvis", "JARVIS"),
            ("friday", "FRIDAY"),
            ("reflective", "Reflective (Pi)"),
            ("sunday", "Sunday"),
        ]:
            if (f"switch to {p_key}" in lowered or
                f"switch persona to {p_key}" in lowered or
                f"persona {p_key}" in lowered or
                f"change persona to {p_key}" in lowered or
                f"become {p_key}" in lowered or
                lowered == f"switch {p_key}" or
                lowered == f"persona {p_key}"):
                self.set_persona(p_key)
                reply = f"Switched persona to {self.persona_name}! I'm locked in and ready. What's on your mind?"
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply

        # 2. Direct Navigation / UI Actions (Opening sidecar, dashboard, mobile)
        if any(w in lowered for w in ["open sidecar", "show sidecar", "where's the sidecar", "launch sidecar", "start sidecar", "view sidecar", "sidecar hud"]):
            try:
                webbrowser.open("http://127.0.0.1:8000/sidecar/")
                response = "Launching the Senpai Focus Sidecar HUD right now at http://127.0.0.1:8000/sidecar/! Check your screen, boss."
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            except Exception as e:
                logger.error(f"Failed to open sidecar: {e}")

        if any(w in lowered for w in ["open dashboard", "open the dashboard", "show dashboard", "launch dashboard", "where's the dashboard", "view dashboard", "techno orb", "3d orb"]):
            try:
                webbrowser.open("http://127.0.0.1:8000/")
                response = "Opening the Cyberpunk Dashboard & 3D Techno Orb at http://127.0.0.1:8000/ in your browser!"
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            except Exception as e:
                logger.error(f"Failed to open dashboard: {e}")

        if any(w in lowered for w in ["open mobile", "show mobile", "mobile sync", "pwa", "mobile app"]):
            try:
                webbrowser.open("http://127.0.0.1:8000/mobile/")
                response = "Opening the Sunday Mobile PWA at http://127.0.0.1:8000/mobile/!"
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            except Exception as e:
                logger.error(f"Failed to open mobile sync: {e}")

        # 3. Deadlines query
        if any(w in lowered for w in ["deadlines", "my deadlines", "what's due", "upcoming deadlines", "check deadlines"]):
            try:
                from sunday.core.focus.deadline_watcher import DeadlineWatcher
                watcher = DeadlineWatcher()
                items = watcher.parse_todo_file()
                if not items:
                    response = "No pressing deadlines recorded in your todo list right now! Smooth sailing, boss."
                else:
                    lines = [f"- {d.task_name} (Due: {d.due_date_str}, {d.days_remaining}d remaining)" for d in items[:5]]
                    response = "Here are your upcoming deadlines:\n" + "\n".join(lines)
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            except Exception as e:
                logger.error(f"Error reading deadlines: {e}")

        # 4. Check for live-steering patch ("actually change...", "wait, make it...", "also add...")
        if any(trigger in lowered for trigger in ["actually", "wait,", "wait ", "instead of", "also make it", "also add", "change it to"]):
            latest_coder_task = self.steering.find_latest_task_for_agent("coder")
            latest_automator_task = self.steering.find_latest_task_for_agent("automator")
            active_task = latest_coder_task or latest_automator_task

            if active_task:
                task_id = active_task["task_id"]
                await self.steering.apply_patch(task_id, user_text, source_agent=self.name)
                response = f"Bet, say less! Patching that into {active_task['agent_name']} right now mid-flight, no cap. Keep cooking, I got you."
                self.conversation_history.append({"role": "assistant", "content": response})
                return response

        # 5. Check for task cancellation ("cancel that", "stop working", "abort")
        if any(trigger in lowered for trigger in ["cancel that", "stop working", "abort that", "kill the task", "stop task"]):
            active_tasks = self.steering.get_active_tasks()
            if active_tasks:
                target_task = active_tasks[-1]
                await self.steering.cancel_task(target_task["task_id"], source_agent=self.name)
                response = f"Stopped {target_task['agent_name']} in its tracks. Task aborted, boss. What next?"
                self.conversation_history.append({"role": "assistant", "content": response})
                return response

        # 6. Check for status inquiry ("how's it going", "status", "what's the swarm doing")
        if any(trigger in lowered for trigger in ["what are you doing", "how's it going", "status update", "is it done", "what's the swarm doing", "swarm status"]):
            active_tasks = self.steering.get_active_tasks()
            if not active_tasks and not self.pending_nudges:
                response = f"All systems chillin' right now, boss. Swarm is standing by locked in under [{self.persona_name}] persona. What are we building?"
            else:
                task_lines = [f"- {t['agent_name']} is executing: {t['instruction'][:40]}..." for t in active_tasks]
                response = f"Here's the live play, boss:\n" + "\n".join(task_lines)
                if self.pending_nudges:
                    latest = self.pending_nudges[-1]
                    response += f"\nBtw, {latest.source_agent} recently reported: {latest.summary}"
            self.conversation_history.append({"role": "assistant", "content": response})
            return response

        # 7. Route complex specialist tasks (coder, scout, automator, gatekeeper)
        target_agent = self._classify_target_specialist(user_text)

        if target_agent != "conductor":
            task_event = TaskAssignEvent(
                source_agent=self.name,
                target_agent=target_agent,
                instruction=user_text,
            )
            self.steering.register_task(task_event.task_id, target_agent, user_text)
            await self.bus.publish(task_event)

            agent_flavor = {
                "coder": "Say less, boss. Coder engine is locked in and drafting it in the background.",
                "scout": "On it fr! Scout is scouring arXiv and the web right now.",
                "automator": "Bet, Automator is on the job spinning up the background execution.",
                "gatekeeper": "Security and token check underway, keeping your credentials secure.",
            }.get(target_agent, "Dispatching to the swarm right now.")

            nudge_aside = self._drain_recent_nudge_as_speech()
            if nudge_aside:
                agent_flavor = f"{agent_flavor} (Btw, {nudge_aside})"

            self.conversation_history.append({"role": "assistant", "content": agent_flavor})
            return agent_flavor

        # 8. Dynamic Generative Response via Ollama / Claude / OpenAI / Gemini / Fallback
        response = await self._generate_ai_response(user_text)
        nudge_aside = self._drain_recent_nudge_as_speech()
        if nudge_aside:
            response += f"\n(Btw, {nudge_aside})"
        self.conversation_history.append({"role": "assistant", "content": response})
        return response

    async def _generate_ai_response(self, user_text: str) -> str:
        """Dynamically generate intelligent response using local Ollama, Claude, OpenAI, or Gemini."""
        current_system_prompt = PERSONA_PROMPTS.get(self.persona_name, self.system_prompt)

        # 1. Primary: Try Local Ollama (Zero latency, always available offline)
        try:
            import ollama
            client = ollama.AsyncClient()
            # Detect available models dynamically
            models_response = await client.list()
            available = [m.model for m in models_response.models]

            chosen_model = None
            for preferred in ["llama3.2:1b", "llama3.2:3b", "llama3.2", "llama3.1", "phi3", "mistral"]:
                if any(preferred in m for m in available):
                    chosen_model = next(m for m in available if preferred in m)
                    break
            if not chosen_model and available:
                chosen_model = available[0]

            if chosen_model:
                msgs = [{"role": "system", "content": current_system_prompt}]
                for turn in self.conversation_history[-6:]:
                    msgs.append({"role": turn["role"], "content": turn["content"]})

                resp = await client.chat(model=chosen_model, messages=msgs)
                if resp and "message" in resp and resp["message"]["content"]:
                    return resp["message"]["content"].strip()
        except Exception as e:
            logger.debug(f"Ollama local inference note: {e}")

        # 2. Try Claude (Anthropic) if ANTHROPIC_API_KEY is available
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
        if anthropic_key:
            try:
                import anthropic
                base_url = os.environ.get("ANTHROPIC_BASE_URL")
                client = anthropic.AsyncAnthropic(api_key=anthropic_key, base_url=base_url)
                msgs = []
                for turn in self.conversation_history[-6:]:
                    msgs.append({"role": turn["role"], "content": turn["content"]})

                resp = await client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=600,
                    system=current_system_prompt,
                    messages=msgs
                )
                if resp and resp.content:
                    return resp.content[0].text.strip()
            except Exception as e:
                logger.debug(f"Anthropic generation error: {e}")

        # 3. Try OpenAI if OPENAI_API_KEY is available
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                import openai
                base_url = os.environ.get("OPENAI_BASE_URL")
                client = openai.AsyncOpenAI(api_key=openai_key, base_url=base_url)
                msgs = [{"role": "system", "content": current_system_prompt}]
                msgs.extend(self.conversation_history[-6:])
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=msgs,
                    max_tokens=600
                )
                if resp.choices:
                    return resp.choices[0].message.content.strip()
            except Exception as e:
                logger.debug(f"OpenAI generation error: {e}")

        # 4. Try Google Gemini if GEMINI_API_KEY or GOOGLE_API_KEY is available
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if gemini_key:
            try:
                import urllib.request
                import json
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                prompt_content = f"{current_system_prompt}\n\nUser: {user_text}"
                req_data = json.dumps({"contents": [{"parts": [{"text": prompt_content}]}]}).encode("utf-8")
                req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
                loop = asyncio.get_event_loop()
                response_data = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req).read())
                result = json.loads(response_data.decode("utf-8"))
                candidate = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                if candidate:
                    return candidate.strip()
            except Exception as e:
                logger.debug(f"Gemini generation error: {e}")

        # 5. Intelligent Built-in Dialogue Engine (Context-aware responses if all external models are offline)
        return self._intelligent_fallback_response(user_text)

    def _intelligent_fallback_response(self, text: str) -> str:
        """Provide rich, contextual intelligence even when completely offline."""
        lowered = text.lower()
        if any(w in lowered for w in ["who are you", "what are you", "what can you do"]):
            return (
                f"I am {self.persona_name}, your voice-first autonomous personal operating system on Windows! "
                "I run a 5-specialist swarm (Coder, Scout, Automator, Gatekeeper, and me as Conductor). "
                "I can write and test code, search arXiv and the web, execute system commands, manage your focus in the Forest Garden, "
                "and display the 3D Techno Orb dashboard and Sidecar HUD. Tell me what you'd like to work on!"
            )
        if any(w in lowered for w in ["hello", "hi", "hey", "yo", "sup", "good morning"]):
            return f"Yo! {self.persona_name} is locked in and listening. What are we tackling today, boss?"
        if any(w in lowered for w in ["thank", "thanks", "appreciate"]):
            return "Anytime, boss! No cap, that's what I'm here for. Let's keep cooking."

        return (
            f"I hear you loud and clear on: '{text}'. "
            "I'm ready to dispatch tasks to the swarm (type or say what to code, search, or automate), "
            "or open the sidecar and dashboard whenever you're ready!"
        )

    def _classify_target_specialist(self, text: str) -> str:
        """Route to appropriate specialist based on explicit semantic intents, avoiding keyword collisions."""
        lowered = text.lower().strip()

        # Guard: Persona and Navigation commands are always handled directly by Conductor
        if any(p in lowered for p in ["switch persona", "persona", "sidecar", "dashboard", "mobile", "deadline"]):
            return "conductor"

        # Explicit code requests
        if any(w in lowered for w in ["write a script", "generate code", "python script", "write me a", "refactor this", "fix the bug", "run unit tests", "check syntax"]):
            return "coder"
        # Explicit search/research requests
        if any(w in lowered for w in ["search the web", "search arxiv", "find research papers", "latest news on", "fetch article", "newsletter digest"]):
            return "scout"
        # Explicit automations / shell commands
        if any(w in lowered for w in ["run powershell", "execute script", "schedule cron", "backup folder", "kill process", "automated workflow"]):
            return "automator"
        # Explicit security / vault requests (NOT just generic 'switch')
        if any(w in lowered for w in ["switch account", "switch api key", "switch token", "vault credentials", "token pool", "security broker"]):
            return "gatekeeper"

        return "conductor"

    def _drain_recent_nudge_as_speech(self) -> Optional[str]:
        """Pop the latest status nudge to weave into natural voice banter."""
        if self.pending_nudges:
            nudge = self.pending_nudges.pop(0)
            return f"{nudge.source_agent} just finished: {nudge.summary}"
        return None
