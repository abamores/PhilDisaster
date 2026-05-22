# Philippines Disaster Monitoring System 🌏

Real-time monitoring dashboard and alerting system for Philippine disaster events with crowd-sourced safety status tracking.

## Features

### Dashboard
- **Live RSS/XML aggregation** from:
  - 🌋 PHILVOLCS (seismic activity, volcanic eruptions, tsunamis)
  - 🌦️ PAGASA (weather, tropical cyclones, floods)
  - 🌍 GDACS (global disasters affecting Philippines)
  - 📺 Google News PH (Philippine disaster news)

- **Severity filtering** with color-coded alerts:
  - 🔴 Critical (M5.0+ earthquakes, State of Calamity)
  - 🟠 High (M4.0+ earthquakes, Severe weather warnings)
  - 🟡 Medium (M3.0+ seismic activity, Weather advisories)
  - 🟢 Low (Minor events, informational)

- **Provincial hazard sidebar** with Mindanao focus:
  - Real-time status per province
  - Active event counts
  - Regional grouping
  - Risk level indicators

### Alerting System
- **Telegram alerts** for:
  - 🚨 State of Calamity declarations
  - 🌋 Major earthquakes (M5.0+)
  - 🌪️ Severe tropical cyclones (Signal #3+)

- **Rich formatted messages** with:
  - Location and affected region
  - Hazard types for the area
  - Direct links to official sources
  - Recommended safety actions

- **Broadcast to all users**: When disaster alerts trigger, ALL registered Telegram users receive the alert

### Crowd-Sourced Safety Status
- **People can report via Telegram**:
  - `/sos` - Request emergency help
  - `/safe` - Confirm you're safe
  - `/status` - Check your status

- **Dashboard shows all reports**:
  - 🔴 SOS count (people needing help)
  - 🟢 SAFE count (people confirmed safe)
  - Individual user status with timestamp
  - Telegram username tracking

- **How it works**:
  1. User messages @PhilippineDisasterMonitoring_bot
  2. Sends /sos or /safe
  3. Status appears on dashboard in real-time
  4. All users receive disaster alerts automatically

## Quick Start

### 1. Install Dependencies

```bash
cd disaster-monitor
pip install -r requirements.txt
```

### 2. Configure Telegram

Set environment variables:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### 3. Start the Bot Handler (Terminal 1)

```bash
cd /Users/a2519/CLAUDE_WORKSPACE/disaster-monitor
python3 bot_handler.py 8938903628:AAGCXL5AgWsymcZAGmOOoe0d2ZHCMPHpzbM
```

### 4. Run the Dashboard (Terminal 2)

```bash
cd /Users/a2519/CLAUDE_WORKSPACE/disaster-monitor
streamlit run dashboard.py --server.port 8501
```

### 5. Run the Automated Monitor (Optional)

```bash
python monitor.py --interval 15
```

## Project Structure

```
disaster-monitor/
├── scraper.py      # RSS/XML feed parsing and data models
├── dashboard.py    # Streamlit dashboard UI
├── monitor.py      # Automated monitoring and alerting
├── bot_handler.py  # Telegram bot for SOS/SAFE commands
├── requirements.txt
├── config.json     # (optional) Configuration file
└── README.md
```

## How Users Register

1. **User messages the bot** on Telegram: @PhilippineDisasterMonitoring_bot
2. **User sends `/sos`** (if they need help) or **`/safe`** (if they're safe)
3. **Bot registers the user** and records their status
4. **Dashboard updates** showing all user statuses
5. **When disaster alert fires**, ALL registered users receive the alert via broadcast

## Alert Triggers

| Event Type | Trigger Condition | Alert |
|------------|------------------|-------|
| Earthquake | Magnitude >= 5.0 | 🚨 Critical |
| Earthquake | Magnitude >= 4.0 | ⚠️ High |
| Weather | Tropical Cyclone Signal #3+ | 🚨 Critical |
| Calamity | "State of Calamity" declared | 🚨 Critical |
| Tsunami | Any tsunami warning | 🚨 Critical |
| Volcanic | Any eruption warning | ⚠️ High |

## Provincial Risk Profiles

The system tracks 30+ high-risk Philippine provinces, with special focus on Mindanao regions:

**Highest Risk (Seismic)**
- Davao Oriental/Sur/Norte
- Surigao del Norte/Sur
- Compostela Valley

**High Risk (Flooding)**
- Pampanga, Bulacan, Nueva Ecija
- Leyte, Samar

**Monitored Hazards**
- Earthquakes, Tsunamis
- Volcanic eruptions
- Tropical cyclones
- Flooding, Landslides

## Deployment

### Local Development
```bash
python3 bot_handler.py <BOT_TOKEN> &  # Start Telegram bot
streamlit run dashboard.py           # Start dashboard
```

### Production (Self-Hosted)
```bash
python3 bot_handler.py <BOT_TOKEN> &  # Background Telegram bot
python3 monitor.py --interval 5 &     # Background monitor
```

---
Built for rapid awareness of regional disaster escalations in the Philippines.