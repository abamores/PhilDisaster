"""
Web Server for Philippine Disaster Monitor
Full HTML Dashboard + Telegram polling via UptimeRobot
"""

import os
import sys
import json
import requests
from datetime import datetime
from flask import Flask, jsonify, request, redirect

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8938903628:AAGCXL5AgWsymcZAGmOOoe0d2ZHCMPHpzbM")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "59838581")

STATUS_FILE = "status.json"
USERS_FILE = "users.json"

HIGH_RISK_PROVINCES = {
    "Davao Oriental": {"region": "Davao", "risk": "high", "hazards": ["earthquake", "landslide", "flood"]},
    "Davao del Norte": {"region": "Davao", "risk": "high", "hazards": ["flood", "landslide"]},
    "Davao del Sur": {"region": "Davao", "risk": "high", "hazards": ["earthquake", "flood"]},
    "Compostela Valley": {"region": "Davao", "risk": "high", "hazards": ["landslide", "flood"]},
    "Surigao del Norte": {"region": "Caraga", "risk": "high", "hazards": ["earthquake", "tsunami"]},
    "Surigao del Sur": {"region": "Caraga", "risk": "high", "hazards": ["earthquake", "flood"]},
    "Agusan del Norte": {"region": "Caraga", "risk": "medium", "hazards": ["flood", "landslide"]},
    "Bukidnon": {"region": "Northern Mindanao", "risk": "high", "hazards": ["landslide", "earthquake"]},
    "Lanao del Norte": {"region": "Northern Mindanao", "risk": "high", "hazards": ["flood", "landslide"]},
    "Zamboanga del Norte": {"region": "Zamboanga", "risk": "high", "hazards": ["earthquake", "flood"]},
    "Zamboanga del Sur": {"region": "Zamboanga", "risk": "high", "hazards": ["earthquake", "landslide"]},
    "Misamis Oriental": {"region": "Northern Mindanao", "risk": "high", "hazards": ["earthquake", "flood"]},
    "Leyte": {"region": "Eastern Visayas", "risk": "high", "hazards": ["typhoon", "storm surge", "landslide"]},
    "Samar": {"region": "Eastern Visayas", "risk": "high", "hazards": ["typhoon", "flood"]},
    "Pampanga": {"region": "Central Luzon", "risk": "high", "hazards": ["volcanic", "flood"]},
    "Bulacan": {"region": "Central Luzon", "risk": "medium", "hazards": ["flood"]},
    "Nueva Ecija": {"region": "Central Luzon", "risk": "high", "hazards": ["flood", "earthquake"]},
    "Quezon": {"region": "CALABARZON", "risk": "high", "hazards": ["typhoon", "flood", "landslide"]},
    "Cebu": {"region": "Central Visayas", "risk": "medium", "hazards": ["earthquake", "flood"]},
    "Iloilo": {"region": "Western Visayas", "risk": "medium", "hazards": ["flood", "typhoon"]},
}

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
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

OFFSET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".telegram_offset")

def poll_telegram_commands():
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"timeout": 1, "allowed_updates": ["message"]}

        # Load last offset so we only get NEW updates
        offset = load_json(OFFSET_FILE, None)
        if offset:
            params["offset"] = offset

        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if not data.get("ok"):
            return 0

        updates = data.get("result", [])
        processed = 0
        new_offset = offset
        statuses = load_json(STATUS_FILE, {})
        users = load_json(USERS_FILE, {})

        for update in updates:
            message = update.get("message")
            if not message:
                continue

            new_offset = update["update_id"] + 1
            chat_id = str(message["chat"]["id"])
            name = f"{message['chat'].get('first_name', '')} {message['chat'].get('last_name', '')}".strip() or "Unknown"
            username = message['chat'].get('username', '')
            text = message.get("text", "")

            # Extract location if present
            location = None
            msg_location = message.get("location")
            if msg_location:
                location = {"lat": msg_location.get("latitude"), "lon": msg_location.get("longitude")}

            users[chat_id] = {"chat_id": chat_id, "name": name, "username": username, "status": "UNKNOWN", "last_seen": datetime.now().isoformat()}

            if text.startswith('/sos'):
                statuses[chat_id] = {"name": name, "username": username, "status": "SOS", "timestamp": datetime.now().isoformat(), "chat_id": chat_id, "location": location}
                users[chat_id]["status"] = "SOS"
                processed += 1
                send_telegram_message(chat_id, "🆘 SOS registered! Help is on the way.\n\n🌐 Dashboard: https://phil-disaster-monitor.onrender.com/dashboard")
            elif text.startswith('/safe'):
                statuses[chat_id] = {"name": name, "username": username, "status": "SAFE", "timestamp": datetime.now().isoformat(), "chat_id": chat_id, "location": location}
                users[chat_id]["status"] = "SAFE"
                processed += 1
                send_telegram_message(chat_id, "✅ You're marked as SAFE. Glad you're okay!\n\n🌐 Dashboard: https://phil-disaster-monitor.onrender.com/dashboard")
            elif text.startswith('/status'):
                current = statuses.get(chat_id, {}).get('status', 'UNKNOWN')
                send_telegram_message(chat_id, f"📍 Your current status: {current}")

        if processed > 0:
            save_json(STATUS_FILE, statuses)
            save_json(USERS_FILE, users)

        # Save offset AFTER processing so Telegram knows we've read these updates
        if new_offset:
            save_json(OFFSET_FILE, new_offset)

        return processed
    except:
        return 0

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌏 Philippine Disaster Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f4f8; color: #333; display: flex; min-height: 100vh; }
        .sidebar { width: 280px; background: linear-gradient(180deg, #1E3A5F 0%, #2C5282 100%); color: white; padding: 1.5rem; position: fixed; height: 100vh; overflow-y: auto; }
        .sidebar h2 { font-size: 1.25rem; margin-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 0.5rem; }
        .sidebar-section { margin-bottom: 1.5rem; }
        .sidebar h3 { font-size: 0.85rem; text-transform: uppercase; opacity: 0.8; margin-bottom: 0.75rem; }
        .province { padding: 0.5rem; border-radius: 6px; margin-bottom: 0.5rem; background: rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center; }
        .province-name { font-size: 0.9rem; }
        .province-status { font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 4px; }
        .province-status.high { background: #FF4444; }
        .province-status.medium { background: #FF8C00; }
        .province-status.low { background: #4CAF50; }
        .province-count { background: rgba(255,255,255,0.2); padding: 0.2rem 0.5rem; border-radius: 50%; font-size: 0.75rem; }
        .legend { font-size: 0.8rem; }
        .legend-item { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
        .legend-dot { width: 10px; height: 10px; border-radius: 50%; }
        .main { flex: 1; margin-left: 280px; padding: 1.5rem; }
        .header { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 1.5rem; text-align: center; }
        .header h1 { font-size: 2.5rem; color: #1E3A5F; margin-bottom: 0.5rem; }
        .header p { color: #666; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
        .metric { background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
        .metric h3 { font-size: 2.5rem; margin-bottom: 0.25rem; }
        .metric p { color: #666; font-size: 0.9rem; }
        .metric.alert { background: linear-gradient(135deg, #FF4444 0%, #CC0000 100%); color: white; }
        .metric.alert h3 { color: white; }
        .metric.safe { background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%); color: white; }
        .metric.safe h3 { color: white; }
        .telegram-box { background: #E8F5E9; border-left: 4px solid #4CAF50; padding: 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1.5rem; }
        .telegram-box h4 { color: #2E7D32; margin-bottom: 0.5rem; }
        .telegram-box code { background: #C8E6C9; padding: 0.2rem 0.5rem; border-radius: 4px; font-family: monospace; }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
        .tab { padding: 0.75rem 1.5rem; background: white; border: 2px solid #e2e8f0; border-radius: 8px; cursor: pointer; font-size: 1rem; transition: all 0.3s; }
        .tab:hover { border-color: #2C5282; }
        .tab.active { background: #2C5282; color: white; border-color: #2C5282; }
        .content { background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .content h3 { margin-bottom: 1rem; font-size: 1.25rem; }
        .event { padding: 1rem; border-left: 4px solid #ccc; margin-bottom: 1rem; border-radius: 0 8px 8px 0; background: #f8f9fa; }
        .event.critical { border-left-color: #FF4444; background: #FFE5E5; }
        .event.high { border-left-color: #FF8C00; background: #FFF3E5; }
        .event.medium { border-left-color: #FFD700; background: #FFFFF0; }
        .event h4 { margin-bottom: 0.5rem; font-size: 1rem; }
        .event-meta { font-size: 0.8rem; color: #666; margin-bottom: 0.5rem; }
        .event a { color: #2C5282; text-decoration: none; font-size: 0.9rem; }
        .event a:hover { text-decoration: underline; }
        .person { display: flex; align-items: center; gap: 1rem; padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem; background: #f8f9fa; }
        .person.sos { background: #FFE5E5; border-left: 4px solid #FF4444; }
        .person.safe { background: #E8F5E9; border-left: 4px solid #4CAF50; }
        .person-emoji { font-size: 2rem; }
        .person-info h4 { margin: 0; font-size: 1rem; }
        .person-info small { opacity: 0.7; }
        .source-tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
        .source-tab { padding: 0.5rem 1rem; background: #f0f4f8; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
        .source-tab.active { background: #1E3A5F; color: white; }
        .region-group { margin-bottom: 1rem; }
        .region-title { font-weight: bold; font-size: 0.9rem; color: #1E3A5F; margin-bottom: 0.5rem; padding-bottom: 0.25rem; border-bottom: 1px solid #e2e8f0; }
        .empty { text-align: center; padding: 2rem; color: #666; }
        .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
        .user-card { display: flex; align-items: center; gap: 1rem; padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem; background: #f8f9fa; border-left: 4px solid #ccc; }
        .user-card.safe { border-left-color: #4CAF50; background: #E8F5E9; }
        .user-card.sos { border-left-color: #FF4444; background: #FFE5E5; }
        .user-card .avatar { font-size: 1.5rem; }
        .user-card .info { flex: 1; }
        .user-card .info h4 { margin: 0 0 0.25rem 0; font-size: 0.95rem; }
        .user-card .info small { opacity: 0.7; }
        .user-card .status-badge { padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.8rem; font-weight: bold; }
        .status-badge.safe { background: #4CAF50; color: white; }
        .status-badge.sos { background: #FF4444; color: white; }
        .status-badge.unknown { background: #999; color: white; }
        @media (max-width: 900px) {
            .sidebar { width: 100%; position: relative; height: auto; }
            .main { margin-left: 0; }
            body { flex-direction: column; }
        }
        #people-map { border: 2px solid #e2e8f0; }
    </style>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
</head>
<body>
    <div class="sidebar">
        <h2>🗺️ Provincial Hazard Status</h2>
        <p style="font-size: 0.85rem; opacity: 0.8; margin-bottom: 1rem;">Mindanao & High-Risk Areas</p>

        <div class="sidebar-section">
            <h3>Regions</h3>
            <div id="province-list">Loading...</div>
        </div>

        <div class="sidebar-section">
            <h3>Status Legend</h3>
            <div class="legend">
                <div class="legend-item"><span class="legend-dot" style="background:#FF4444;"></span> Emergency</div>
                <div class="legend-item"><span class="legend-dot" style="background:#FF8C00;"></span> Watch</div>
                <div class="legend-item"><span class="legend-dot" style="background:#FFD700;"></span> Advisory</div>
                <div class="legend-item"><span class="legend-dot" style="background:#4CAF50;"></span> Normal</div>
            </div>
        </div>

        <div class="sidebar-section">
            <h3>Refresh</h3>
            <button onclick="refreshData()" style="width:100%; padding: 0.75rem; background: rgba(255,255,255,0.2); border: none; color: white; border-radius: 6px; cursor: pointer;">🔄 Refresh Data</button>
        </div>
    </div>

    <div class="main">
        <div class="header">
            <h1>🌏 Philippine Disaster Monitor</h1>
            <p>Real-time monitoring: PHILVOLCS • PAGASA • GDACS • Google News PH</p>
        </div>

        <div class="metrics">
            <div class="metric">
                <h3 id="total-events">0</h3>
                <p>Total Events</p>
            </div>
            <div class="metric">
                <h3 id="critical-count">0</h3>
                <p>Critical/High</p>
            </div>
            <div class="metric alert">
                <h3 id="sos-count">0</h3>
                <p>🔴 SOS Reports</p>
            </div>
            <div class="metric safe">
                <h3 id="safe-count">0</h3>
                <p>🟢 Safe Reports</p>
            </div>
        </div>

        <div class="telegram-box">
            <h4>📱 Telegram Integration Active</h4>
            <p>Message <strong><a href="https://t.me/PhilippineDisasterMonitoring_bot" target="_blank">t.me/PhilippineDisasterMonitoring_bot</a></strong> on Telegram:</p>
            <p><code>/sos</code> Request emergency help | <code>/safe</code> Confirm you're safe | <code>/status</code> Check your status</p>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('events')">📊 All Events</button>
            <button class="tab" onclick="showTab('mindanao')">🏝️ Mindanao Focus</button>
            <button class="tab" onclick="showTab('sos')">🆘 People Status</button>
            <button class="tab" onclick="showTab('users')">👥 Users</button>
        </div>

        <div id="events-tab" class="content">
            <div class="source-tabs">
                <span class="source-tab active" onclick="filterSource('all')">All Sources</span>
                <span class="source-tab" onclick="filterSource('PHILVOLCS')">🌋 PHILVOLCS</span>
                <span class="source-tab" onclick="filterSource('PAGASA')">🌦️ PAGASA</span>
                <span class="source-tab" onclick="filterSource('GDACS')">🌍 GDACS</span>
                <span class="source-tab" onclick="filterSource('Google News PH')">📰 News</span>
            </div>
            <h3>📊 Recent Disaster Events</h3>
            <div id="events-list">Loading...</div>
        </div>

        <div id="mindanao-tab" class="content" style="display:none;">
            <h3>🏝️ Mindanao Regional Focus</h3>
            <div id="mindanao-list">Loading...</div>
        </div>

        <div id="sos-tab" class="content" style="display:none;">
            <h3>🆘 People Status Reports</h3>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:1rem; margin-bottom:1rem;">
                <div id="people-list">Loading...</div>
                <div>
                    <h4 style="margin-bottom:0.5rem;">📍 Location Map</h4>
                    <div id="people-map" style="height:350px; border-radius:8px; overflow:hidden; background:#e0e0e0;"></div>
                </div>
            </div>
        </div>

        <div id="users-tab" class="content" style="display:none;">
            <h3>👥 User Registration & Management</h3>

            <div style="background:#E8F5E9;border-left:4px solid #4CAF50;padding:1rem;border-radius:0 8px 8px 0;margin-bottom:1.5rem;">
                <h4 style="color:#2E7D32;margin-bottom:0.5rem;">📝 Register New User</h4>
                <p style="font-size:0.9rem;margin-bottom:1rem;">Fill in the details below. After registration, the user <strong>must message <a href="https://t.me/PhilippineDisasterMonitoring_bot" target="_blank">t.me/PhilippineDisasterMonitoring_bot</a></strong> and send <code>/safe</code> or <code>/sos</code> to activate alerts.</p>
                <form id="register-form" onsubmit="submitRegistration(event)">
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:0.75rem;">
                        <input type="text" id="reg-firstname" placeholder="First Name *" required style="padding:0.6rem;border:1px solid #ccc;border-radius:6px;font-size:0.9rem;">
                        <input type="text" id="reg-lastname" placeholder="Last Name *" required style="padding:0.6rem;border:1px solid #ccc;border-radius:6px;font-size:0.9rem;">
                        <select id="reg-region" style="padding:0.6rem;border:1px solid #ccc;border-radius:6px;font-size:0.9rem;">
                            <option value="">Region *</option>
                            <option>National Capital Region (NCR)</option>
                            <option>Central Luzon</option>
                            <option>CALABARZON</option>
                            <option>Western Visayas</option>
                            <option>Central Visayas</option>
                            <option>Eastern Visayas</option>
                            <option>Northern Mindanao</option>
                            <option>Davao Region</option>
                            <option>Caraga</option>
                            <option>Zamboanga Peninsula</option>
                            <option>Soccsksargen</option>
                            <option>Bicol Region</option>
                            <option>Ilocos Region</option>
                            <option>Cagayan Valley</option>
                            <option>MMRA</option>
                        </select>
                        <input type="text" id="reg-section" placeholder="Section / Unit" style="padding:0.6rem;border:1px solid #ccc;border-radius:6px;font-size:0.9rem;">
                        <input type="text" id="reg-isname" placeholder="IS Name / Role" style="padding:0.6rem;border:1px solid #ccc;border-radius:6px;font-size:0.9rem;">
                        <input type="text" id="reg-chatid" placeholder="Telegram Chat ID *" required style="padding:0.6rem;border:1px solid #ccc;border-radius:6px;font-size:0.9rem;">
                        <input type="text" id="reg-username" placeholder="Telegram Username (optional)" style="padding:0.6rem;border:1px solid #ccc;border-radius:6px;font-size:0.9rem;">
                    </div>
                    <button type="submit" style="padding:0.75rem 2rem;background:#2E7D32;color:white;border:none;border-radius:6px;cursor:pointer;font-size:0.95rem;">Register User</button>
                </form>
                <div id="reg-result" style="margin-top:0.75rem;"></div>
            </div>

            <h4 style="margin-bottom:0.75rem;">📋 Registered Users (<span id="user-count">0</span>)</h4>
            <div id="users-list">Loading...</div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let allEvents = [];
        let currentSource = 'all';
        let currentTab = 'events';
        let peopleMap = null;
        let sosMarkers = [];
        let safeMarkers = [];

        async function fetchData() {
            try {
                const res = await fetch('/api/data');
                return await res.json();
            } catch {
                return { events: [], statuses: [] };
            }
        }

        function showTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('events-tab').style.display = tab === 'events' ? 'block' : 'none';
            document.getElementById('mindanao-tab').style.display = tab === 'mindanao' ? 'block' : 'none';
            document.getElementById('sos-tab').style.display = tab === 'sos' ? 'block' : 'none';
            document.getElementById('users-tab').style.display = tab === 'users' ? 'block' : 'none';
            if (tab === 'users') renderUsers(data?.users || {});
        }

        function filterSource(source) {
            currentSource = source;
            document.querySelectorAll('.source-tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            renderEvents();
        }

        function renderEvents() {
            const container = document.getElementById('events-list');
            let events = allEvents;
            if (currentSource !== 'all') {
                events = events.filter(e => e.source === currentSource);
            }
            if (!events.length) {
                container.innerHTML = '<div class="empty"><div class="empty-icon">📭</div><p>No events found</p></div>';
                return;
            }
            container.innerHTML = events.slice(0, 50).map(e => `
                <div class="event ${e.severity || 'low'}">
                    <h4>${e.severity === 'critical' ? '🚨' : e.severity === 'high' ? '⚠️' : 'ℹ️'} ${e.title || 'No Title'}</h4>
                    <div class="event-meta">${e.source || 'Unknown'} | ${e.type || 'general'} | ${(e.severity || 'low').toUpperCase()}</div>
                    <p>${(e.description || '').substring(0, 200)}...</p>
                    ${e.link ? `<a href="${e.link}" target="_blank">View Source →</a>` : ''}
                </div>
            `).join('');
        }

        function renderMindanao(events) {
            const container = document.getElementById('mindanao-list');
            const keywords = ['davao', 'surigao', 'bukidnon', 'lanao', 'maguindanao', 'cotabato', 'zamboanga', 'misamis', 'agusan', 'compostela', 'basilan', 'sulu'];
            const mindanao = events.filter(e => {
                const text = ((e.title || '') + ' ' + (e.description || '')).toLowerCase();
                return keywords.some(kw => text.includes(kw));
            });
            if (!mindanao.length) {
                container.innerHTML = '<div class="empty"><div class="empty-icon">✅</div><p>No active alerts for Mindanao region</p></div>';
                return;
            }
            container.innerHTML = mindanao.slice(0, 30).map(e => `
                <div class="event ${e.severity || 'low'}">
                    <h4>${e.severity === 'critical' ? '🚨' : e.severity === 'high' ? '⚠️' : '⚠️'} ${e.title || 'No Title'}</h4>
                    <div class="event-meta">${e.source || 'Unknown'} | ${(e.severity || 'low').toUpperCase()}</div>
                    <p>${(e.description || '').substring(0, 200)}...</p>
                    ${e.link ? `<a href="${e.link}" target="_blank">View Source →</a>` : ''}
                </div>
            `).join('');
        }

        function renderPeople(statuses) {
            const container = document.getElementById('people-list');
            if (!statuses || !Object.keys(statuses).length) {
                container.innerHTML = '<div class="empty"><div class="empty-icon">📭</div><p>No status reports yet. Send /sos or /safe via Telegram.</p></div>';
                renderPeopleMap({});
                return;
            }
            const sos = Object.values(statuses).filter(s => s.status === 'SOS');
            const safe = Object.values(statuses).filter(s => s.status === 'SAFE');

            let html = '';
            if (sos.length) {
                html += '<h4 style="color:#FF4444; margin-bottom:1rem;">🚨 SOS - Need Immediate Help</h4>';
                html += sos.map(s => `
                    <div class="person sos">
                        <div class="person-emoji">🔴</div>
                        <div class="person-info">
                            <h4>${s.name || 'Unknown'}</h4>
                            <small>@${s.username || 'N/A'} | ${s.status} | ${s.timestamp ? s.timestamp.substring(0, 16) : ''}</small>
                            ${s.location ? `<small style="display:block;margin-top:0.25rem;">📍 ${s.location.lat}, ${s.location.lon}</small>` : ''}
                        </div>
                    </div>
                `).join('');
            }
            if (safe.length) {
                html += '<h4 style="color:#4CAF50; margin:1rem 0;">🟢 Safe - Confirmed Okay</h4>';
                html += safe.map(s => `
                    <div class="person safe">
                        <div class="person-emoji">🟢</div>
                        <div class="person-info">
                            <h4>${s.name || 'Unknown'}</h4>
                            <small>@${s.username || 'N/A'} | ${s.status} | ${s.timestamp ? s.timestamp.substring(0, 16) : ''}</small>
                            ${s.location ? `<small style="display:block;margin-top:0.25rem;">📍 ${s.location.lat}, ${s.location.lon}</small>` : ''}
                        </div>
                    </div>
                `).join('');
            }
            container.innerHTML = html;
            renderPeopleMap(statuses);
        }

        function renderPeopleMap(statuses) {
            const mapDiv = document.getElementById('people-map');
            if (!mapDiv) return;

            // Clear existing markers
            sosMarkers.forEach(m => m.remove());
            safeMarkers.forEach(m => m.remove());
            sosMarkers = [];
            safeMarkers = [];

            if (!peopleMap) {
                peopleMap = L.map('people-map').setView([12.8797, 121.7740], 6);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap'
                }).addTo(peopleMap);
            }

            const withLocation = Object.values(statuses).filter(s => s.location && s.location.lat && s.location.lon);

            if (withLocation.length === 0) {
                mapDiv.innerHTML = '<div style="height:100%;display:flex;align-items:center;justify-content:center;color:#666;">No location data yet</div>';
                return;
            }

            mapDiv.innerHTML = '';

            withLocation.forEach(s => {
                const color = s.status === 'SOS' ? '#FF4444' : '#4CAF50';
                const emoji = s.status === 'SOS' ? '🔴' : '🟢';
                const marker = L.circleMarker([s.location.lat, s.location.lon], {
                    radius: 10,
                    fillColor: color,
                    color: '#fff',
                    weight: 2,
                    fillOpacity: 0.8
                }).addTo(peopleMap);
                marker.bindPopup(`<b>${emoji} ${s.name || 'Unknown'}</b><br>@${s.username || 'N/A'}<br>${s.status} - ${s.timestamp ? s.timestamp.substring(0, 16) : ''}`);
                if (s.status === 'SOS') sosMarkers.push(marker);
                else safeMarkers.push(marker);
            });

            if (withLocation.length > 0) {
                const bounds = L.latLngBounds(withLocation.map(s => [s.location.lat, s.location.lon]));
                peopleMap.fitBounds(bounds, { padding: [30, 30] });
            }
        }

        function renderUsers(users) {
            const container = document.getElementById('users-list');
            const countEl = document.getElementById('user-count');
            if (!users || !Object.keys(users).length) {
                countEl.textContent = '0';
                container.innerHTML = '<div class="empty"><div class="empty-icon">👥</div><p>No users registered yet.</p></div>';
                return;
            }
            countEl.textContent = Object.keys(users).length;
            container.innerHTML = Object.values(users).map(u => {
                const status = u.status || 'UNKNOWN';
                const badgeClass = status.toLowerCase();
                const avatar = status === 'SOS' ? '🔴' : status === 'SAFE' ? '🟢' : '⚪';
                return `<div class="user-card ${badgeClass}">
                    <div class="avatar">${avatar}</div>
                    <div class="info">
                        <h4>${u.name || 'Unknown'}</h4>
                        <small>@${u.username || 'N/A'} | ${u.region || ''} ${u.section ? '| ' + u.section : ''} ${u.is_name ? '| ' + u.is_name : ''}</small>
                    </div>
                    <span class="status-badge ${badgeClass}">${status}</span>
                </div>`;
            }).join('');
        }

        function submitRegistration(e) {
            e.preventDefault();
            const payload = {
                first_name: document.getElementById('reg-firstname').value,
                last_name: document.getElementById('reg-lastname').value,
                region: document.getElementById('reg-region').value,
                section: document.getElementById('reg-section').value,
                is_name: document.getElementById('reg-isname').value,
                chat_id: document.getElementById('reg-chatid').value,
                username: document.getElementById('reg-username').value
            };
            fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(res => {
                const el = document.getElementById('reg-result');
                if (res.success) {
                    el.innerHTML = '<span style="color:#2E7D32;">✅ ' + res.message + '</span>';
                    document.getElementById('register-form').reset();
                    loadData().then(d => { data = d; renderUsers(data?.users || {}); });
                } else {
                    el.innerHTML = '<span style="color:#FF4444;">❌ ' + res.message + '</span>';
                }
            }).catch(() => {
                document.getElementById('reg-result').innerHTML = '<span style="color:#FF4444;">❌ Error submitting form</span>';
            });
        }

        function renderProvinces(statuses) {
            const container = document.getElementById('province-list');
            const provinceStatuses = {};
            const keywords = ["Davao Oriental", "Davao del Norte", "Davao del Sur", "Compostela Valley", "Surigao del Norte", "Surigao del Sur", "Agusan del Norte", "Bukidnon", "Lanao del Norte", "Zamboanga del Norte", "Zamboanga del Sur", "Misamis Oriental", "Leyte", "Samar", "Pampanga", "Bulacan", "Nueva Ecija", "Quezon", "Cebu", "Iloilo"];

            // Count events per region
            Object.values(statuses || {}).forEach(s => {
                const name = s.name || '';
                keywords.forEach(kw => {
                    if (name.toLowerCase().includes(kw.toLowerCase())) {
                        provinceStatuses[kw] = (provinceStatuses[kw] || 0) + 1;
                    }
                });
            });

            const regions = {
                'Davao': ['Davao Oriental', 'Davao del Norte', 'Davao del Sur', 'Compostela Valley'],
                'Caraga': ['Surigao del Norte', 'Surigao del Sur', 'Agusan del Norte'],
                'Northern Mindanao': ['Bukidnon', 'Lanao del Norte', 'Misamis Oriental'],
                'Zamboanga': ['Zamboanga del Norte', 'Zamboanga del Sur'],
                'Eastern Visayas': ['Leyte', 'Samar'],
                'Central Luzon': ['Pampanga', 'Bulacan', 'Nueva Ecija'],
                'Other': ['Quezon', 'Cebu', 'Iloilo']
            };

            let html = '';
            for (const [region, provinces] of Object.entries(regions)) {
                html += `<div class="region-group"><div class="region-title">${region}</div>`;
                provinces.forEach(p => {
                    const count = provinceStatuses[p] || 0;
                    const risk = count > 0 ? 'high' : 'low';
                    html += `<div class="province">
                        <span class="province-name">${p}</span>
                        <span class="province-status ${risk}">${count > 0 ? count + ' events' : 'Normal'}</span>
                    </div>`;
                });
                html += '</div>';
            }
            container.innerHTML = html;
        }

        async function refreshData() {
            const data = await fetchData();
            allEvents = data.events || [];

            // Update metrics
            document.getElementById('total-events').textContent = allEvents.length;
            const critical = allEvents.filter(e => e.severity === 'critical' || e.severity === 'high').length;
            document.getElementById('critical-count').textContent = critical;

            const statuses = data.statuses || {};
            const sos = Object.values(statuses).filter(s => s.status === 'SOS').length;
            const safe = Object.values(statuses).filter(s => s.status === 'SAFE').length;
            document.getElementById('sos-count').textContent = sos;
            document.getElementById('safe-count').textContent = safe;

            // Render all sections
            renderEvents();
            renderMindanao(allEvents);
            renderPeople(statuses);
            renderProvinces(statuses);
        }

        refreshData();
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return redirect('/dashboard', code=302)

@app.route('/dashboard')
def dashboard():
    return DASHBOARD_HTML

@app.route('/api/data')
def api_data():
    poll_telegram_commands()
    statuses = load_json(STATUS_FILE, {})
    users = load_json(USERS_FILE, {})
    events = []
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from scraper import scrape_all_feeds
        events = scrape_all_feeds()
    except:
        pass
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "events": events,
        "statuses": statuses,
        "users": users
    })

@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        data = request.get_json()
        required = ['first_name', 'last_name', 'chat_id']
        for f in required:
            if not data.get(f):
                return jsonify({"success": False, "message": f"{f} is required"})
        users = load_json(USERS_FILE, {})
        chat_id = str(data['chat_id'])
        users[chat_id] = {
            "chat_id": chat_id,
            "name": f"{data['first_name']} {data['last_name']}".strip(),
            "first_name": data['first_name'],
            "last_name": data['last_name'],
            "region": data.get('region', ''),
            "section": data.get('section', ''),
            "is_name": data.get('is_name', ''),
            "username": data.get('username', ''),
            "status": "UNKNOWN",
            "registered_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat()
        }
        save_json(USERS_FILE, users)
        return jsonify({"success": True, "message": f"User {data['first_name']} registered!"})
    except:
        return jsonify({"success": False, "message": "Registration failed"})

@app.route('/health')
def health():
    processed = poll_telegram_commands()
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
        }
    })

@app.route('/status')
def status():
    return jsonify(load_json(STATUS_FILE, {}))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🌏 Philippine Disaster Monitor running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)