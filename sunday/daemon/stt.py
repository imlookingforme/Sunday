import asyncio
import logging
import os
import tempfile
import wave
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pyaudio
    import webrtcvad
    from faster_whisper import WhisperModel
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False


class STTEngine:
    """Real-time Speech-to-Text engine using faster-whisper with WebRTC Voice Activity Detection."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.model = None
        self.audio = None
        self.vad = None

        if STT_AVAILABLE:
            try:
                self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                self.audio = pyaudio.PyAudio()
                self.vad = webrtcvad.Vad(2)  # Moderate aggressiveness
                logger.info(f"STTEngine initialized with model: {self.model_size}")
            except Exception as e:
                logger.warning(f"Failed to initialize STTEngine: {e}")

    async def listen(self, max_duration: float = 12.0, timeout: float = 6.0) -> str:
        """Record microphone input while user is speaking and transcribe to text."""
        if not STT_AVAILABLE or not self.audio or not self.model:
            return ""

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._record_and_transcribe, max_duration, timeout)

    def _record_and_transcribe(self, max_duration: float, timeout: float) -> str:
        stream = None
        temp_filename = None
        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=320
            )

            logger.info("Listening for user speech...")
            frames = []
            silence_frames = 0
            is_speaking = False
            total_frames = 0
            # 320 samples per frame at 16000 Hz = 20ms per frame = 50 frames per second
            max_frames = int(max_duration * 50)
            timeout_frames = int(timeout * 50)

            while total_frames < max_frames:
                data = stream.read(320, exception_on_overflow=False)
                total_frames += 1

                try:
                    is_speech = self.vad.is_speech(data, 16000)
                except Exception:
                    is_speech = False

                if is_speech:
                    if not is_speaking:
                        is_speaking = True
                    silence_frames = 0
                    frames.append(data)
                elif is_speaking:
                    silence_frames += 1
                    frames.append(data)
                    if silence_frames > 45:  # ~0.9 seconds of silence after speech ends
                        break
                else:
                    # Not yet started speaking
                    if total_frames > timeout_frames:
                        # Timed out waiting for speech
                        break

            if not frames:
                return ""

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_filename = temp_wav.name

            with wave.open(temp_filename, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(16000)
                wf.writeframes(b"".join(frames))

            logger.info("Transcribing speech audio with faster-whisper...")
            segments, _ = self.model.transcribe(temp_filename, beam_size=5)
            text = "".join([segment.text for segment in segments]).strip()
            return text

        except Exception as e:
            logger.error(f"Error in STT recording/transcription: {e}")
            return ""
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if temp_filename and os.path.exists(temp_filename):
                try:
                    os.remove(temp_filename)
                except Exception:
                    pass

    def cleanup(self):
        """Terminate PyAudio resources."""
        if self.audio:
            try:
                self.audio.terminate()
            except Exception:
                pass
            self.audio = None
