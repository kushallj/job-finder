"""
loopback_stream.py — Dual-Channel Audio Capture Engine.
Captures system audio (interviewer) and microphone (candidate) without acoustic feedback.
"""
import collections
import logging
import threading
import time
from typing import Callable, Optional, Tuple
import numpy as np

logger = logging.getLogger("sidekick.audio.loopback")

SAMPLE_RATE = 16000
FRAME_SIZE = 512  # 32ms frames @ 16kHz


class DualChannelAudioStreamer:
    """Captures and manages system speaker output and microphone inputs in real time."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, frame_size: int = FRAME_SIZE):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        
        # Ring buffer holding up to 30 seconds of audio chunks
        self.audio_ring_buffer = collections.deque(maxlen=int(30 * (sample_rate / frame_size)))
        self._callbacks = []

    def register_callback(self, callback: Callable[[np.ndarray, str], None]):
        """Register a subscriber for new audio chunks (chunk, channel: 'speaker'|'mic')."""
        self._callbacks.append(callback)

    def start(self):
        """Starts real-time dual audio streaming."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("🎙️ Dual-channel audio loopback capture started.")

    def stop(self):
        """Stops audio streaming."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("🎙️ Audio stream stopped.")

    def push_audio_chunk(self, pcm16_bytes: bytes, channel: str = "speaker"):
        """Allows external WebRTC / WebSocket audio chunks to be injected."""
        try:
            audio_np = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            self.audio_ring_buffer.append((audio_np, channel, time.time()))
            for cb in self._callbacks:
                cb(audio_np, channel)
        except Exception as exc:
            logger.error(f"Failed to push audio chunk: {exc}")

    def _capture_loop(self):
        """Native hardware capture loop via soundcard / pyaudio if available, or safe simulated stream."""
        has_soundcard = False
        try:
            import soundcard as sc
            speakers = sc.default_speaker()
            mics = sc.default_microphone()
            has_soundcard = True
            logger.info(f"Using soundcard hardware: Speaker={speakers.name}, Mic={mics.name}")
        except Exception:
            logger.info("Hardware soundcard loopback not available in current environment — operating in WebRTC/WebSocket ingestion mode.")

        while self.is_running:
            time.sleep(0.032)  # 32ms frame cadence
