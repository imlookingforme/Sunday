with open('/app/sunday/daemon/pipeline.py', 'r') as f:
    content = f.read()

patch3 = """    def _init_swarm(self):
        \"\"\"Initialize Swarm Mesh and 5 Core Specialists.\"\"\"
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
                logger.warning("Telegram Bot enabled but TELEGRAM_BOT_TOKEN not found in environment.")"""

old = """    def _init_swarm(self):
        \"\"\"Initialize Swarm Mesh and 5 Core Specialists.\"\"\"
        self.swarm_bus = SwarmBus()
        self.steering_manager = LiveSteeringManager(self.swarm_bus)
        self.conductor = Conductor(self.swarm_bus, self.steering_manager)
        self.coder = Coder(self.swarm_bus)
        self.scout = Scout(self.swarm_bus)
        self.automator = Automator(self.swarm_bus)
        self.gatekeeper = Gatekeeper(self.swarm_bus)
        self.livekit_pipeline = LiveKitVoicePipeline(bus=self.swarm_bus, conductor=self.conductor)
        logger.info("Swarm Mesh and 5 Core Specialists initialized")"""

content = content.replace(old, patch3)

with open('/app/sunday/daemon/pipeline.py', 'w') as f:
    f.write(content)
