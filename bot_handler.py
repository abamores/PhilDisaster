"""
Telegram Bot Handler for SOS/SAFE commands with Broadcast support
Listens for /sos and /safe commands, tracks individual users
Supports broadcasting alerts to all registered users
"""

import requests
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(BASE_DIR, "status.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")

# ==================== USER MANAGEMENT ====================

def load_users() -> dict:
    """Load registered users from file"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users: dict):
    """Save registered users to file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2, default=str)

def register_user(chat_id: str, first_name: str = "", last_name: str = "", username: str = "") -> dict:
    """Register or update a user"""
    users = load_users()
    user_id = str(chat_id)

    users[user_id] = {
        "chat_id": chat_id,
        "name": f"{first_name} {last_name}".strip() or "Unknown",
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "status": "UNKNOWN",
        "status_timestamp": None,
        "registered_at": users.get(user_id, {}).get("registered_at", datetime.now().isoformat()),
        "last_seen": datetime.now().isoformat()
    }

    save_users(users)
    return users[user_id]

def get_registered_users() -> dict:
    """Get all registered users"""
    return load_users()

def get_all_chat_ids() -> list:
    """Get list of all chat IDs"""
    users = load_users()
    return [u.get("chat_id") for u in users.values() if u.get("chat_id")]

# ==================== STATUS MANAGEMENT ====================

def load_statuses() -> dict:
    """Load user statuses from file"""
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_statuses(statuses: dict):
    """Save user statuses to file"""
    with open(STATUS_FILE, 'w') as f:
        json.dump(statuses, f, indent=2, default=str)

def get_all_statuses() -> dict:
    """Get all statuses for dashboard"""
    return load_statuses()

# ==================== COMMAND HANDLING ====================

def handle_command(bot_token: str, chat_id: str, command: str, name: str = "Unknown", username: str = "") -> str:
    """Handle /sos, /safe, /status, /broadcast commands"""
    users = load_users()
    statuses = load_statuses()
    user_id = str(chat_id)

    # Register/update user on any command
    user_info = register_user(chat_id, name.split()[0] if name else "", " ".join(name.split()[1:]) if len(name.split()) > 1 else "", username)

    if command.lower() in ['/sos', 'sos']:
        statuses[user_id] = {
            "name": name,
            "username": username,
            "status": "SOS",
            "timestamp": datetime.now().isoformat(),
            "chat_id": chat_id
        }
        save_statuses(statuses)

        # Update user's status too
        users[user_id]["status"] = "SOS"
        users[user_id]["status_timestamp"] = datetime.now().isoformat()
        save_users(users)

        return "🆘 SOS registered! Help is being coordinated. Stay safe."

    elif command.lower() in ['/safe', '/ok', 'safe']:
        statuses[user_id] = {
            "name": name,
            "username": username,
            "status": "SAFE",
            "timestamp": datetime.now().isoformat(),
            "chat_id": chat_id
        }
        save_statuses(statuses)

        users[user_id]["status"] = "SAFE"
        users[user_id]["status_timestamp"] = datetime.now().isoformat()
        save_users(users)

        return "✅ Status updated to SAFE. Glad you're safe!"

    elif command.lower() in ['/status', '/check']:
        current = statuses.get(user_id, {}).get('status', 'UNKNOWN')
        return f"📍 Your current status: {current}"

    elif command.lower() in ['/list', '/reports']:
        # Admin command - list all statuses
        if not statuses:
            return "No statuses registered yet."

        msg = "📋 Current statuses:\n\n"
        for uid, data in sorted(statuses.items(), key=lambda x: x[1].get('timestamp', ''), reverse=True):
            status_emoji = "🟢" if data['status'] == 'SAFE' else "🔴" if data['status'] == 'SOS' else "⚪"
            timestamp = data.get('timestamp', '')[:16]
            msg += f"{status_emoji} {data.get('name', 'Unknown')} (@{data.get('username', 'N/A')}): {data['status']} ({timestamp})\n"

        # Summary
        sos_count = sum(1 for s in statuses.values() if s.get('status') == 'SOS')
        safe_count = sum(1 for s in statuses.values() if s.get('status') == 'SAFE')
        msg += f"\n📊 Summary: 🔴{sos_count} SOS | 🟢{safe_count} SAFE | Total: {len(statuses)}"

        return msg

    elif command.lower() in ['/users', '/members']:
        # List all registered users
        if not users:
            return "No users registered yet."

        msg = f"📋 Registered users ({len(users)}):\n\n"
        for uid, data in sorted(users.items(), key=lambda x: x[1].get('last_seen', ''), reverse=True):
            status = data.get('status', 'UNKNOWN')
            status_emoji = "🟢" if status == 'SAFE' else "🔴" if status == 'SOS' else "⚪"
            msg += f"{status_emoji} {data.get('name', 'Unknown')} (@{data.get('username', 'N/A')})\n"

        return msg

    elif command.lower() in ['/subscribe', '/register']:
        return f"✅ You're registered! Name: {name}\nYour status: {statuses.get(user_id, {}).get('status', 'UNKNOWN')}\n\nCommands:\n/sos - Request help\n/safe - I'm safe\n/status - Check status"

    return "Commands:\n/sos - Request emergency help\n/safe - Confirm you're safe\n/status - Check your current status\n/subscribe - Register"

# ==================== BROADCAST ====================

def broadcast_message(bot_token: str, message: str, parse_mode: str = "HTML") -> dict:
    """Broadcast a message to all registered users"""
    users = get_registered_users()
    results = {
        "sent": [],
        "failed": [],
        "total": len(users)
    }

    for user_id, user_data in users.items():
        chat_id = user_data.get("chat_id")
        if not chat_id:
            continue

        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            }, timeout=10)

            if response.json().get("ok"):
                results["sent"].append(chat_id)
            else:
                results["failed"].append({"chat_id": chat_id, "error": response.json().get("description")})

        except Exception as e:
            results["failed"].append({"chat_id": chat_id, "error": str(e)})

    return results

def send_broadcast_from_monitor(bot_token: str, event_title: str, event_type: str, location: str = "", severity: str = "high") -> dict:
    """Send alert broadcast from monitor.py"""
    severity_emoji = {"critical": "🚨", "high": "⚠️", "medium": "📢", "low": "ℹ️"}.get(severity, "⚠️")

    message = f"{severity_emoji} <b>⚠️ DISASTER ALERT</b>\n\n"
    message += f"<b>Type:</b> {event_type}\n"
    if location:
        message += f"<b>Location:</b> {location}\n"
    message += f"<b>Event:</b> {event_title}\n\n"
    message += "Please respond with:\n"
    message += "/sos - If you need help\n"
    message += "/safe - If you're safe\n"

    return broadcast_message(bot_token, message)

# ==================== TELEGRAM POLLING ====================

def poll_updates(bot_token: str):
    """Poll Telegram for updates - continuous loop"""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    offset = None

    print("🤖 Telegram Bot Handler started...")
    print("Listening for commands: /sos, /safe, /status, /broadcast, /list, /users")

    while True:
        params = {"timeout": 30, "allowed_updates": ["message"]}
        if offset:
            params["offset"] = offset

        try:
            response = requests.get(url, params=params, timeout=35)
            data = response.json()

            if not data.get("ok"):
                continue

            updates = data.get("result", [])
            for update in updates:
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                chat_id = str(message["chat"]["id"])
                name = f"{message['chat'].get('first_name', '')} {message['chat'].get('last_name', '')}".strip() or "Unknown"
                username = message['chat'].get('username', '')

                text = message.get("text", "")

                # Process commands
                if text.startswith('/sos'):
                    reply = handle_command(bot_token, chat_id, '/sos', name, username)
                elif text.startswith('/safe'):
                    reply = handle_command(bot_token, chat_id, '/safe', name, username)
                elif text.startswith('/status'):
                    reply = handle_command(bot_token, chat_id, '/status', name, username)
                elif text.startswith('/list') or text.startswith('/reports'):
                    reply = handle_command(bot_token, chat_id, '/list', name, username)
                elif text.startswith('/users') or text.startswith('/members'):
                    reply = handle_command(bot_token, chat_id, '/users', name, username)
                elif text.startswith('/subscribe') or text.startswith('/register'):
                    reply = handle_command(bot_token, chat_id, '/subscribe', name, username)
                else:
                    reply = f"👋 Hello {name}! I'm the Disaster Monitor Bot.\n\nCommands:\n/sos - Request emergency help\n/safe - Confirm you're safe\n/status - Check your status\n/subscribe - Register"

                # Send reply
                send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                requests.post(send_url, json={
                    "chat_id": chat_id,
                    "text": reply,
                    "parse_mode": "HTML"
                }, timeout=10)

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"Error: {e}")
            continue

# ==================== MAIN ====================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python bot_handler.py <bot_token>")
        print("")
        print("Telegram Commands:")
        print("  /sos       - Request emergency help")
        print("  /safe      - Confirm you're safe")
        print("  /status    - Check your status")
        print("  /subscribe - Register yourself")
        print("  /list      - View all statuses (admin)")
        print("  /users     - View all registered users")
        sys.exit(1)

    token = sys.argv[1]

    try:
        poll_updates(token)
    except KeyboardInterrupt:
        print("\n👋 Bot handler stopped")