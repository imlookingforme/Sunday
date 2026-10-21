import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pyaudio
    import numpy as np
    from openwakeword.model import Model
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False


class WakeWordDetector:
    """Detects spoken wake words (e.g. 'Hey Sunday', 'Hey Jarvis') using openWakeWord & VAD."""

    def __init__(self, wake_word: str = "hey_sunday", sensitivity: float = 0.5):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self.is_listening = False
        self.model = None
        self.audio = None
        self.stream = None
        self.active_model_name = None

        if OPENWAKEWORD_AVAILABLE:
            try:
                # Map friendly alias to downloaded ONNX model
                model_target = "hey_jarvis"
                if self.wake_word in ["alexa", "hey_mycroft", "timer", "weather"]:
                    model_target = self.wake_word

                self.model = Model(wakeword_models=[model_target], inference_framework="onnx")
                self.active_model_name = model_target
                self.audio = pyaudio.PyAudio()
                logger.info(f"WakeWordDetector initialized with model [{model_target}] for keyword '{self.wake_word}'")
            except Exception as e:
                logger.warning(f"Failed to initialize openwakeword model: {e}")
                self.model = None

    async def wait_for_wake_word(self) -> bool:
        """Listen asynchronously on microphone until wake word or hotword is spoken."""
        if not OPENWAKEWORD_AVAILABLE or not self.audio or not self.model:
            await asyncio.sleep(1)
            return False

        self.is_listening = True
        stream = None
        try:
            loop = asyncio.get_event_loop()
            stream = await loop.run_in_executor(
                None,
                lambda: self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1280
                )
            )
            self.stream = stream

            logger.info(f"Listening for wake word: '{self.wake_word}' (or 'Hey Jarvis')...")
            
            while self.is_listening:
                data = await loop.run_in_executor(
                    None,
                    lambda: stream.read(1280, exception_on_overflow=False)
                )
                if not data:
                    await asyncio.sleep(0.01)
                    continue

                audio_data = np.frombuffer(data, dtype=np.int16)
                prediction = self.model.predict(audio_data)

                # Check if the model score exceeds sensitivity
                score = prediction.get(self.active_model_name, 0.0)
                if score > self.sensitivity:
                    logger.info(f"Wake word detected! (score: {score:.3f})")
                    return True

                await asyncio.sleep(0.005)

        except Exception as e:
            logger.error(f"Error in wake word detection: {e}")
            await asyncio.sleep(1)
            return False
        finally:
            self.stop()

        return False

    def stop(self):
        """Stop listening and close stream."""
        self.is_listening = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def cleanup(self):
        """Terminate audio subsystem."""
        self.stop()
        if self.audio:
            try:
                self.audio.terminate()
            except Exception:
                pass
            self.audio = None
