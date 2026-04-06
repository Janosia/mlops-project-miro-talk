#!/usr/bin/env python3
"""
run_demo.py
-----------
Launches the mock service + data generator together for demo/video purposes.
Runs the mock service in the background, then starts the generator.

Usage:
    python3 run_demo.py

This is what you run when recording the demo video.
"""

import subprocess
import sys
import time
import os

PORT = 8000
ENDPOINT = f"http://localhost:{PORT}"
RATE = 4          # requests per minute (every 15 seconds — visible in video)
DURATION = 180    # 3 minutes of runtime for the video


def main():
    print("=" * 55)
    print("  TRANSCRIPTION SERVICE — DATA GENERATOR DEMO")
    print("=" * 55)
    print()

    # Step 1 — start mock service in background
    print("Step 1: Starting mock transcription service...")
    service = subprocess.Popen(
        [sys.executable, "scripts/mock_service.py", "--port", str(PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(1.5)  # wait for service to start

    if service.poll() is not None:
        print("  ✗ Mock service failed to start")
        sys.exit(1)
    print(f"  ✓ Mock service running on {ENDPOINT}\n")

    # Step 2 — run data generator
    print("Step 2: Starting data generator...")
    print(f"  Rate    : {RATE} requests/min")
    print(f"  Duration: {DURATION}s (~{DURATION//60} min)")
    print(f"  Mode    : mixed (audio + text)\n")
    time.sleep(1)

    try:
        generator = subprocess.run(
            [
                sys.executable, "scripts/generate_requests.py",
                "--endpoint", ENDPOINT,
                "--rate", str(RATE),
                "--duration", str(DURATION),
                "--mode", "mixed",
            ]
        )
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    finally:
        print("\nStopping mock service...")
        service.terminate()
        service.wait()
        print("Done.")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
