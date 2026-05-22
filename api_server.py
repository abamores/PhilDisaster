"""
Web Server for Philippine Disaster Monitor
Serves HTML dashboard + Telegram polling via UptimeRobot
"""

import os
import sys
import json
import requests
from datetime import datetime
from flask import Flask, jsonify, request, redirect

app = Flask(__name__)

# Get bot token
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8938903628:AAGCXL5AgWsymcZAGmOOoe0d2ZHCMPHpzbM")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "59838581")

# Files
STATUS_FILE = "status.json"
USERS_FILE = "users.json"

# ==================== HELPER FUNCTIONS ====================

def load_json(filepath, default=None):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except:
        pass
    return default if default is not None else {}

def save_json(filepath, data):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except:
        return False

def send_telegram_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
    except:
        pass

def poll_telegram_commands():
    """Poll Telegram for any pending /sos or /safe updates"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"timeout": 1, "allowed_updates": ["message"]}
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if not data.get("ok"):
            return 0

        updates = data.get("result", [])
        processed = 0
        statuses = load_json(STATUS_FILE, {})
        users = load_json(USERS_FILE, {})

        for update in updates:
            message = update.get("message")
            if not message:
                continue

            chat_id = str(message["chat"]["id"])
            name = f"{message['chat'].get('first_name', '')} {message['chat'].get('last_name', '')}".strip() or "Unknown"
            username = message['chat'].get('username', '')
            text = message.get("text", "")

            # Register user
            users[chat_id] = {
                "chat_id": chat_id,
                "name": name,
                "username": username,
                "status": "UNKNOWN",
                "last_seen": datetime.now().isoformat()
            }

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
                send_telegram_message(chat_id, "🆘 SOS registered! Help is on the way. Stay safe.")

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
                send_telegram_message(chat_id, "✅ You're marked as SAFE. Glad you're okay!")

        if processed > 0:
            save_json(STATUS_FILE, statuses)
            save_json(USERS_FILE, users)

        return processed
    except Exception as e:
        print(f"Error polling Telegram: {e}")
        return 0

def get_dashboard_data():
    """Fetch disaster events from feeds"""
    events = []
    try:
        from scraper import get_dashboard_data as scrape
        data = scrape()
        events = data.get('events', [])
    except:
        pass
    return events

# ==================== HTML DASHBOARD ====================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌏 Philippine Disaster Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1E3A5F 0%, #2C5282 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .header p { opacity: 0.9; }
        .container { max-width: 1200px; margin: 0 auto; padding: 1.5rem; }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .metric {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .metric h3 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .metric p { opacity: 0.7; }
        .metric.alert { background: #FF4444; color: white; }
        .metric.safe { background: #4CAF50; color: white; }
        .tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }
        .tab {
            padding: 0.75rem 1.5rem;
            background: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s;
        }
        .tab:hover { background: #e2e8f0; }
        .tab.active { background: #2C5282; color: white; }
        .content {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .event {
            padding: 1rem;
            border-left: 4px solid #ccc;
            margin-bottom: 1rem;
            border-radius: 0 8px 8px 0;
            background: #f8f9fa;
        }
        .event.critical { border-left-color: #FF4444; }
        .event.high { border-left-color: #FF8C00; }
        .event.medium { border-left-color: #FFD700; }
        .event h4 { margin-bottom: 0.5rem; }
        .event small { opacity: 0.7; }
        .event a { color: #2C5282; }
        .person {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            background: #f8f9fa;
        }
        .person.sos { background: #FFE5E5; border-left: 4px solid #FF4444; }
        .person.safe { background: #E8F5E9; border-left: 4px solid #4CAF50; }
        .person-emoji { font-size: 2rem; }
        .person-info h4 { margin: 0; }
        .person-info small { opacity: 0.7; }
        .section-title { margin-bottom: 1rem; font-size: 1.25rem; }
        .refresh {
            position: fixed;
            bottom: 1.5rem;
            right: 1.5rem;
            background: #2C5282;
            color: white;
            border: none;
            padding: 1rem 1.5rem;
            border-radius: 50px;
            cursor: pointer;
            font-size: 1rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .telegram-info {
            background: #e8f5e9;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }
        .telegram-info h4 { color: #2C5282; margin-bottom: 0.5rem; }
        .telegram-info code {
            background: #c8e6c9;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌏 Philippine Disaster Monitor</h1>
        <p>Real-time monitoring: PHILVOLCS • PAGASA • GDACS</p>
    </div>

    <div class="container">
        <div class="metrics">
            <div class="metric">
                <h3 id="total-events">0</h3>
                <p>Total Events</p>
            </div>
            <div class="metric" id="critical-metric">
                <h3 id="critical-count">0</h3>
                <p>Critical/High</p>
            </div>
            <div class="metric alert">
                <h3 id="sos-count">0</h3>
                <p>🔴 SOS</p>
            </div>
            <div class="metric safe">
                <h3 id="safe-count">0</h3>
                <p>🟢 SAFE</p>
            </div>
        </div>

        <div class="telegram-info">
            <h4>📱 Telegram Commands</h4>
            <p>Message <strong>@PhilippineDisasterMonitoring_bot</strong> and send:</p>
            <p><code>/sos</code> - Request help | <code>/safe</code> - I'm safe | <code>/status</code> - Check status</p>
            <p><small>Bot is active! Status updates appear below automatically.</small></p>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('events')">📊 All Events</button>
            <button class="tab" onclick="showTab('sos')">🆘 People Status</button>
        </div>

        <div class="content" id="events-tab">
            <h3 class="section-title">📊 Recent Disaster Events</h3>
            <div id="events-list">Loading...</div>
        </div>

        <div class="content" id="sos-tab" style="display:none;">
            <h3 class="section-title">🆘 People Status Reports</h3>
            <div id="people-list">Loading...</div>
        </div>
    </div>

    <button class="refresh" onclick="refreshData()">🔄 Refresh</button>

    <script>
        let currentTab = 'events';

        async function fetchData() {
            try {
                const res = await fetch('/api/data');
                return await res.json();
            } catch (e) {
                return { events: [], statuses: [], users: {} };
            }
        }

        function showTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('events-tab').style.display = tab === 'events' ? 'block' : 'none';
            document.getElementById('sos-tab').style.display = tab === 'sos' ? 'block' : 'none';
        }

        function renderEvents(events) {
            const container = document.getElementById('events-list');
            if (!events || events.length === 0) {
                container.innerHTML = '<p>No events found.</p>';
                return;
            }
            container.innerHTML = events.slice(0, 30).map(e => `
                <div class="event ${e.severity || 'low'}">
                    <h4>${e.severity === 'critical' ? '🚨' : e.severity === 'high' ? '⚠️' : 'ℹ️'} ${e.title || 'No Title'}</h4>
                    <small>${e.source || 'Unknown'} | ${e.type || 'general'} | ${e.severity || 'low'}</small>
                    <p>${(e.description || '').substring(0, 200)}...</p>
                    ${e.link ? `<a href="${e.link}" target="_blank">View Source →</a>` : ''}
                </div>
            `).join('');
        }

        function renderPeople(statuses) {
            const container = document.getElementById('people-list');
            if (!statuses || Object.keys(statuses).length === 0) {
                container.innerHTML = '<p>No status reports yet. People can send /sos or /safe via Telegram.</p>';
                return;
            }
            container.innerHTML = Object.values(statuses).map(s => `
                <div class="person ${s.status === 'SOS' ? 'sos' : 'safe'}">
                    <div class="person-emoji">${s.status === 'SOS' ? '🔴' : '🟢'}</div>
                    <div class="person-info">
                        <h4>${s.name || 'Unknown'}</h4>
                        <small>@${s.username || 'N/A'} | ${s.status}</small>
                    </div>
                </div>
            `).join('');
        }

        async function refreshData() {
            const data = await fetchData();

            // Update metrics
            document.getElementById('total-events').textContent = data.events?.length || 0;
            const critical = (data.events || []).filter(e => e.severity === 'critical' || e.severity === 'high').length;
            document.getElementById('critical-count').textContent = critical;

            const sos = Object.values(data.statuses || {}).filter(s => s.status === 'SOS').length;
            const safe = Object.values(data.statuses || {}).filter(s => s.status === 'SAFE').length;
            document.getElementById('sos-count').textContent = sos;
            document.getElementById('safe-count').textContent = safe;

            // Render content
            renderEvents(data.events);
            renderPeople(data.statuses);
        }

        // Initial load and auto-refresh every 30 seconds
        refreshData();
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
"""

# ==================== WEB ENDPOINTS ====================

@app.route('/')
def index():
    """Main dashboard"""
    return redirect('/dashboard', code=302)

@app.route('/dashboard')
def dashboard():
    """Serve the HTML dashboard"""
    return DASHBOARD_HTML

@app.route('/api/data')
def api_data():
    """Get all data for dashboard"""
    # Poll Telegram for any new commands (keeps bot active)
    poll_telegram_commands()

    # Load statuses and users
    statuses = load_json(STATUS_FILE, {})
    users = load_json(USERS_FILE, {})

    # Get events
    events = []
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from scraper import scrape_all_feeds
        events = scrape_all_feeds()
    except Exception as e:
        print(f"Error fetching events: {e}")

    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "events": events,
        "statuses": statuses,
        "users": users,
        "sos_count": sum(1 for s in statuses.values() if s.get('status') == 'SOS'),
        "safe_count": sum(1 for s in statuses.values() if s.get('status') == 'SAFE')
    })

@app.route('/health')
def health():
    """Health check + Telegram polling"""
    # Process any pending Telegram commands
    processed = poll_telegram_commands()

    # Load current status
    statuses = load_json(STATUS_FILE, {})
    users = load_json(USERS_FILE, {})

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "telegram_processed": processed,
        "people_status": {
            "sos": sum(1 for s in statuses.values() if s.get('status') == 'SOS'),
            "safe": sum(1 for s in statuses.values() if s.get('status') == 'SAFE'),
            "total": len(statuses)
        },
        "users_registered": len(users)
    })

@app.route('/status')
def status():
    """Simple status endpoint"""
    return jsonify(load_json(STATUS_FILE, {}))

@app.route('/broadcast', methods=['POST'])
def broadcast():
    """Broadcast message to all users"""
    message = request.json.get('message', '')
    if not message:
        return jsonify({"error": "No message"}), 400

    users = load_json(USERS_FILE, {})
    sent, failed = [], []

    for user_id, user_data in users.items():
        chat_id = user_data.get('chat_id')
        if not chat_id:
            continue
        try:
            send_telegram_message(chat_id, message)
            sent.append(chat_id)
        except:
            failed.append(chat_id)

    return jsonify({"sent": sent, "failed": failed, "total": len(users)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║         🌏 Philippine Disaster Monitor                      ║
║         API Server + Dashboard                              ║
╚══════════════════════════════════════════════════════════════╝

🚀 Server running on port {port}

📍 Endpoints:
   /           → Redirect
   /dashboard  → HTML Dashboard
   /api/data   → JSON data (events + statuses)
   /health     → Health check + Telegram polling
   /status     → Current statuses
   /broadcast  → Send message to all users
    """)
    app.run(host="0.0.0.0", port=port, debug=False)