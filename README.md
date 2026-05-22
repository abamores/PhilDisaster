# Philippines Disaster Monitoring System 🌏

Real-time monitoring dashboard and alerting system for Philippine disaster events with crowd-sourced safety status tracking.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Render.com (Free Tier)                    │
│  ┌─────────────────┐    ┌────────────────────────────────┐ │
│  │  Flask API      │    │      Streamlit Dashboard        │ │
│  │  Server         │◄──►│      (HTML Dashboard)          │ │
│  │  /health        │    │                                │ │
│  │  /status        │    │  Tabs:                          │ │
│  │  /broadcast     │    │  • All Events                    │ │
│  │                 │    │  • Mindanao Focus               │ │
│  │  Telegram       │    │  • People Status (SOS/SAFE)     │ │
│  │  Polling        │    │  • User Management              │ │
│  │  (on /health)   │    │                                │ │
│  └────────┬────────┘    └────────────────────────────────┘ │
│           │                                             │
│  ┌────────▼────────┐                                      │
│  │  UptimeRobot    │◄──── Pings /health every 5 min       │
│  │  (Free)        │       Keeps app alive                 │
│  └────────────────┘       Polls Telegram for /sos       │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴────────────────┐
              ▼                               ▼
     ┌────────────────┐              ┌────────────────┐
     │ Telegram Bot   │              │  Alert         │
     │ @PhilippineDis │              │  Broadcast     │
     │ asterMonitor  │              │  to All Users │
     └────────────────┘              └────────────────┘
```

## Features

### Dashboard
- **Live RSS/XML aggregation** from Google News PH
- **Severity filtering** with color-coded alerts
- **Provincial hazard sidebar** with Mindanao focus
- **People Status** tab - SOS/SAFE reports from Telegram
- **User Management** tab - Register users, broadcast alerts

### Telegram Integration
- Users send `/sos` or `/safe` to the bot
- Status updates reflect on dashboard automatically
- UptimeRobot pings `/health` endpoint every 5 min
- `/health` processes Telegram updates and keeps app alive

## Deployment

### 1. Push to GitHub
```bash
git add .
git commit -m "Add all files"
git push origin main
```

### 2. Deploy to Render.com (Free)
1. Go to https://render.com and sign in with GitHub
2. Click **"New +"** → **"Web Service"**
3. Connect **abamores/PhilDisaster** repo
4. Configure:
   - **Name:** `phil-disaster-monitor`
   - **Region:** Singapore
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python api_server.py`
5. Add Environment Variables:
   - `TELEGRAM_BOT_TOKEN` = `8938903628:AAGCXL5AgWsymcZAGmOOoe0d2ZHCMPHpzbM`
   - `TELEGRAM_CHAT_ID` = `59838581`
6. Click **"Create Web Service"**

### 3. Configure UptimeRobot (Free - keeps app alive)
1. Go to https://uptimerobot.com and sign up
2. Click **"Add New Monitor"**
3. Configure:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** PhilDisaster Health
   - **URL:** `https://phil-disaster-monitor.onrender.com/health`
   - **Monitoring Interval:** 5 minutes
4. Click **Create Monitor**

Now your app stays awake 24/7 and Telegram commands are processed on each UptimeRobot ping!

## Local Development

```bash
cd /Users/a2519/CLAUDE_WORKSPACE/disaster-monitor

# Start everything (Dashboard + API Server)
python3 launcher_combined.py

# Or start individually
python3 api_server.py          # API + Telegram polling
python3 -m streamlit run dashboard.py  # Dashboard only

# Dashboard: http://localhost:8501
# API Server: http://localhost:5000/health
```

## Telegram Commands (for users)
- `/sos` - Request emergency help
- `/safe` - Confirm you're safe
- `/status` - Check your status

## Project Structure

```
disaster-monitor/
├── api_server.py        # Flask API + Telegram polling
├── dashboard.py         # Streamlit dashboard
├── scraper.py          # RSS/XML feed parsing
├── bot_handler.py      # Telegram bot logic
├── monitor.py         # Disaster monitoring
├── health_check.py     # Standalone health check
├── launcher_combined.py # Start all components
├── requirements.txt    # Dependencies
├── Procfile           # Render deployment
├── render.yaml        # Render config
└── README.md
```