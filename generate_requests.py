#!/usr/bin/env python3
"""
generate_requests.py
--------------------
Hits the transcription service endpoints with real MeetingBank samples
and synthetic audio data. Simulates realistic traffic patterns.

Usage:
    python3 generate_requests.py --endpoint http://<service-ip>:8000 --rate 2 --duration 300

Environment:
    SERVICE_ENDPOINT  — transcription API base URL
    REQUEST_RATE      — requests per minute (default: 5)
    DURATION_SEC      — how long to run (default: 300)
"""

import argparse
import io
import json
import os
import random
import time
import wave
from datetime import datetime

import numpy as np
import requests

# ── Synthetic audio generation ────────────────────────────────────────────────

SAMPLE_RATE = 16000
SPEAKERS = ["Speaker_A", "Speaker_B", "Speaker_C", "Speaker_D"]

# Real-ish meeting phrases for synthetic transcripts
MEETING_PHRASES = [
    "I move that we approve the budget for the next quarter.",
    "The motion is seconded. All in favor?",
    "We need to table this discussion until the next meeting.",
    "Can we have a vote on the proposed amendment?",
    "I'd like to open the floor for public comment.",
    "The council will now consider item three on the agenda.",
    "We are adjourned. Thank you all for attending.",
    "I have a question regarding the infrastructure proposal.",
    "The committee recommends approval of the resolution.",
    "Let the record show that the motion passed unanimously.",
    "We need to revisit the zoning ordinance from last session.",
    "Public works has submitted their quarterly report.",
    "I'd like to yield my remaining time to the councilmember.",
    "The budget allocation for this project needs further review.",
    "Can we get a clarification on the timeline for implementation?",
]


def generate_sine_audio(duration_sec=3.0, freq=220.0, noise_level=0.05):
    """Generate a sine wave with noise — mimics speech-like audio."""
    t = np.linspace(0, duration_sec, int(SAMPLE_RATE * duration_sec))
    # Mix a few harmonics to sound more speech-like
    audio = (
        0.5 * np.sin(2 * np.pi * freq * t) +
        0.3 * np.sin(2 * np.pi * freq * 2 * t) +
        0.1 * np.sin(2 * np.pi * freq * 3 * t)
    )
    # Add noise
    audio += np.random.randn(len(t)) * noise_level
    # Normalize
    audio = audio / np.max(np.abs(audio)) * 0.8
    return audio.astype(np.float32)


def generate_synthetic_speech(duration_sec=None):
    """Generate synthetic speech-like audio of random duration."""
    if duration_sec is None:
        duration_sec = random.uniform(2.0, 8.0)

    # Random fundamental frequency (male: 85-180Hz, female: 165-255Hz)
    freq = random.uniform(85, 255)
    noise = random.uniform(0.02, 0.08)
    return generate_sine_audio(duration_sec, freq, noise), SAMPLE_RATE


def audio_to_wav_bytes(audio, sr):
    """Convert numpy audio array to WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        pcm = (audio * 32767).astype(np.int16)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def generate_synthetic_transcript():
    """Generate a realistic synthetic meeting transcript."""
    n_turns = random.randint(3, 8)
    turns = []
    for _ in range(n_turns):
        speaker = random.choice(SPEAKERS)
        phrase = random.choice(MEETING_PHRASES)
        # Small perturbation
        if random.random() < 0.3:
            phrase = phrase.lower()
        turns.append({"speaker": speaker, "text": phrase})
    return turns


# ── API client ────────────────────────────────────────────────────────────────

class TranscriptionClient:
    def __init__(self, endpoint):
        self.endpoint = endpoint.rstrip("/")
        self.session = requests.Session()
        self.stats = {
            "total": 0, "success": 0, "failed": 0,
            "total_latency_ms": 0.0
        }

    def health_check(self):
        """Check if service is up."""
        try:
            r = self.session.get(f"{self.endpoint}/health", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def send_audio(self, audio_bytes, meeting_id, expected_transcript=None):
        """POST audio file to /transcribe endpoint."""
        t0 = time.time()
        try:
            files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
            data = {"meeting_id": meeting_id}
            if expected_transcript:
                data["reference_transcript"] = json.dumps(expected_transcript)

            r = self.session.post(
                f"{self.endpoint}/transcribe",
                files=files,
                data=data,
                timeout=30
            )
            latency_ms = (time.time() - t0) * 1000
            self.stats["total"] += 1
            self.stats["total_latency_ms"] += latency_ms

            if r.status_code == 200:
                self.stats["success"] += 1
                return True, r.json(), latency_ms
            else:
                self.stats["failed"] += 1
                return False, r.text, latency_ms

        except requests.exceptions.ConnectionError:
            self.stats["total"] += 1
            self.stats["failed"] += 1
            return False, "Connection refused — is the service running?", 0

        except Exception as e:
            self.stats["total"] += 1
            self.stats["failed"] += 1
            return False, str(e), 0

    def send_text(self, transcript_turns, meeting_id):
        """POST synthetic transcript to /evaluate endpoint."""
        t0 = time.time()
        try:
            payload = {
                "meeting_id": meeting_id,
                "transcript": transcript_turns,
                "synthetic": True,
            }
            r = self.session.post(
                f"{self.endpoint}/evaluate",
                json=payload,
                timeout=10
            )
            latency_ms = (time.time() - t0) * 1000
            self.stats["total"] += 1
            self.stats["total_latency_ms"] += latency_ms

            if r.status_code == 200:
                self.stats["success"] += 1
                return True, r.json(), latency_ms
            else:
                self.stats["failed"] += 1
                return False, r.text, latency_ms

        except requests.exceptions.ConnectionError:
            self.stats["total"] += 1
            self.stats["failed"] += 1
            return False, "Connection refused — is the service running?", 0

        except Exception as e:
            self.stats["total"] += 1
            self.stats["failed"] += 1
            return False, str(e), 0

    def print_stats(self):
        avg_latency = (
            self.stats["total_latency_ms"] / self.stats["total"]
            if self.stats["total"] > 0 else 0
        )
        print(f"\n{'─'*50}")
        print(f"  STATS")
        print(f"{'─'*50}")
        print(f"  Total requests : {self.stats['total']}")
        print(f"  Successful     : {self.stats['success']}")
        print(f"  Failed         : {self.stats['failed']}")
        print(f"  Avg latency    : {avg_latency:.1f}ms")
        print(f"{'─'*50}")


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_generator(endpoint, rate_per_min, duration_sec, mode="mixed"):
    """
    Main generator loop.

    mode: 'audio'  — only send audio requests
          'text'   — only send transcript requests
          'mixed'  — alternate between audio and text (default)
    """
    client = TranscriptionClient(endpoint)
    interval = 60.0 / rate_per_min
    start_time = time.time()
    request_num = 0

    print(f"{'='*50}")
    print(f"  TRANSCRIPTION SERVICE DATA GENERATOR")
    print(f"{'='*50}")
    print(f"  Endpoint  : {endpoint}")
    print(f"  Rate      : {rate_per_min} req/min")
    print(f"  Duration  : {duration_sec}s")
    print(f"  Mode      : {mode}")
    print(f"{'='*50}\n")

    # Health check
    print("Checking service health...")
    if client.health_check():
        print("  ✓ Service is up\n")
    else:
        print("  ✗ Service not responding — sending requests anyway (will show as failed)\n")

    while time.time() - start_time < duration_sec:
        request_num += 1
        meeting_id = f"synth_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{request_num:04d}"
        elapsed = time.time() - start_time
        remaining = duration_sec - elapsed

        print(f"[{elapsed:.0f}s] Request #{request_num} — {meeting_id}")

        # Decide request type
        if mode == "audio" or (mode == "mixed" and request_num % 2 == 1):
            # Send synthetic audio
            duration_audio = random.uniform(2.0, 6.0)
            audio, sr = generate_synthetic_speech(duration_audio)
            wav_bytes = audio_to_wav_bytes(audio, sr)
            transcript = generate_synthetic_transcript()

            print(f"  Type    : audio ({duration_audio:.1f}s, {len(wav_bytes)/1024:.1f}KB)")
            ok, result, latency = client.send_audio(wav_bytes, meeting_id, transcript)

        else:
            # Send synthetic transcript text
            turns = generate_synthetic_transcript()
            print(f"  Type    : text ({len(turns)} turns)")
            ok, result, latency = client.send_text(turns, meeting_id)

        if ok:
            print(f"  Status  : ✓ success ({latency:.0f}ms)")
            if isinstance(result, dict):
                if "transcript" in result:
                    preview = str(result["transcript"])[:80]
                    print(f"  Result  : {preview}...")
                elif "wer" in result:
                    print(f"  WER     : {result['wer']:.3f}")
        else:
            print(f"  Status  : ✗ failed — {str(result)[:100]}")

        # Sleep until next request
        time.sleep(interval)

    client.print_stats()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Data generator for transcription service"
    )
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("SERVICE_ENDPOINT", "http://localhost:8000"),
        help="Transcription service base URL"
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=float(os.environ.get("REQUEST_RATE", "5")),
        help="Requests per minute"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=int(os.environ.get("DURATION_SEC", "300")),
        help="How long to run in seconds"
    )
    parser.add_argument(
        "--mode",
        choices=["audio", "text", "mixed"],
        default="mixed",
        help="Type of requests to send"
    )
    args = parser.parse_args()
    run_generator(args.endpoint, args.rate, args.duration, args.mode)
