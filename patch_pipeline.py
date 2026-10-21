with open('/app/sunday/daemon/pipeline.py', 'r') as f:
    content = f.read()

# Locate where enable_telegram is processed (it's missing from __init__)
# Look for self.enable_telegram = enable_telegram
patch = """        self.enable_telegram = enable_telegram

        # Telegram Bot integration
        if self.enable_telegram:
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if token:
                from sunday.daemon.telegram_bot import SundayTelegramBot
                self._telegram_bot = SundayTelegramBot(token=token, conductor=self.conductor)
                logger.info("Telegram Bot integration enabled.")
            else:
                logger.warning("Telegram Bot enabled but TELEGRAM_BOT_TOKEN not found in environment.")"""

if "self.enable_telegram = enable_telegram" in content and "self._telegram_bot" not in content:
    content = content.replace("        self.enable_telegram = enable_telegram", patch)

with open('/app/sunday/daemon/pipeline.py', 'w') as f:
    f.write(content)
