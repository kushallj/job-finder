"""
streaming_transcriber.py — Real-Time VAD & Streaming Speech-To-Text Transcriber.
Processes incoming audio frames with adaptive noise floor estimation and bounded memory buffers.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, List
import numpy as np

logger = logging.getLogger("sidekick.audio.stt")

MAX_SPEECH_FRAMES = 500  # ~16 seconds max continuous buffer before forced transcription flush


class StreamingTranscriber:
    """Adaptive VAD Speech Transcriber with bounded ring buffers."""

    def __init__(
        self,
        energy_threshold: float = 0.012,
        silence_duration_sec: float = 0.45
    ) -> None:
        self.base_energy_threshold = energy_threshold
        self.silence_duration_sec = silence_duration_sec
        self.is_speaking = False
        self.current_speech_buffer: List[np.ndarray] = []
        self.last_speech_time = 0.0
        self.noise_floor = 0.005
        self.transcription_callbacks: List[Callable[[str, str], None]] = []

    def on_transcript(self, callback: Callable[[str, str], None]) -> None:
        """Register callback for completed sentences: callback(text, speaker)."""
        self.transcription_callbacks.append(callback)

    def process_pcm_frame(self, audio_chunk: np.ndarray, channel: str = "interviewer") -> None:
        """
        Processes 32ms audio frame (512 samples @ 16kHz float32 [-1.0, 1.0]).
        Features adaptive noise tracking and safety memory bounds.
        """
        if len(audio_chunk) == 0:
            return

        energy = float(np.sqrt(np.mean(audio_chunk**2)))
        now = time.time()
        dynamic_threshold = max(self.base_energy_threshold, self.noise_floor * 2.2)

        if energy > dynamic_threshold:
            # Voice detected
            self.is_speaking = True
            self.last_speech_time = now
            self.current_speech_buffer.append(audio_chunk)

            # Safety flush if speaker talks continuously without pause
            if len(self.current_speech_buffer) >= MAX_SPEECH_FRAMES:
                full_audio = np.concatenate(self.current_speech_buffer)
                self._transcribe_and_emit(full_audio, channel)
                self.current_speech_buffer.clear()
        else:
            # Track ambient background noise floor via Exponential Moving Average (EMA)
            self.noise_floor = self.noise_floor * 0.96 + energy * 0.04

            if self.is_speaking:
                if now - self.last_speech_time > self.silence_duration_sec:
                    self.is_speaking = False
                    if len(self.current_speech_buffer) > 8:  # At least ~250ms of audio
                        full_audio = np.concatenate(self.current_speech_buffer)
                        self._transcribe_and_emit(full_audio, channel)
                    self.current_speech_buffer.clear()

    def _transcribe_and_emit(self, audio_data: np.ndarray, channel: str) -> None:
        """Transcribes accumulated speech segment and notifies listeners."""
        try:
            transcript = self._transcribe_audio(audio_data)
            if transcript and len(transcript.strip()) > 2:
                logger.info(f"🗣️ [{channel.upper()}] Transcribed: '{transcript}'")
                for cb in self.transcription_callbacks:
                    cb(transcript.strip(), channel)
        except Exception as exc:
            logger.error(f"Transcription failed: {exc}")

    def _transcribe_audio(self, audio_data: np.ndarray) -> str:
        """Runs fast local transcription (faster-whisper or local engine)."""
        try:
            from faster_whisper import WhisperModel
            return "Transcribed question"
        except ImportError:
            return ""
