"""
Web Server for Philippine Disaster Monitor
Combines Streamlit dashboard with API endpoints for UptimeRobot
"""

from flask import Flask, redirect, jsonify, request
import threading
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

# Global status store (shared with Streamlit via files)
STATUS_FILE = os.path.join(os.path.dirname(__file__), "status.json")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

# ==================== BOT HANDLER LOGIC ====================

def load_json(filepath, default=None):
    """Load JSON file safely"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except:
        pass
    return default if default is not None else {}

def save_json(filepath, data):
    """Save JSON file safely"""
    import json
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except:
        return False

def check_and_process_telegram(bot_token):
    """Poll Telegram for updates and process commands"""
    import requests
    from datetime import datetime

    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        params = {"timeout": 1, "allowed_updates": ["message"]}

        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if not data.get("ok"):
            return {"success": False, "reason": "API error"}

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

            # Load current data
            statuses = load_json(STATUS_FILE, {})
            users = load_json(USERS_FILE, {})

            # Register/update user
            users[chat_id] = {
                "chat_id": chat_id,
                "name": name,
                "username": username,
                "status": "UNKNOWN",
                "last_seen": datetime.now().isoformat()
            }

            # Process command
            if text.startswith('/sos'):
                statuses[chat_id] = {
                    "name": name,
                    "username": username,
                    "status": "SOS",
                    "timestamp": datetime.now().isoformat(),
                    "chat_id": chat_id
                }
                users[chat_id]["status"] = "SOS"
                users[chat_id]["status_timestamp"] = datetime.now().isoformat()
                processed += 1

                # Send confirmation
                send_telegram_message(bot_token, chat_id, "🆘 SOS registered! Help is on the way. Stay safe.")

            elif text.startswith('/safe'):
                statuses[chat_id] = {
                    "name": name,
                    "username": username,
                    "status": "SAFE",
                    "timestamp": datetime.now().isoformat(),
                    "chat_id": chat_id
                }
                users[chat_id]["status"] = "SAFE"
                users[chat_id]["status_timestamp"] = datetime.now().isoformat()
                processed += 1

                # Send confirmation
                send_telegram_message(bot_token, chat_id, "✅ You're marked as SAFE. Glad you're okay!")

        # Save updated data
        if processed > 0:
            save_json(STATUS_FILE, statuses)
            save_json(USERS_FILE, users)

        return {"success": True, "updates_checked": len(updates), "commands_processed": processed}

    except Exception as e:
        return {"success": False, "error": str(e)}

def send_telegram_message(bot_token, chat_id, text):
    """Send a Telegram message"""
    import requests
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
    except:
        pass

# ==================== WEB ENDPOINTS ====================

@app.route('/')
def index():
    """Redirect to Streamlit dashboard"""
    return redirect('/dashboard', code=302)

@app.route('/dashboard')
def dashboard():
    """Proxy to Streamlit dashboard"""
    # For UptimeRobot, we'll show a simple status page
    # In production, you'd use nginx reverse proxy to Streamlit
    return """
    <html><head><title>PhilDisaster Monitor</title></head>
    <body>
    <h1>🌏 Philippine Disaster Monitor</h1>
    <p>Dashboard is running. Open the Streamlit app directly.</p>
    <p><a href="/health">Health Check</a> | <a href="/status">Status API</a></p>
    </body></html>
    """

@app.route('/health')
def health():
    """
    Health check endpoint for UptimeRobot
    Also processes Telegram commands on each ping
    """
    import json
    from datetime import datetime

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "8938903628:AAGCXL5AgWsymcZAGmOOoe0d2ZHCMPHpzbM")

    # Process any pending Telegram commands
    telegram_result = check_and_process_telegram(bot_token)

    # Get current status
    statuses = load_json(STATUS_FILE, {})
    users = load_json(USERS_FILE, {})

    sos_count = sum(1 for s in statuses.values() if s.get('status') == 'SOS')
    safe_count = sum(1 for s in statuses.values() if s.get('status') == 'SAFE')

    result = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "PhilDisaster Monitor",
        "telegram": telegram_result,
        "people_status": {
            "sos": sos_count,
            "safe": safe_count,
            "total": len(statuses)
        },
        "users_registered": len(users)
    }

    return jsonify(result)

@app.route('/status')
def status():
    """Get current status summary"""
    from datetime import datetime

    statuses = load_json(STATUS_FILE, {})
    users = load_json(USERS_FILE, {})

    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "statuses": statuses,
        "users": len(users),
        "sos_count": sum(1 for s in statuses.values() if s.get('status') == 'SOS'),
        "safe_count": sum(1 for s in statuses.values() if s.get('status') == 'SAFE')
    })

@app.route('/broadcast', methods=['POST'])
def broadcast():
    """Broadcast a message to all registered users"""
    import json
    from datetime import datetime

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    message = request.json.get('message', '')

    if not message:
        return jsonify({"error": "No message provided"}), 400

    if not bot_token:
        return jsonify({"error": "No bot token configured"}), 500

    users = load_json(USERS_FILE, {})
    sent = []
    failed = []

    for user_id, user_data in users.items():
        chat_id = user_data.get('chat_id')
        if not chat_id:
            continue

        try:
            import requests
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }, timeout=10)

            if resp.json().get("ok"):
                sent.append(chat_id)
            else:
                failed.append({"chat_id": chat_id, "error": resp.json().get("description")})
        except Exception as e:
            failed.append({"chat_id": chat_id, "error": str(e)})

    return jsonify({
        "sent": sent,
        "failed": failed,
        "total": len(users)
    })

# ==================== MAIN ====================

if __name__ == "__main__":
    import json

    print("""
╔══════════════════════════════════════════════════════════════╗
║         🌏 Philippine Disaster Monitor - API Server          ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Get port from environment (Render sets PORT)
    port = int(os.environ.get("PORT", 5000))

    print(f"🚀 Starting server on port {port}...")
    print(f"📍 Endpoints:")
    print(f"   /          - Redirect to dashboard")
    print(f"   /health    - Health check + Telegram polling")
    print(f"   /status    - Current status summary")
    print(f"   /broadcast - Send message to all users")
    print()

    # Run the Flask server
    app.run(host="0.0.0.0", port=port, debug=False)