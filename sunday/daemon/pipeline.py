import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from sunday.core.broker.audit import AuditLedger
from sunday.core.broker.broker import Broker
from sunday.core.broker.permissions import PermissionChecker, default_permission_rules
from sunday.core.broker.vault import KeyringVault
from sunday.core.orchestrator import Orchestrator
from sunday.mcp.client import MCPClient
from sunday.mcp.servers import MCPServerRegistry
from sunday.memory.task_store import TaskStore
from sunday.memory.titans_memory import TitansMemory
from sunday.tools.registry import ToolRegistry

try:
    from sunday.sidecar.windows_sidecar import WindowsSidecar
except ImportError:
    WindowsSidecar = None  # Sidecar unavailable

from sunday.core.swarm import (
    Automator,
    Coder,
    Conductor,
    Gatekeeper,
    LiveSteeringManager,
    Scout,
    SwarmBus,
)

from .livekit_pipeline import LiveKitVoicePipeline
from .stt import STT_AVAILABLE, STTEngine
from .tts import TTSEngine
from .wake import OPENWAKEWORD_AVAILABLE, WakeWordDetector

logger = logging.getLogger(__name__)

class SundayDaemon:
    """Main Sunday daemon integrating all components."""

    def __init__(
        self,
        enable_dashboard: bool = False,
        enable_sidecar: bool = False,
        enable_telegram: bool = False,
        enable_mobile_sync: bool = False,
        enable_insomnia: bool = False,
        enable_autonomous_scout: bool = False,
        enable_fluid_intent: bool = False,
        enable_proactive_suggest: bool = False,
        voice_mode: bool = False,
    ):
        """Initialize Sunday daemon.
        
        Args:
            enable_dashboard: Enable FastAPI dashboard
            enable_sidecar: Enable Windows sidecar
            enable_telegram: Enable Telegram bot (requires TELEGRAM_BOT_TOKEN env var)
            enable_mobile_sync: Enable mobile sync / PWA endpoints
            enable_insomnia: Enable 24/7 Windows Insomnia / AwayMode lid-closed execution
            enable_autonomous_scout: Enable continuous background newsletter & paper scouting
            enable_fluid_intent: Enable neural HuggingFace fluid intent understanding
            enable_proactive_suggest: Enable autonomous proactive habit suggestion engine
            voice_mode: Enable voice input loop with wake word detection
        """
        self.enable_dashboard = enable_dashboard
        self.enable_sidecar = enable_sidecar
        self.enable_telegram = enable_telegram
        self.enable_mobile_sync = enable_mobile_sync
        self.enable_insomnia = enable_insomnia
        self.enable_autonomous_scout = enable_autonomous_scout
        self.enable_fluid_intent = enable_fluid_intent
        self.enable_proactive_suggest = enable_proactive_suggest
        self.voice_mode = voice_mode
        self.running = False

        # Initialize core components
        self._init_core()
        self._init_memory()
        self._init_broker()
        self._init_mcp()
        self._init_swarm()

        # Initialize optional components
        self.sidecar = None
        if self.enable_sidecar and callable(WindowsSidecar):
            self.sidecar = WindowsSidecar()

        # Initialize voice components
        self.wake_detector = WakeWordDetector()
        self.stt = STTEngine()
        self.tts = TTSEngine()

        # Voice mode explicitly toggled or falls back to text
        self.text_mode = not self.voice_mode

    def _init_core(self):
        """Initialize core orchestrator."""
        self.orchestrator = Orchestrator()
        logger.info("Core orchestrator initialized")

    def _init_memory(self):
        """Initialize memory systems."""
        # Initialize Titans Memory
        memory_path = Path('sunday') / 'data' / 'titans_memory.json'
        self.titans_memory = TitansMemory(
            memory_path=memory_path,
            surprise_threshold=0.5,
            decay_rate=0.95,
            max_episodes=1000
        )

        # Initialize Task Store
        self.task_store = TaskStore()

        logger.info("Memory systems initialized")

    def _init_broker(self):
        """Initialize security broker."""
        # Initialize broker components
        audit_path = Path('sunday') / 'data' / 'audit.jsonl'
        self.audit_ledger = AuditLedger(audit_path)
        self.vault = KeyringVault()
        self.permission_checker = PermissionChecker(default_permission_rules())

        # Build tool registry dict for broker
        tool_registry_dict = {}
        for tool in ToolRegistry.get_all():
            tool_registry_dict[tool.name] = {
                "risk": tool.risk.value,
                "reversible": tool.reversible,
                "required_args": tool.required_args
            }

        # Initialize broker
        self.broker = Broker(
            audit_ledger=self.audit_ledger,
            vault=self.vault,
            permission_checker=self.permission_checker,
            tool_registry=tool_registry_dict
        )

        logger.info("Security broker initialized")

    def _init_mcp(self):
        """Initialize MCP client."""
        self.mcp_client = MCPClient()
        self.mcp_registry = MCPServerRegistry()

        # Register default servers
        for name, config in self.mcp_registry.list_servers().items():
            self.mcp_client.register_server(name, config)

        logger.info("MCP client initialized")

    def _init_swarm(self):
        """Initialize Swarm Mesh and 5 Core Specialists."""
        self.swarm_bus = SwarmBus()
        self.steering_manager = LiveSteeringManager(self.swarm_bus)
        self.conductor = Conductor(self.swarm_bus, self.steering_manager)
        self.coder = Coder(self.swarm_bus)
        self.scout = Scout(self.swarm_bus)
        self.automator = Automator(self.swarm_bus)
        self.gatekeeper = Gatekeeper(self.swarm_bus)
        self.livekit_pipeline = LiveKitVoicePipeline(bus=self.swarm_bus, conductor=self.conductor)
        logger.info("Swarm Mesh and 5 Core Specialists initialized")

        if getattr(self, "enable_telegram", False):
            import os
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if token:
                from sunday.daemon.telegram_bot import SundayTelegramBot
                self._telegram_bot = SundayTelegramBot(token=token, conductor=self.conductor)
                logger.info("Telegram Bot integration enabled.")
            else:
                logger.warning("Telegram Bot enabled but TELEGRAM_BOT_TOKEN not found in environment.")

    async def run(self):
        """Run Sunday daemon."""
        self.running = True
        logger.info(f"Starting Sunday Daemon (Text Mode: {self.text_mode})")
        logger.info(f"Dashboard: {self.enable_dashboard}, Sidecar: {self.enable_sidecar}")

        # Start Swarm Bus and Specialists
        await self.swarm_bus.start()
        await self.conductor.start()
        await self.coder.start()
        await self.scout.start()
        await self.automator.start()
        await self.gatekeeper.start()
        logger.info("Swarm Mesh specialists started and connected")

        # Start dashboard if enabled
        if self.enable_dashboard:
            asyncio.create_task(self._run_dashboard())

        # Start sidecar monitoring if enabled
        if self.enable_sidecar:
            asyncio.create_task(self._run_sidecar_monitor())

        # Start Telegram bot if enabled and token is available
        if self.enable_telegram:
            tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if tg_token:
                from sunday.daemon.telegram_bot import SundayTelegramBot
                self._telegram_bot = SundayTelegramBot(token=tg_token, conductor=self.conductor)
                asyncio.create_task(self._telegram_bot.start())
                logger.info("Telegram bot started")
            else:
                logger.warning("--telegram flag set but TELEGRAM_BOT_TOKEN env var not found")

        # Start Insomnia 24/7 mode if enabled
        if self.enable_insomnia:
            from sunday.daemon.insomnia import InsomniaEngine
            self.insomnia_engine = InsomniaEngine()
            self.insomnia_engine.activate()
            logger.info("24/7 Windows Insomnia / AwayMode enabled.")

        # Start Autonomous Scout if enabled
        if self.enable_autonomous_scout:
            from sunday.core.scout.newsletter_scout import NewsletterScout
            self.autonomous_scout = NewsletterScout(titans_memory=self.titans_memory)
            asyncio.create_task(self._run_scout_loop())
            logger.info("Autonomous Newsletter & Paper Scout started.")

        # Initialize Fluid Intent Engine
        from sunday.core.intelligence.fluid_intent import FluidIntentEngine
        self.fluid_intent_engine = FluidIntentEngine(enable_neural=self.enable_fluid_intent)

        # Initialize Proactive Suggestion Engine if enabled
        if self.enable_proactive_suggest:
            from sunday.core.intelligence.suggestion_engine import SuggestionEngine
            self.suggestion_engine = SuggestionEngine(swarm_bus=self.swarm_bus)
            asyncio.create_task(self._run_suggestion_loop())
            logger.info("Proactive Suggestion Engine started.")

        # Log mobile sync status
        if self.enable_mobile_sync:
            logger.info("Mobile sync enabled — PWA served at /mobile/")

        # Connect to MCP servers
        await self._connect_mcp_servers()

        # Run main loop
        # Start Telegram Bot if enabled
        if hasattr(self, "_telegram_bot") and self._telegram_bot:
            asyncio.create_task(self._telegram_bot.start())

        if self.text_mode:
            await self._run_text_loop()
        else:
            await self._run_voice_loop()

    async def _run_dashboard(self):
        """Run FastAPI dashboard."""
        try:
            import uvicorn

            from sunday.dashboard.api.main import app

            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=8000,
                log_level="warning"
            )
            server = uvicorn.Server(config)
            
            # Print prominent visual links in console
            print("\n" + "="*58)
            print("  🌟 SUNDAY DASHBOARD & SIDECAR READY")
            print("="*58)
            print("  ▸ Dashboard & 3D Orb : http://127.0.0.1:8000/")
            print("  ▸ Sidecar HUD        : http://127.0.0.1:8000/sidecar/")
            print("  ▸ Mobile PWA         : http://127.0.0.1:8000/mobile/")
            print("  ▸ REST API Docs      : http://127.0.0.1:8000/docs")
            print("="*58 + "\n")

            # Auto-open dashboard in default browser
            import webbrowser
            try:
                webbrowser.open("http://127.0.0.1:8000/")
            except Exception:
                pass

            await server.serve()
        except Exception as e:
            logger.error(f"Dashboard error: {e}")

    async def _run_sidecar_monitor(self):
        """Run Windows sidecar monitor with FocusSentry & Forest wilting guard."""
        from sunday.dashboard.api.routes import forest_engine
        from sunday.sidecar.focus_sentry import EscalationStage, FocusSentry

        sentry = FocusSentry()
        while self.running:
            try:
                if self.enable_sidecar and self.sidecar:
                    window_info = self.sidecar.get_active_window()
                    if window_info:
                        sentry_res = sentry.update(window_info)
                        if sentry_res.get("new_escalation"):
                            stage = sentry_res.get("stage")
                            msg = sentry_res.get("message", "")
                            logger.info(f"Senpai Focus Sentry: {msg}")

                            if stage == EscalationStage.STAGE_1_VOICE_NUDGE:
                                if hasattr(self, "conductor"):
                                    await self.conductor.publish_nudge("focus_sentry", "progress", msg)
                            elif stage == EscalationStage.STAGE_3_ENFORCEMENT:
                                # Auto minimize offending window
                                hwnd = sentry_res.get("hwnd")
                                if hwnd:
                                    self.sidecar.minimize_window(hwnd)
                                # Wilt current forest tree
                                await forest_engine.wilt_current_tree("Distraction sustained past limit")
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Sidecar monitor error: {e}")
                await asyncio.sleep(5)

    async def _run_scout_loop(self):
        """Run periodic autonomous scouting for tech advancements and newsletters."""
        while self.running:
            try:
                if hasattr(self, "autonomous_scout"):
                    discoveries = await self.autonomous_scout.run_scout_cycle()
                    if discoveries and hasattr(self, "conductor"):
                        top = discoveries[0]
                        await self.conductor.publish_nudge(
                            task_id="autonomous_scout",
                            status="completed",
                            summary=f"Read new research: '{top.title}' ({top.source})"
                        )
                # Run scouting cycle every 30 minutes in background
                await asyncio.sleep(1800)
            except Exception as e:
                logger.error(f"Autonomous scout loop error: {e}")
                await asyncio.sleep(60)

    async def _run_suggestion_loop(self):
        """Run periodic proactive habit and suggestion checks."""
        while self.running:
            try:
                if hasattr(self, "suggestion_engine"):
                    suggestion = await self.suggestion_engine.generate_suggestion()
                    if suggestion and hasattr(self, "conductor"):
                        await self.suggestion_engine.broadcast_suggestion_to_swarm(suggestion)
                # Check for suggestions every 5 minutes
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Proactive suggestion loop error: {e}")
                await asyncio.sleep(60)


    async def _connect_mcp_servers(self):
        """Connect to configured MCP servers."""
        for server_name in self.mcp_registry.list_servers().keys():
            try:
                connected = await self.mcp_client.connect(server_name)
                if connected:
                    logger.info(f"Connected to MCP server: {server_name}")
                else:
                    logger.warning(f"Failed to connect to MCP server: {server_name}")
            except Exception as e:
                logger.error(f"Error connecting to {server_name}: {e}")

    async def _run_text_loop(self):
        """Run text input loop."""
        print("\n" + "="*50)
        print("SUNDAY DAEMON - TEXT MODE")
        print("="*50)
        print("Type your input below (Ctrl+C to exit)")
        print("Commands: /status, /swarm, /tools, /persona, /sidecar, /dashboard, /help")
        print("="*50 + "\n")

        while self.running:
            try:
                loop = asyncio.get_event_loop()
                user_input = await loop.run_in_executor(None, input, f"\nYou ({self.conductor.persona_name}): ")

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # Process through Swarm Conductor with active persona
                response = await self.conductor.handle_user_turn(user_input)
                print(f"\nSunday ({self.conductor.persona_name}): {response}")

                # Store in Titans Memory
                await self.titans_memory.remember(
                    content=f"User: {user_input}\nSunday: {response}",
                    outcome="success"
                )

            except (KeyboardInterrupt, EOFError):
                self.stop()
            except Exception as e:
                logger.error(f"Error in text loop: {e}")
                print(f"\nError: {e}")

    async def _run_voice_loop(self):
        """Run voice input loop."""
        print("\n" + "="*50)
        print("SUNDAY DAEMON - VOICE MODE")
        print("="*50)
        print("Say 'Hey Sunday' or 'Hey Jarvis' to wake me up")
        print("Press Ctrl+C to exit")
        print("="*50 + "\n")

        while self.running:
            try:
                detected = await self.wake_detector.wait_for_wake_word()
                if not detected or not self.running:
                    continue

                # Barge-in support
                self.tts.stop_speaking()
                print("\n[🎙️ Wake word detected - Listening...]")

                text = await self.stt.listen()
                if not text:
                    continue

                logger.info(f"Recognized: {text}")
                print(f"\nYou: {text}")

                # Process through Swarm Conductor with multi-model brain
                response = await self.conductor.handle_user_turn(text)
                print(f"\nSunday ({self.conductor.persona_name}): {response}")

                # Store in Titans Memory
                await self.titans_memory.remember(
                    content=f"User: {text}\nSunday: {response}",
                    outcome="success"
                )

                # Speak response headlessly
                await self.tts.speak(response, self.conductor.persona_name)

            except Exception as e:
                logger.error(f"Error in voice loop: {e}")
                await asyncio.sleep(1)

    async def _handle_command(self, command: str):
        """Handle slash commands."""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/status":
            print("\n--- Sunday Status ---")
            print(f"Mode: {'Text' if self.text_mode else 'Voice'}")
            print(f"Active Persona: {self.conductor.persona_name}")
            print(f"Dashboard: {'Enabled' if self.enable_dashboard else 'Disabled'}")
            print(f"Sidecar: {'Enabled' if self.enable_sidecar else 'Disabled'}")
            print(f"Tools: {len(ToolRegistry.get_all())}")
            print(f"MCP Servers: {len(self.mcp_client.get_connected_servers())}")
            stats = await self.titans_memory.get_statistics()
            print(f"Memory Episodes: {stats['total_episodes']}")
            print("---------------------\n")

        elif cmd == "/persona":
            if len(parts) > 1:
                target = " ".join(parts[1:])
                new_p = self.conductor.set_persona(target)
                print(f"\nActive persona updated to: [{new_p}]\n")
            else:
                print(f"\nCurrent Persona: {self.conductor.persona_name}")
                print("Available personas: genz, senpai, jarvis, friday, reflective, sunday")
                print("Usage: /persona <name> (e.g. /persona senpai)\n")

        elif cmd in ["/sidecar", "/hud"]:
            import webbrowser
            try:
                webbrowser.open("http://127.0.0.1:8000/sidecar/")
                print("\nOpening Senpai Sidecar HUD at http://127.0.0.1:8000/sidecar/ ...\n")
            except Exception as e:
                print(f"\nFailed to open browser: {e}\n")

        elif cmd in ["/dashboard", "/orb"]:
            import webbrowser
            try:
                webbrowser.open("http://127.0.0.1:8000/")
                print("\nOpening Cyberpunk Techno Orb Dashboard at http://127.0.0.1:8000/ ...\n")
            except Exception as e:
                print(f"\nFailed to open browser: {e}\n")

        elif cmd in ["/mobile", "/pwa"]:
            import webbrowser
            try:
                webbrowser.open("http://127.0.0.1:8000/mobile/")
                print("\nOpening Mobile PWA at http://127.0.0.1:8000/mobile/ ...\n")
            except Exception as e:
                print(f"\nFailed to open browser: {e}\n")

        elif cmd == "/tools":
            print("\n--- Available Tools ---")
            for category in set(t.category for t in ToolRegistry.get_all()):
                tools = ToolRegistry.list_by_category(category)
                print(f"\n{category.upper()}:")
                for tool in tools[:5]:
                    print(f"  - {tool.name}: {tool.description}")
            print("-----------------------\n")

        elif cmd == "/swarm":
            print("\n--- Sunday Swarm Mesh Status ---")
            specialists = ["conductor", "coder", "scout", "automator", "gatekeeper"]
            print(f"Core Specialists: {', '.join(specialists)}")
            active = self.steering_manager.get_active_tasks()
            print(f"Active Background Tasks: {len(active)}")
            for t in active:
                print(f"  [{t['agent_name']}] {t['task_id'][:8]} - {t['instruction'][:40]}")
            nudges = len(self.conductor.pending_nudges)
            print(f"Pending Status Nudges: {nudges}")
            print("--------------------------------\n")

        elif cmd == "/help":
            print("\n--- Commands ---")
            print("/status     - Show system status & active persona")
            print("/persona    - Switch persona (genz, senpai, jarvis, friday, reflective, sunday)")
            print("/sidecar    - Open Senpai Sidecar HUD in browser")
            print("/dashboard  - Open 3D Techno Orb Dashboard in browser")
            print("/mobile     - Open Mobile PWA in browser")
            print("/swarm      - Show active swarm specialists & tasks")
            print("/tools      - List available tools")
            print("/help       - Show this help")
            print("----------------\n")

        else:
            print(f"\nUnknown command: {cmd}")
            print("Type /help for available commands\n")

    def stop(self):
        """Stop Sunday daemon."""
        logger.info("Stopping Sunday Daemon...")
        self.running = False
        self.wake_detector.stop()
        self.tts.stop_speaking()
        if hasattr(self, "livekit_pipeline"):
            try:
                asyncio.create_task(self.livekit_pipeline.end_call())
            except Exception:
                pass
        if hasattr(self, "swarm_bus"):
            try:
                asyncio.create_task(self.swarm_bus.stop())
            except Exception:
                pass
        if hasattr(self, "_telegram_bot"):
            try:
                asyncio.create_task(self._telegram_bot.stop())
            except Exception:
                pass
        if hasattr(self, "insomnia_engine"):
            try:
                self.insomnia_engine.deactivate()
            except Exception:
                pass

    def cleanup(self):
        """Cleanup resources."""
        self.wake_detector.cleanup()
        self.stt.cleanup()
        self.tts.cleanup()
        logger.info("Cleanup complete")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Sunday - Voice-first, local-first personal AI agent")
    parser.add_argument("--dashboard", action="store_true", help="Enable FastAPI dashboard")
    parser.add_argument("--sidecar", action="store_true", help="Enable Windows sidecar")
    parser.add_argument("--telegram", action="store_true", help="Enable Telegram bot (requires TELEGRAM_BOT_TOKEN env var)")
    parser.add_argument("--mobile-sync", action="store_true", help="Enable mobile sync / PWA endpoints")
    parser.add_argument("--insomnia", action="store_true", help="Enable 24/7 Windows Insomnia / AwayMode lid-closed execution")
    parser.add_argument("--autonomous-scout", action="store_true", help="Enable continuous background newsletter & paper scouting")
    parser.add_argument("--fluid-intent", action="store_true", help="Enable neural HuggingFace fluid intent understanding")
    parser.add_argument("--voice", action="store_true", help="Launch in Voice Mode with wake word detection ('Hey Sunday')")
    parser.add_argument("--text", action="store_true", help="Launch in Text Mode interactive console (default)")
    parser.add_argument("--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize daemon
    daemon = SundayDaemon(
        enable_dashboard=args.dashboard,
        enable_sidecar=args.sidecar,
        enable_telegram=args.telegram,
        enable_mobile_sync=args.mobile_sync,
        enable_insomnia=args.insomnia,
        enable_autonomous_scout=args.autonomous_scout,
        enable_fluid_intent=args.fluid_intent,
        enable_proactive_suggest=args.proactive_suggest,
        voice_mode=args.voice,
    )

    # Setup signal handlers
    def signal_handler(sig, frame):
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run daemon
    try:
        asyncio.run(daemon.run())
    finally:
        daemon.cleanup()


if __name__ == "__main__":
    main()
