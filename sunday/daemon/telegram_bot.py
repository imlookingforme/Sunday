"""Telegram Bot integration for Sunday AI.

Uses raw HTTP calls to the Telegram Bot API via aiohttp — no external
``python-telegram-bot`` package required.  Text messages are routed
straight to the Swarm Conductor; voice messages are downloaded and a
placeholder STT step is noted before routing.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)

# Telegram Bot API base URL template
_TG_API = "https://api.telegram.org/bot{token}"
_TG_FILE = "https://api.telegram.org/file/bot{token}"


class SundayTelegramBot:
    """Telegram bot that bridges Telegram chats to the Sunday Swarm Conductor.

    Args:
        token: Telegram Bot API token (from @BotFather).
        conductor: A :class:`sunday.core.swarm.Conductor` instance for
            routing user messages through the swarm.
    """

    def __init__(self, token: str, conductor: Any) -> None:
        self.token: str = token
        self.conductor: Any = conductor
        self._api_url: str = _TG_API.format(token=token)
        self._file_url: str = _TG_FILE.format(token=token)
        self._session: Optional[aiohttp.ClientSession] = None
        self._running: bool = False
        self._offset: int = 0  # Telegram update offset for long-polling

    # ──────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────

    async def start(self) -> None:
        """Start the Telegram long-polling loop.

        Creates an ``aiohttp.ClientSession`` and continuously polls the
        Telegram ``getUpdates`` endpoint, dispatching each incoming
        message to :meth:`_handle_message`.
        """
        logger.info("Starting Telegram bot polling…")
        self._session = aiohttp.ClientSession()
        self._running = True

        try:
            while self._running:
                try:
                    updates = await self._get_updates()
                    for update in updates:
                        message = update.get("message")
                        if message:
                            await self._handle_message(message)
                        # Advance offset past this update
                        self._offset = update["update_id"] + 1
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("Telegram poll error: %s", exc)
                    await asyncio.sleep(5)  # back-off on transient errors
        finally:
            await self._close_session()

    async def stop(self) -> None:
        """Stop the polling loop gracefully."""
        logger.info("Stopping Telegram bot…")
        self._running = False
        await self._close_session()

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    async def _close_session(self) -> None:
        """Close the aiohttp session if open."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _get_updates(self) -> list[Dict[str, Any]]:
        """Long-poll the Telegram ``getUpdates`` endpoint.

        Returns:
            A list of update dicts from the Telegram API.
        """
        assert self._session is not None
        url = f"{self._api_url}/getUpdates"
        params: Dict[str, Any] = {
            "offset": self._offset,
            "timeout": 30,  # long-poll timeout in seconds
        }
        async with self._session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=45)) as resp:
            data = await resp.json()
            if not data.get("ok"):
                logger.warning("getUpdates returned ok=false: %s", data)
                return []
            return data.get("result", [])

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Route an incoming Telegram message to the Conductor.

        Handles two content types:
        - **text**: routes the plain text directly.
        - **voice**: downloads the ``.ogg`` voice note, mocks STT
          transcription, and routes the (placeholder) transcript.

        Args:
            message: A Telegram ``Message`` object (dict).
        """
        chat_id: int = message["chat"]["id"]

        # ── Text message ──
        text: Optional[str] = message.get("text")
        if text:
            logger.info("Telegram text from chat %s: %s", chat_id, text[:80])
            try:
                response = await self.conductor.handle_user_turn(text)
            except Exception as exc:
                logger.error("Conductor error: %s", exc)
                response = "yo something broke on my end 😵 try again in a sec"
            await self._send_reply(chat_id, response)
            return

        # ── Voice message ──
        voice: Optional[Dict[str, Any]] = message.get("voice")
        if voice:
            logger.info("Telegram voice from chat %s (duration=%ss)", chat_id, voice.get("duration"))
            ogg_path = await self._download_voice(voice["file_id"])
            if ogg_path:
                # NOTE: In production, this would pipe the .ogg through a real
                # STT engine (e.g. Whisper).  For now we mock the transcript.
                transcript = "[voice transcription placeholder]"
                logger.info("Mock STT transcript: %s", transcript)
                try:
                    response = await self.conductor.handle_user_turn(transcript)
                except Exception as exc:
                    logger.error("Conductor error: %s", exc)
                    response = "couldn't process that voice note rn 😵"
                await self._send_reply(chat_id, f"🎙 heard: _{transcript}_\n\n{response}")
                # Clean up temp file
                try:
                    os.remove(ogg_path)
                except OSError:
                    pass
            else:
                await self._send_reply(chat_id, "couldn't download that voice note — try again?")
            return

        # ── Unsupported content ──
        logger.debug("Ignoring unsupported message type from chat %s", chat_id)

    async def _download_voice(self, file_id: str) -> Optional[str]:
        """Download a Telegram voice file to a temporary ``.ogg`` path.

        Args:
            file_id: Telegram file ID for the voice message.

        Returns:
            Absolute path to the downloaded ``.ogg`` file, or ``None`` on failure.
        """
        assert self._session is not None
        # Step 1: resolve file_id → file_path via getFile
        url = f"{self._api_url}/getFile"
        async with self._session.get(url, params={"file_id": file_id}) as resp:
            data = await resp.json()
            if not data.get("ok"):
                logger.warning("getFile failed: %s", data)
                return None
            file_path: str = data["result"]["file_path"]

        # Step 2: download the actual file bytes
        download_url = f"{self._file_url}/{file_path}"
        async with self._session.get(download_url) as resp:
            if resp.status != 200:
                logger.warning("Voice download HTTP %s", resp.status)
                return None
            voice_bytes = await resp.read()

        # Step 3: write to a temp .ogg file
        tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
        try:
            tmp.write(voice_bytes)
            tmp.flush()
        finally:
            tmp.close()
        logger.debug("Voice saved to %s (%d bytes)", tmp.name, len(voice_bytes))
        return tmp.name

    async def _send_reply(self, chat_id: int, text: str) -> None:
        """Send a text reply to a Telegram chat.

        Args:
            chat_id: The Telegram chat ID to reply to.
            text: The message text to send (supports Markdown).
        """
        assert self._session is not None
        url = f"{self._api_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        try:
            async with self._session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("sendMessage HTTP %s: %s", resp.status, body[:200])
        except Exception as exc:
            logger.error("Failed to send Telegram reply: %s", exc)
