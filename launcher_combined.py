#!/usr/bin/env python3
"""
Combined Launcher - Starts Dashboard + API Server
API Server handles UptimeRobot pings and Telegram polling
"""

import subprocess
import sys
import os
import time
import signal
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = "/Users/a2519/.pyenv/shims/python3"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8938903628:AAGCXL5AgWsymcZAGmOOoe0d2ZHCMPHpzbM")

processes = []

def signal_handler(sig, frame):
    print("\n🛑 Shutting down all processes...")
    for p in processes:
        p.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def start_component(name, script, args=None):
    """Start a component process"""
    cmd = [PYTHON, script]
    if args:
        cmd.extend(args)

    print(f"🚀 Starting {name}...")
    p = subprocess.Popen(
        cmd,
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(p)
    print(f"✅ {name} started (PID: {p.pid})")
    return p

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║      🌏 PHILIPPINE DISASTER MONITOR - COMBINED LAUNCHER     ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Start API Server (handles /health for UptimeRobot + Telegram polling)
    start_component("API Server (Flask)", "api_server.py")

    # Small delay
    time.sleep(1)

    # Start Dashboard
    print("🚀 Starting Dashboard (Streamlit)...")
    dashboard_proc = subprocess.Popen(
        [PYTHON, "-m", "streamlit", "run", "dashboard.py",
         "--server.port", "8501", "--server.headless", "true"],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(dashboard_proc)

    print("""
╔══════════════════════════════════════════════════════════════╗
║  ✅ All systems started!                                      ║
║                                                              ║
║  Dashboard:  http://localhost:8501                            ║
║  API Server: http://localhost:5000                           ║
║                                                              ║
║  UptimeRobot should ping: http://localhost:5000/health      ║
║                                                              ║
║  Press Ctrl+C to stop all services                           ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Monitor outputs
    try:
        while True:
            for p in processes:
                if p.poll() is not None:
                    idx = processes.index(p)
                    print(f"⚠️ Process ended unexpectedly")
                    break
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()