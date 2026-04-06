#!/usr/bin/env python3
"""
mock_service.py
---------------
A lightweight mock transcription service for demo purposes.
Simulates realistic API responses so the data generator can be
demonstrated without a real model deployed.

Usage:
    python3 mock_service.py --port 8000

Endpoints:
    GET  /health       — health check
    POST /transcribe   — accepts audio, returns fake transcript + WER
    POST /evaluate     — accepts transcript text, returns fake WER
    GET  /metrics      — returns request counts and avg latency
"""

import json
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
import argparse

MOCK_TRANSCRIPTS = [
    "the council will now consider item three on the agenda",
    "i move that we approve the proposed budget amendment",
    "the motion is seconded all in favor say aye",
    "public comment period is now open please keep remarks to two minutes",
    "the committee recommends approval of the infrastructure resolution",
    "we are adjourned thank you all for your participation today",
    "i yield my remaining time to the councilmember from district four",
    "the zoning variance request has been tabled until next session",
]

# In-memory metrics
METRICS = {
    "total_requests": 0,
    "transcribe_requests": 0,
    "evaluate_requests": 0,
    "total_latency_ms": 0.0,
    "start_time": datetime.utcnow().isoformat(),
}


class MockTranscriptionHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Custom log format
        print(f"  [{datetime.utcnow().strftime('%H:%M:%S')}] {format % args}")

    def send_json(self, status, data):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {
                "status": "healthy",
                "model": "whisper-meetingbank-finetuned-v1",
                "timestamp": datetime.utcnow().isoformat(),
            })

        elif self.path == "/metrics":
            avg_latency = (
                METRICS["total_latency_ms"] / METRICS["total_requests"]
                if METRICS["total_requests"] > 0 else 0
            )
            self.send_json(200, {
                **METRICS,
                "avg_latency_ms": round(avg_latency, 2),
                "uptime_sec": round(
                    (datetime.utcnow() - datetime.fromisoformat(
                        METRICS["start_time"])).total_seconds(), 1
                ),
            })
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        t0 = time.time()
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""

        # Simulate processing time
        time.sleep(random.uniform(0.05, 0.3))

        latency_ms = (time.time() - t0) * 1000
        METRICS["total_requests"] += 1
        METRICS["total_latency_ms"] += latency_ms

        if self.path == "/transcribe":
            METRICS["transcribe_requests"] += 1
            transcript = random.choice(MOCK_TRANSCRIPTS)
            wer = round(random.uniform(0.08, 0.25), 4)
            self.send_json(200, {
                "request_id": f"req_{METRICS['total_requests']:06d}",
                "transcript": transcript,
                "wer": wer,
                "model": "whisper-meetingbank-finetuned-v1",
                "latency_ms": round(latency_ms, 2),
                "timestamp": datetime.utcnow().isoformat(),
            })

        elif self.path == "/evaluate":
            METRICS["evaluate_requests"] += 1
            try:
                payload = json.loads(body)
                turns = payload.get("transcript", [])
            except Exception:
                turns = []
            wer = round(random.uniform(0.05, 0.20), 4)
            cer = round(wer * 0.6, 4)
            self.send_json(200, {
                "request_id": f"req_{METRICS['total_requests']:06d}",
                "wer": wer,
                "cer": cer,
                "turn_count": len(turns),
                "latency_ms": round(latency_ms, 2),
                "timestamp": datetime.utcnow().isoformat(),
            })

        else:
            self.send_json(404, {"error": "Unknown endpoint"})


def run(port):
    server = HTTPServer(("0.0.0.0", port), MockTranscriptionHandler)
    print(f"{'='*50}")
    print(f"  MOCK TRANSCRIPTION SERVICE")
    print(f"{'='*50}")
    print(f"  Listening on http://0.0.0.0:{port}")
    print(f"  Endpoints:")
    print(f"    GET  /health")
    print(f"    POST /transcribe")
    print(f"    POST /evaluate")
    print(f"    GET  /metrics")
    print(f"{'='*50}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down mock service.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    run(args.port)
