import asyncio
import io
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import edge_tts
    import av
    import pyaudio
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


PERSONA_VOICES = {
    "JARVIS": "en-GB-ThomasNeural",
    "SENPAI": "en-US-JennyNeural",
    "GENZ": "en-US-ChristopherNeural",
    "FRIDAY": "en-IE-EmilyNeural",
    "REFLECTIVE": "en-US-GuyNeural",
    "SUNDAY": "en-US-AriaNeural",
}


class TTSEngine:
    """Headless neural text-to-speech engine using Edge-TTS with PyAudio in-memory streaming."""

    def __init__(self):
        self.is_speaking = False
        self._current_stream = None
        self._pyaudio_instance = None
        if EDGE_TTS_AVAILABLE:
            try:
                self._pyaudio_instance = pyaudio.PyAudio()
            except Exception as e:
                logger.warning(f"Failed to initialize PyAudio in TTSEngine: {e}")

    async def speak(self, text: str, persona_mode: str = "SUNDAY") -> None:
        """Convert text to speech and play headlessly with barge-in cancellation."""
        if not text or not text.strip():
            return

        logger.info(f"Speaking [{persona_mode}]: {text}")
        self.is_speaking = True

        if not EDGE_TTS_AVAILABLE or not self._pyaudio_instance:
            print(f"[{persona_mode} Voice]: {text}")
            await asyncio.sleep(0.5)
            self.is_speaking = False
            return

        try:
            # Select appropriate voice for active persona
            voice = PERSONA_VOICES.get(persona_mode.upper(), "en-US-AriaNeural")
            comm = edge_tts.Communicate(text, voice)

            # Stream audio chunks in memory
            mp3_bytes = bytearray()
            async for chunk in comm.stream():
                if not self.is_speaking:
                    return
                if chunk["type"] == "audio":
                    mp3_bytes.extend(chunk["data"])

            if not mp3_bytes or not self.is_speaking:
                return

            # Decode MP3 in memory using PyAV and play via PyAudio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._play_audio_bytes, bytes(mp3_bytes))

        except Exception as e:
            logger.error(f"TTS playback error: {e}")
            print(f"[{persona_mode} Voice]: {text}")
        finally:
            self.is_speaking = False

    def _play_audio_bytes(self, data: bytes) -> None:
        """Decode and play audio bytes synchronously in worker thread."""
        try:
            container = av.open(io.BytesIO(data))
            stream = container.streams.audio[0]
            resampler = av.AudioResampler(format="s16", layout="mono", rate=stream.rate)

            out_stream = self._pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=stream.rate,
                output=True,
            )
            self._current_stream = out_stream

            for frame in container.decode(stream):
                if not self.is_speaking:
                    break
                for resampled in resampler.resample(frame):
                    if not self.is_speaking:
                        break
                    out_stream.write(resampled.to_ndarray().tobytes())

            out_stream.stop_stream()
            out_stream.close()
            self._current_stream = None

        except Exception as e:
            logger.debug(f"Audio chunk decode/play error: {e}")

    def stop_speaking(self) -> None:
        """Immediate barge-in cancellation: stop audio output stream."""
        self.is_speaking = False
        if self._current_stream:
            try:
                self._current_stream.stop_stream()
                self._current_stream.close()
            except Exception:
                pass
            self._current_stream = None

    def cleanup(self) -> None:
        """Terminate TTS resources."""
        self.stop_speaking()
        if self._pyaudio_instance:
            try:
                self._pyaudio_instance.terminate()
            except Exception:
                pass
            self._pyaudio_instance = None
