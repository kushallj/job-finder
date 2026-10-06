"""
native_mic_listener.py — Pro-Grade Real-Time Speech Recognition with Adaptive VAD & Rolling Turn Aggregation.
Captures continuous 16kHz audio from macOS Core Audio without cutting off long questions or pausing.
"""
import sys
import os
import time
import json
import threading
import queue
import urllib.request
import numpy as np
import sounddevice as sd
import speech_recognition as sr

SAMPLE_RATE = 16000
BLOCK_SIZE = int(SAMPLE_RATE * 0.05)  # 50ms blocks (800 samples)
SILENCE_TIMEOUT_SEC = 4.0             # Allow up to 4.0 seconds of thinking/breathing pause before completing an utterance
MIN_PHRASE_DURATION_SEC = 0.8         # Ignore clicks or sub-second taps
MAX_PHRASE_DURATION_SEC = 25.0        # Max phrase length for a single question turn
BACKEND_FEED_URL = "http://127.0.0.1:8000/api/sidekick/feed-speech"

# Conversational filler filter to prevent wiping active hints
FILLER_PHRASES = frozenset({
    "yes", "no", "yeah", "okay", "ok", "alright", "right", "uh", "um", "ah",
    "so", "well", "like", "let me see", "can you hear me", "hello", "thank you"
})


class ConversationSessionAggregator:
    """Maintains a rolling 45-second sliding window of conversation turns for full question context."""
    def __init__(self, max_history_sec=45):
        self.max_history_sec = max_history_sec
        self.history = []  # [(timestamp, text)]
        self._lock = threading.Lock()

    def add_phrase(self, text: str):
        now = time.time()
        with self._lock:
            self.history.append((now, text))
            self._prune(now)

    def get_accumulated_context(self) -> str:
        now = time.time()
        with self._lock:
            self._prune(now)
            return " ".join(t for _, t in self.history).strip()

    def _prune(self, now: float):
        self.history = [(t, text) for t, text in self.history if (now - t) <= self.max_history_sec]


session_aggregator = ConversationSessionAggregator()


def post_to_backend(phrase: str, accumulated_context: str):
    try:
        data = json.dumps({
            "transcript": phrase,
            "accumulated_context": accumulated_context
        }).encode("utf-8")
        req = urllib.request.Request(
            BACKEND_FEED_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            pass
        print(f"🎯 [Copilot Live VAD] Question Captured:\n   Current: '{phrase}'\n   Context: '{accumulated_context}'\n", flush=True)
    except Exception as exc:
        print(f"⚠️ [Copilot Live VAD] Feed failed: {exc}", flush=True)


class RealtimeVADTranscriber:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 250
        self.recognizer.dynamic_energy_threshold = True
        self.running = True

        # VAD State
        self.noise_floor = 150.0
        self.is_speaking = False
        self.speech_start_time = 0.0
        self.last_speech_time = 0.0
        self.collected_frames = []

    def audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback from CoreAudio (every 50ms)."""
        if status:
            pass
        self.audio_queue.put(indata.copy())

    def process_audio_loop(self):
        print(f"🎙️ [Copilot Live VAD] Continuous Listening Online on macOS Core Audio (16kHz Mono, {SILENCE_TIMEOUT_SEC}s Pause Tolerance)...", flush=True)

        while self.running:
            try:
                frame = self.audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            # Compute RMS energy
            pcm = frame.flatten()
            rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)))
            now = time.time()

            # Dynamic noise floor adaptation during silence
            if not self.is_speaking:
                self.noise_floor = 0.95 * self.noise_floor + 0.05 * max(50.0, rms)
                speech_threshold = max(250.0, self.noise_floor * 2.8)
            else:
                speech_threshold = max(200.0, self.noise_floor * 2.0)

            # Speech onset detection
            if rms > speech_threshold:
                if not self.is_speaking:
                    self.is_speaking = True
                    self.speech_start_time = now
                    self.collected_frames = []
                self.last_speech_time = now
                self.collected_frames.append(pcm)
            elif self.is_speaking:
                # In speech turn, but current frame is quiet (pause/breathing)
                self.collected_frames.append(pcm)
                pause_duration = now - self.last_speech_time
                phrase_duration = now - self.speech_start_time

                # Check if turn completed after 4.0s pause OR exceeded max phrase duration
                if pause_duration >= SILENCE_TIMEOUT_SEC or phrase_duration >= MAX_PHRASE_DURATION_SEC:
                    self.is_speaking = False
                    total_dur = len(self.collected_frames) * 0.05
                    if total_dur >= MIN_PHRASE_DURATION_SEC:
                        frames_to_transcribe = list(self.collected_frames)
                        threading.Thread(target=self._transcribe_and_feed, args=(frames_to_transcribe,), daemon=True).start()
                    self.collected_frames = []

    def _transcribe_and_feed(self, frames):
        try:
            full_pcm = np.concatenate(frames).astype(np.int16)
            audio_data = sr.AudioData(full_pcm.tobytes(), sample_rate=SAMPLE_RATE, sample_width=2)
            
            transcript = self.recognizer.recognize_google(audio_data).strip()
            if not transcript or len(transcript) < 2:
                return

            lower = transcript.lower().strip()
            # Ignore standalone filler words that don't constitute a question
            if lower in FILLER_PHRASES and len(lower.split()) <= 2:
                print(f"ℹ️ [Copilot Live VAD] Conversational pause/filler ignored: '{transcript}'", flush=True)
                return

            session_aggregator.add_phrase(transcript)
            accumulated = session_aggregator.get_accumulated_context()
            post_to_backend(transcript, accumulated)

        except sr.UnknownValueError:
            # Ambient noise or inaudible mumble
            pass
        except Exception as err:
            pass

    def start(self):
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=BLOCK_SIZE,
                callback=self.audio_callback
            ):
                self.process_audio_loop()
        except Exception as e:
            print(f"❌ [Copilot Live VAD] CoreAudio stream error: {e}", flush=True)


if __name__ == "__main__":
    transcriber = RealtimeVADTranscriber()
    transcriber.start()
