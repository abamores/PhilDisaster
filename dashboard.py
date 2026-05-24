"""
Philippine Disaster Monitoring Dashboard
Real-time monitoring of seismic, weather, and global disaster events
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import (
    scrape_all_feeds, filter_by_severity, get_province_status,
    HIGH_RISK_PROVINCES, get_dashboard_data, sort_events_by_published
)

# Bot handler imports - will be loaded dynamically to allow API server mode
def load_bot_handler():
    """Lazy load bot_handler to allow running without it"""
    try:
        from bot_handler import (
            get_all_statuses, get_registered_users, save_users, load_users,
            broadcast_message, send_broadcast_from_monitor
        )
        return True
    except ImportError:
        return False

BOT_HANDLER_AVAILABLE = load_bot_handler()

# ==================== PAGE CONFIG ====================

st.set_page_config(
    page_title="Philippine Disaster Monitor",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .severity-critical { background-color: #FF4444; color: white; padding: 0.5rem; border-radius: 0.3rem; }
    .severity-high { background-color: #FF8C00; color: white; padding: 0.5rem; border-radius: 0.3rem; }
    .severity-medium { background-color: #FFD700; color: black; padding: 0.5rem; border-radius: 0.3rem; }
    .severity-low { background-color: #4CAF50; color: white; padding: 0.5rem; border-radius: 0.3rem; }
    .province-card {
        background-color: #f8f9fa;
        border-left: 4px solid #ccc;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-radius: 0.2rem;
    }
    .province-emergency { border-left-color: #FF4444; background-color: #FFE5E5; }
    .province-watch { border-left-color: #FF8C00; background-color: #FFF3E5; }
    .province-advisory { border-left-color: #FFD700; background-color: #FFFFF0; }
    .province-normal { border-left-color: #4CAF50; background-color: #E8F5E9; }
    .metric-card {
        background-color: #f0f4f8;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
    }
    .source-philvolcs { color: #0066CC; }
    .source-pagasa { color: #00AA44; }
    .source-gdacs { color: #FF6600; }
    .source-abs-cbn { color: #CC0000; }
</style>
""", unsafe_allow_html=True)


# ==================== SIDEBAR ====================

def render_sidebar():
    """Render the provincial hazard status sidebar"""

    with st.sidebar:
        st.markdown("## 🗺️ Provincial Hazard Status")
        st.markdown("**Mindanao & High-Risk Areas**")
        st.markdown("---")

        # Group provinces by region
        regions = {}
        for province, info in HIGH_RISK_PROVINCES.items():
            region = info.get("region", "Other")
            if region not in regions:
                regions[region] = []
            regions[region].append((province, info))

        # Show provinces with active alerts first
        if 'province_statuses' in st.session_state and st.session_state.province_statuses:
            # Sort provinces: emergency > watch > advisory > normal
            def sort_key(item):
                province, status = item
                order = {"emergency": 0, "watch": 1, "advisory": 2, "normal": 3}
                return order.get(status.get("status", "normal"), 3)

            all_provinces = list(st.session_state.province_statuses.items())
            all_provinces.sort(key=sort_key)

            for province, status in all_provinces:
                status_class = f"province-{status.get('status', 'normal')}"

                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{province}**")
                        st.caption(f"{status.get('status', 'normal').upper()}")
                    with col2:
                        if status.get('active_events', 0) > 0:
                            st.markdown(f"🔴 {status.get('active_events')}")
                        else:
                            st.markdown("🟢")

                    if status.get('latest_event'):
                        with st.expander("Details"):
                            st.caption(status.get('latest_event', '')[:100])

                    st.markdown("---")
        else:
            st.info("Loading province data...")

        # Legend
        st.markdown("### Status Legend")
        st.markdown("🔴 **Emergency** - Critical active threat")
        st.markdown("🟠 **Watch** - Significant hazard")
        st.markdown("🟡 **Advisory** - Monitor closely")
        st.markdown("🟢 **Normal** - No active alerts")

        st.markdown("---")
        st.markdown("### Settings")

        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)

        # Severity filter
        min_severity = st.select_slider(
            "Minimum Severity",
            options=["low", "medium", "high", "critical"],
            value="low"
        )

        return auto_refresh, min_severity


# ==================== SOS STATUS PANEL ====================

def render_sos_status():
    """Render SOS/SAFE status panel from Telegram responses"""

    # Check if bot handler is available
    if not BOT_HANDLER_AVAILABLE:
        st.warning("⚠️ Bot handler not available. SOS status updates won't work until bot_handler.py is run.")
        st.info("💡 Tip: Deploy api_server.py on Render to enable 24/7 Telegram polling")

        # Still try to load from files directly
        import os
        import json
        status_file = os.path.join(os.path.dirname(__file__), "status.json")
        users_file = os.path.join(os.path.dirname(__file__), "users.json")

        statuses = {}
        users = {}

        if os.path.exists(status_file):
            try:
                with open(status_file, 'r') as f:
                    statuses = json.load(f)
            except:
                pass

        if os.path.exists(users_file):
            try:
                with open(users_file, 'r') as f:
                    users = json.load(f)
            except:
                pass
    else:
        from bot_handler import get_all_statuses, get_registered_users
        statuses = get_all_statuses()
        users = get_registered_users()

    st.markdown("## 🆘 People Status Monitor")

    # Show registered users count
    st.markdown(f"""
    **👥 Registered Users:** {len(users)}

    To register, message **@PhilippineDisasterMonitoring_bot** on Telegram and send:
    - `/sos` - Request emergency help
    - `/safe` - Confirm you're safe
    - `/status` - Check your status
    """)

    st.markdown("---")

    if not statuses:
        st.info("📭 No one has reported status yet. All registered users should send /sos or /safe.")
        return

    # Summary metrics
    sos_count = sum(1 for s in statuses.values() if s.get('status') == 'SOS')
    safe_count = sum(1 for s in statuses.values() if s.get('status') == 'SAFE')
    unknown_count = len(statuses) - sos_count - safe_count

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔴 SOS", sos_count)
    with col2:
        st.metric("🟢 SAFE", safe_count)
    with col3:
        st.metric("⚪ Unknown", unknown_count)
    with col4:
        st.metric("📋 Total Reports", len(statuses))

    st.markdown("---")

    # SOS ALERTS - Show prominently
    sos_users = {uid: data for uid, data in statuses.items() if data.get('status') == 'SOS'}
    if sos_users:
        st.error("🚨 **SOS ALERTS - NEED IMMEDIATE ATTENTION**")
        for user_id, data in sorted(sos_users.items(), key=lambda x: x[1].get('timestamp', ''), reverse=True):
            timestamp = data.get('timestamp', 'Unknown')
            if isinstance(timestamp, str) and len(timestamp) > 16:
                timestamp = timestamp[:16]

            with st.container():
                col1, col2, col3, col4 = st.columns([1, 3, 2, 1])
                with col1:
                    st.markdown("### 🔴")
                with col2:
                    st.markdown(f"**🚨 {data.get('name', 'Unknown')}**")
                    if data.get('username'):
                        st.caption(f"@{data.get('username')}")
                    st.caption(f"Chat ID: {data.get('chat_id', user_id)}")
                with col3:
                    st.markdown(f"_{timestamp}_")
                with col4:
                    if st.button("Respond", key=f"sos_{user_id}"):
                        st.info(f"Response logged for {data.get('name')}")

                st.markdown("---")

    # SAFE users
    safe_users = {uid: data for uid, data in statuses.items() if data.get('status') == 'SAFE'}
    if safe_users:
        st.success(f"🟢 **{len(safe_users)} people SAFE**")
        for user_id, data in sorted(safe_users.items(), key=lambda x: x[1].get('timestamp', ''), reverse=True):
            timestamp = data.get('timestamp', 'Unknown')
            if isinstance(timestamp, str) and len(timestamp) > 16:
                timestamp = timestamp[:16]

            with st.container():
                col1, col2, col3 = st.columns([1, 3, 2])
                with col1:
                    st.markdown("### 🟢")
                with col2:
                    st.markdown(f"**{data.get('name', 'Unknown')}**")
                    if data.get('username'):
                        st.caption(f"@{data.get('username')}")
                with col3:
                    st.markdown(f"_{timestamp}_")

        st.markdown("---")


# ==================== USER MANAGEMENT TAB ====================

def render_user_management():
    """Render user management panel"""
    st.markdown("## 👥 User Registration & Management")

    # Telegram credentials
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or st.session_state.get("bot_token", "")

    # Load users from file directly
    import os
    import json
    users_file = os.path.join(os.path.dirname(__file__), "users.json")
    users = {}

    if os.path.exists(users_file):
        try:
            with open(users_file, 'r') as f:
                users = json.load(f)
        except:
            pass

    if not bot_token:
        st.warning("⚠️ Set TELEGRAM_BOT_TOKEN environment variable to enable broadcasts")
        bot_token = st.text_input("Or enter bot token here:", type="password", key="bot_token_input")
        if bot_token:
            st.session_state["bot_token"] = bot_token

    st.markdown("---")

    # Manual registration form
    st.markdown("### 📝 Register New User")

    with st.form("register_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            chat_id = st.text_input("Telegram Chat ID *", placeholder="e.g., 59838581")
            name = st.text_input("Name *", placeholder="e.g., Juan Dela Cruz")
        with col2:
            username = st.text_input("Telegram Username", placeholder="e.g., @juandelacruz")
            status = st.selectbox("Status", ["SAFE", "SOS", "UNKNOWN"])

        submitted = st.form_submit_button("Register User")
        if submitted and chat_id and name:
            users = load_users()
            users[chat_id] = {
                "chat_id": chat_id,
                "name": name,
                "username": username.replace("@", "") if username else "",
                "status": status,
                "status_timestamp": datetime.now().isoformat(),
                "registered_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            }
            save_users(users)
            st.success(f"✅ User {name} registered successfully!")

    st.markdown("---")

    # List registered users
    st.markdown("### 📋 Registered Users")

    users = get_registered_users()

    if not users:
        st.info("No users registered yet.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", len(users))
        with col2:
            st.metric("🟢 SAFE", sum(1 for u in users.values() if u.get('status') == 'SAFE'))
        with col3:
            st.metric("🔴 SOS", sum(1 for u in users.values() if u.get('status') == 'SOS'))
        with col4:
            st.metric("⚪ Unknown", sum(1 for u in users.values() if u.get('status') == 'UNKNOWN'))

        st.markdown("---")

        # User table
        for user_id, data in sorted(users.items(), key=lambda x: x[1].get('last_seen', ''), reverse=True):
            status = data.get('status', 'UNKNOWN')
            status_emoji = {"SOS": "🔴", "SAFE": "🟢"}.get(status, "⚪")

            with st.container():
                col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
                with col1:
                    st.markdown(f"### {status_emoji}")
                with col2:
                    st.markdown(f"**{data.get('name', 'Unknown')}**")
                    st.caption(f"@{data.get('username', 'N/A')} | ID: {data.get('chat_id')}")
                with col3:
                    st.markdown(f"**{status}**")
                    st.caption(f"Since: {str(data.get('registered_at', ''))[:10]}")
                with col4:
                    if st.button("Remove", key=f"remove_{user_id}"):
                        del users[user_id]
                        save_users(users)
                        st.rerun()

            st.markdown("---")

    # Broadcast section
    if bot_token:
        st.markdown("### 📢 Broadcast Alert to All Users")

        with st.form("broadcast_form"):
            broadcast_msg = st.text_area("Message to broadcast", placeholder="Enter alert message...")
            broadcast_submitted = st.form_submit_button("Send to All Users")

            if broadcast_submitted and broadcast_msg:
                result = broadcast_message(bot_token, broadcast_msg)
                if result["sent"]:
                    st.success(f"✅ Message sent to {len(result['sent'])} users!")
                else:
                    st.error(f"❌ Failed to send. {len(result['failed'])} failed.")
                if result["failed"]:
                    st.write("Failed:", result["failed"])


# ==================== MAIN CONTENT ====================

def render_header():
    """Render the main header with summary metrics"""

    col1, col2, col3, col4 = st.columns(4)

    total = st.session_state.get('total_events', 0)
    critical = len([e for e in st.session_state.get('events', [])
                     if e.get('severity') == 'critical'])
    high = len([e for e in st.session_state.get('events', [])
                if e.get('severity') == 'high'])
    mindanao_active = len([
        e for e in st.session_state.get('events', [])
        if any(prov.lower() in (e.get('title', '') + ' ' + e.get('description', '')).lower()
               for prov in ['davao', 'surigao', 'bukidnon', 'lanao', 'maguindanao', 'cotabato',
                           'zamboanga', 'misamis', 'agusan', 'compostela'])
    ])

    with col1:
        st.metric("Total Events", total)
    with col2:
        st.metric("Critical/High", f"{critical + high}", delta="Alert!" if critical > 0 else None)
    with col3:
        st.metric("Mindanao Events", mindanao_active)
    with col4:
        if st.session_state.get('timestamp'):
            age = (datetime.now() - st.session_state.timestamp).seconds
            st.metric("Last Updated", f"{age}s ago")


def render_source_tabs(events, min_severity="low"):
    """Render events organized by source with tabs"""
    events = sort_events_by_published(events)

    sources = {
        "All": events,
        "🌋 PHILVOLCS": [e for e in events if e.get("source") == "PHILVOLCS"],
        "🌦️ PAGASA": [e for e in events if e.get("source") == "PAGASA"],
        "🌍 GDACS": [e for e in events if e.get("source") == "GDACS"],
        "📺 ABS-CBN": [e for e in events if e.get("source") == "ABS-CBN"]
    }

    tabs = st.tabs(list(sources.keys()))

    for tab, (source_name, source_events) in zip(tabs, sources.items()):
        with tab:
            filtered = filter_by_severity(source_events, min_severity)
            filtered = sort_events_by_published(filtered)

            if not filtered:
                st.info(f"No events from {source_name} matching filter criteria")
                continue

            for event in filtered:
                render_event_card(event)


def render_event_card(event):
    """Render a single event card"""

    severity = event.get("severity", "low")
    severity_icons = {
        "critical": "🚨",
        "high": "⚠️",
        "medium": "📢",
        "low": "ℹ️"
    }

    with st.container():
        col1, col2 = st.columns([1, 4])

        with col1:
            st.markdown(f"### {severity_icons.get(severity, 'ℹ️')}")
            st.markdown(f"**{event.get('source', 'UNKNOWN')}")

        with col2:
            published = event.get("published")
            if isinstance(published, datetime):
                time_str = published.strftime("%b %d, %Y %H:%M")
            else:
                time_str = str(published)[:16]

            st.markdown(f"**{event.get('title', 'No Title')}**")
            st.caption(f"🕐 {time_str} | 🔖 {event.get('type', 'general').upper()}")

            st.markdown(event.get("description", "")[:300] + "..." if len(event.get("description", "")) > 300 else event.get("description", ""))

            # Link to source
            link = event.get("link", "")
            if link:
                st.markdown(f"[View Full Report →]({link})")

        st.markdown("---")


def render_mindanao_focus(events):
    """Render Mindanao-specific focused view"""

    st.markdown("## 🏝️ Mindanao Regional Focus")

    # Mindanao provinces
    mindanao_keywords = [
        'davao', 'surigao', 'bukidnon', 'lanao', 'maguindanao', 'cotabato',
        'zamboanga', 'misamis', 'agusan', 'compostela', 'basilan', 'sulu',
        'tawi', 'siargao', 'dinagat', 'camiguin', 'misamis'
    ]

    mindanao_events = [
        e for e in events
        if any(kw in (e.get('title', '') + ' ' + e.get('description', '')).lower()
               for kw in mindanao_keywords)
    ]
    mindanao_events = sort_events_by_published(mindanao_events)

    if not mindanao_events:
        st.success("✅ No active alerts for Mindanao region")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        st.warning(f"⚠️ **{len(mindanao_events)} active events** affecting Mindanao")
    with col2:
        severity_counts = {}
        for e in mindanao_events:
            sev = e.get('severity', 'low')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        for sev, count in severity_counts.items():
            emoji = {"critical": "🚨", "high": "⚠️", "medium": "📢", "low": "ℹ️"}.get(sev, "•")
            st.markdown(f"{emoji} {sev.title()}: {count}")

    st.markdown("---")

    for event in mindanao_events:
        render_event_card(event)


def main():
    """Main dashboard rendering"""

    st.markdown('<p class="main-header">🌏 Philippine Disaster Monitor</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time monitoring: PHILVOLCS • PAGASA • GDACS • ABS-CBN</p>', unsafe_allow_html=True)

    # Initialize session state
    if 'events' not in st.session_state:
        st.session_state.events = []
        st.session_state.province_statuses = {}
        st.session_state.timestamp = None

    # Sidebar
    auto_refresh, min_severity = render_sidebar()

    # Refresh data
    if st.button("🔄 Refresh Now") or not st.session_state.events:
        with st.spinner("Fetching latest data..."):
            data = get_dashboard_data()
            st.session_state.events = data['events']
            st.session_state.province_statuses = data['province_statuses']
            st.session_state.timestamp = data['timestamp']
            st.session_state.total_events = data['total_events']

            # Count high-severity events (display only, no alerts)
            high_sev_count = len([e for e in st.session_state.events if e.get('severity') in ['critical', 'high']])
            if high_sev_count > 0:
                st.warning(f"⚠️ {high_sev_count} Critical/High severity events detected. Run monitor.py for Telegram alerts.")

    # Render header metrics
    render_header()

    st.markdown("---")

    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["📊 All Events", "🏝️ Mindanao Focus", "🆘 People Status", "👥 Users"])

    with tab1:
        render_source_tabs(st.session_state.events, min_severity)

    with tab2:
        render_mindanao_focus(st.session_state.events)

    with tab3:
        render_sos_status()

    with tab4:
        render_user_management()

    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()
