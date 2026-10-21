"""Ambient conversation mode with auto-send on pause (alimaandev/Friday pattern)."""

from datetime import datetime
from typing import AsyncIterator, Optional
import asyncio
import numpy as np


class AmbientMode:
    """Ambient conversation mode with auto-send on speech pause.

    Enables natural back-and-forth conversation by automatically
    sending when the user pauses speaking.
    """

    def __init__(self, silence_threshold: float = 1.0, sample_rate: int = 16000):
        """Initialize ambient mode.

        Args:
            silence_threshold: Seconds of silence before auto-send
            sample_rate: Audio sample rate for silence detection
        """
        self.silence_threshold = silence_threshold
        self.sample_rate = sample_rate
        self.buffer = []
        self.last_speech_time: Optional[datetime] = None
        self.is_speaking = False

    async def process_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        transcribe_callback,
        response_callback
    ) -> Optional[str]:
        """Process audio stream with auto-send on silence.

        Args:
            audio_stream: Async iterator of audio chunks
            transcribe_callback: Async function to transcribe audio
            response_callback: Async function to get response from text

        Returns:
            Response text if auto-sent, None otherwise
        """
        async for chunk in audio_stream:
            if self._is_speech(chunk):
                self.buffer.append(chunk)
                self.last_speech_time = datetime.now()
                self.is_speaking = True
            else:
                # Check for silence threshold
                if (self.last_speech_time and
                    self.is_speaking and
                    (datetime.now() - self.last_speech_time).total_seconds() > self.silence_threshold):
                    # Auto-send
                    audio_data = b"".join(self.buffer)
                    text = await transcribe_callback(audio_data)

                    if text:
                        response = await response_callback(text)
                        self._reset()
                        return response

                    self._reset()

        return None

    def _is_speech(self, audio_chunk: bytes) -> bool:
        """Detect if audio chunk contains speech.

        Uses simple energy-based detection (RMS).
        For production, consider using VAD (Voice Activity Detection).
        """
        if not audio_chunk:
            return False

        # Convert bytes to numpy array
        import numpy as np
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)

        # Calculate RMS (root mean square) energy
        if len(audio_array) == 0:
            return False

        rms = np.sqrt(np.mean(audio_array.astype(float)**2))

        # Threshold for speech detection (adjust based on microphone)
        speech_threshold = 500

        return rms > speech_threshold

    def _reset(self) -> None:
        """Reset buffer and state."""
        self.buffer.clear()
        self.last_speech_time = None
        self.is_speaking = False

    def force_send(
        self,
        transcribe_callback,
        response_callback
    ) -> Optional[str]:
        """Force send current buffer (manual trigger)."""
        if not self.buffer:
            return None

        audio_data = b"".join(self.buffer)
        text = asyncio.run(transcribe_callback(audio_data))

        if text:
            response = asyncio.run(response_callback(text))
            self._reset()
            return response

        self._reset()
        return None

    def set_silence_threshold(self, threshold: float) -> None:
        """Update silence threshold."""
        self.silence_threshold = threshold

    def get_buffer_duration(self) -> float:
        """Get duration of buffered audio in seconds."""
        if not self.buffer:
            return 0.0

        total_bytes = sum(len(chunk) for chunk in self.buffer)
        # Assuming 16-bit PCM (2 bytes per sample)
        total_samples = total_bytes // 2
        return total_samples / self.sample_rate
