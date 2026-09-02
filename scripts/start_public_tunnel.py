#!/usr/bin/env python3
"""
NetWatch Persistent Public Tunnel Manager
Maintains an active, self-healing reverse SSH tunnel to serveo.net
with automated keep-alive and reconnection logic.
"""

import subprocess
import time
import sys

def run_tunnel():
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3",
        "-o", "ExitOnForwardFailure=yes",
        "-R", "80:127.0.0.1:8000",
        "serveo.net"
    ]

    print("Starting persistent NetWatch public gateway...")

    while True:
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in iter(process.stdout.readline, ''):
                print(line, end='', flush=True)

            process.wait()
            print("\nTunnel disconnected. Reconnecting in 3 seconds...")
            time.sleep(3)

        except KeyboardInterrupt:
            print("\nTunnel terminated by user.")
            sys.exit(0)
        except Exception as e:
            print(f"\nTunnel error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    run_tunnel()
