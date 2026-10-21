with open('/app/sunday/daemon/pipeline.py', 'r') as f:
    content = f.read()

# Add starting of the bot to the run method
patch2 = """        # Start Telegram Bot if enabled
        if hasattr(self, "_telegram_bot") and self._telegram_bot:
            asyncio.create_task(self._telegram_bot.start())

        if self.text_mode:
"""
content = content.replace("        if self.text_mode:\n", patch2)

with open('/app/sunday/daemon/pipeline.py', 'w') as f:
    f.write(content)
