"""
Health Check Endpoint for UptimeRobot
Keeps the app alive AND checks Telegram updates
Runs every time UptimeRobot pings the /health endpoint
"""

import streamlit as st
import requests
import json
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_telegram_updates(bot_token: str):
    """Poll Telegram for any pending /sos or /safe updates"""
    if not bot_token:
        return {"checked": False, "reason": "no token"}

    try:
        from bot_handler import handle_command, save_statuses, load_statuses

        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        params = {"timeout": 1, "allowed_updates": ["message"]}

        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if not data.get("ok"):
            return {"checked": True, "updates": 0, "processed": 0}

        updates = data.get("result", [])
        processed = 0

        for update in updates:
            message = update.get("message")
            if not message:
                continue

            chat_id = str(message["chat"]["id"])
            name = f"{message['chat'].get('first_name', '')} {message['chat'].get('last_name', '')}".strip() or "Unknown"
            username = message['chat'].get('username', '')
            text = message.get("text", "")

            if text.startswith('/sos'):
                handle_command(bot_token, chat_id, '/sos', name, username)
                processed += 1
            elif text.startswith('/safe'):
                handle_command(bot_token, chat_id, '/safe', name, username)
                processed += 1

        return {"checked": True, "updates": len(updates), "processed": processed}

    except Exception as e:
        return {"checked": False, "error": str(e)}

def render_health_check():
    """Render the health check response"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "8938903628:AAGCXL5AgWsymcZAGmOOoe0d2ZHCMPHpzbM")

    # Check Telegram updates
    result = check_telegram_updates(bot_token)

    # Load current statuses
    try:
        from bot_handler import get_all_statuses
        statuses = get_all_statuses()
        sos_count = sum(1 for s in statuses.values() if s.get('status') == 'SOS')
        safe_count = sum(1 for s in statuses.values() if s.get('status') == 'SAFE')
    except:
        statuses = {}
        sos_count = safe_count = 0

    # Return JSON for health checks
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "telegram": result,
        "status_summary": {
            "sos": sos_count,
            "safe": safe_count,
            "total": len(statuses)
        }
    }

# This runs on EVERY ping from UptimeRobot
if __name__ == "__main__":
    result = render_health_check()
    print(json.dumps(result, indent=2, default=str))