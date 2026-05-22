#!/usr/bin/env python3
"""
Automated Disaster Monitoring Workflow
Scrapes PHILVOLCS, PAGASA, GDACS, and ABS-CBN for major events
Sends Telegram alerts for State of Calamity declarations and M5.0+ earthquakes
Broadcasts to all registered users via bot_handler
"""

import schedule
import time
import json
import os
import sys
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import (
    scrape_all_feeds, check_and_alert, get_dashboard_data,
    HIGH_RISK_PROVINCES, MAJOR_EARTHQUAKE_MAG
)


class DisasterMonitor:
    def __init__(self, config_path: str = None):
        """Initialize the disaster monitor"""
        self.config = self.load_config(config_path)
        self.alert_history = []
        self.last_check = None

        # Load credentials
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or self.config.get("telegram_bot_token")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID") or self.config.get("telegram_chat_id")

        # State of Calamity keywords (expanded)
        self.calamity_keywords = [
            "state of calamity",
            "calamity declared",
            "national disaster",
            "state of national disaster",
            "provincial calamity",
            "municipal calamity",
            "barangay calamity",
            "executive order calamity",
            " declaration of calamity"
        ]

        # Major earthquake patterns
        self.major_quake_patterns = [
            r'\b(?:magnitude|mag|m)\s*[:\s]*([5-9]\d*(?:\.\d+)?)\b',
            r'\b(?:mag|m)[- ]?([5-9]\d*(?:\.\d+)?)\b',
            r'\b(?:intensity|scale)\s*[:\s]*([5-9]\d*(?:\.\d+)?)\b'
        ]

    def load_config(self, config_path: str = None) -> dict:
        """Load configuration from file"""
        if not config_path:
            config_path = os.path.join(os.path.dirname(__file__), "config.json")

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}

    def should_alert_calamity(self, event: dict) -> bool:
        """Check if event indicates State of Calamity declaration"""
        text = (event.get('title', '') + ' ' + event.get('description', '')).lower()

        for keyword in self.calamity_keywords:
            if keyword in text:
                return True
        return False

    def should_alert_earthquake(self, event: dict) -> bool:
        """Check if event is a major earthquake (M5.0+)"""
        if event.get('type') != 'earthquake':
            return False

        text = (event.get('title', '') + ' ' + event.get('description', '')).lower()

        import re
        for pattern in self.major_quake_patterns:
            match = re.search(pattern, text)
            if match:
                mag = float(match.group(1))
                if mag >= MAJOR_EARTHQUAKE_MAG:
                    return True
        return False

    def format_calamity_alert(self, event: dict) -> str:
        """Format a State of Calamity alert message"""
        from scraper import extract_location

        location = extract_location(event.get('title', '') + ' ' + event.get('description', ''))
        province_info = HIGH_RISK_PROVINCES.get(location, {})

        msg = "🚨 <b>⚠️ STATE OF CALAMITY DECLARED</b>\n\n"
        msg += f"<b>Location:</b> {location}\n"

        if province_info:
            msg += f"<b>Region:</b> {province_info.get('region', 'N/A')}\n"
            msg += f"<b>Hazard Types:</b> {', '.join(province_info.get('hazards', []))}\n"

        msg += f"<b>Source:</b> {event.get('source', 'UNKNOWN')}\n"

        published = event.get('published')
        if isinstance(published, datetime):
            msg += f"<b>Time:</b> {published.strftime('%Y-%m-%d %H:%M')}\n\n"
        else:
            msg += f"<b>Time:</b> {str(published)[:16]}\n\n"

        msg += f"<b>Alert:</b> {event.get('title', 'No title')}\n\n"
        msg += f"<i>{event.get('description', '')[:200]}...</i>\n\n"

        link = event.get('link', '')
        if link:
            msg += f"🔗 <a href='{link}'>View Official Source</a>\n\n"

        msg += "⚠️ <b>RECOMMENDED ACTIONS:</b>\n"
        msg += "• Stay alert and monitor official channels\n"
        msg += "• Prepare emergency supplies (water, food, medicine)\n"
        msg += "• Know your evacuation routes and shelter locations\n"
        msg += "• Follow instructions from local authorities\n"
        msg += "• Check on vulnerable family members and neighbors\n"

        return msg

    def format_earthquake_alert(self, event: dict) -> str:
        """Format a major earthquake alert message"""
        from scraper import extract_location
        import re

        location = extract_location(event.get('title', '') + ' ' + event.get('description', ''))

        # Extract magnitude
        text = (event.get('title', '') + ' ' + event.get('description', '')).lower()
        mag = "Unknown"
        for pattern in self.major_quake_patterns:
            match = re.search(pattern, text)
            if match:
                mag = match.group(1)
                break

        province_info = HIGH_RISK_PROVINCES.get(location, {})

        # Depth if available
        depth_match = re.search(r'depth\s*[:\s]*(\d+)\s*km', text)
        depth = f"{depth_match.group(1)} km" if depth_match else "N/A"

        msg = f"🌋 <b>⚠️ MAJOR EARTHQUAKE M{mag}</b>\n\n"
        msg += f"<b>Location:</b> {location}\n"

        if province_info:
            msg += f"<b>Region:</b> {province_info.get('region', 'N/A')}\n"
            msg += f"<b>Risk Hazards:</b> {', '.join(province_info.get('hazards', []))}\n"

        msg += f"<b>Depth:</b> {depth}\n"
        msg += f"<b>Source:</b> {event.get('source', 'PHILVOLCS')}\n"

        published = event.get('published')
        if isinstance(published, datetime):
            msg += f"<b>Time:</b> {published.strftime('%Y-%m-%d %H:%M')}\n\n"
        else:
            msg += f"<b>Time:</b> {str(published)[:16]}\n\n"

        msg += f"<b>Event:</b> {event.get('title', 'Seismic Activity')}\n\n"
        msg += f"<i>{event.get('description', '')[:200]}...</i>\n\n"

        link = event.get('link', '')
        if link:
            msg += f"🔗 <a href='{link}'>View Official Source</a>\n\n"

        # Safety reminders
        msg += "⚠️ <b>SAFETY REMINDERS:</b>\n"
        msg += "• If you feel shaking, DROP, COVER, and HOLD ON\n"
        msg += "• Stay away from windows and heavy objects\n"
        msg += "• Be prepared for aftershocks\n"
        msg += "• Check for injuries and damage around you\n"
        msg += "• Monitor official channels for updates\n"

        return msg

    def send_telegram(self, message: str) -> bool:
        """Send message via Telegram - broadcasts to all registered users"""
        if not self.bot_token:
            print("⚠️ Telegram bot token not configured.")
            return False

        # Import broadcast function
        try:
            from bot_handler import broadcast_message
        except ImportError:
            print("⚠️ bot_handler not available. Install it first.")
            return False

        # Broadcast to all registered users
        result = broadcast_message(self.bot_token, message)

        if result["sent"]:
            print(f"   ✅ Broadcast sent to {len(result['sent'])} users")
            return True
        else:
            print(f"   ⚠️ No users subscribed yet (or broadcast failed)")
            # Fallback: try sending to the default chat_id if configured
            if self.chat_id:
                try:
                    import requests
                    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                    response = requests.post(url, json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": "HTML"
                    }, timeout=10)
                    if response.json().get("ok"):
                        print(f"   ✅ Fallback: sent to default chat_id")
                        return True
                except:
                    pass
            return False

    def run_monitoring_cycle(self) -> Dict:
        """Run one monitoring cycle - scrape and alert"""
        print(f"\n{'='*60}")
        print(f"🔍 MONITORING CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # Scrape all feeds
        print("📡 Fetching feeds...")
        data = get_dashboard_data()
        events = data['events']
        print(f"   Total events fetched: {len(events)}")

        alerts_sent = []

        # Check each event for alert conditions
        for event in events:
            alert_msg = None
            alert_type = None

            # Check State of Calamity
            if self.should_alert_calamity(event):
                alert_msg = self.format_calamity_alert(event)
                alert_type = "CALAMITY"

            # Check major earthquake
            elif self.should_alert_earthquake(event):
                alert_msg = self.format_earthquake_alert(event)
                alert_type = "EARTHQUAKE"

            # Send alert if conditions met
            if alert_msg:
                print(f"\n🚨 {alert_type} ALERT DETECTED!")
                print(f"   Event: {event.get('title', '')[:80]}...")

                success = self.send_telegram(alert_msg)
                alerts_sent.append({
                    "type": alert_type,
                    "title": event.get('title', ''),
                    "sent": success,
                    "time": datetime.now().isoformat()
                })

                if success:
                    print(f"   ✅ Telegram alert sent")
                else:
                    print(f"   ❌ Telegram alert failed")

        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"   Events processed: {len(events)}")
        print(f"   Alerts sent: {len(alerts_sent)}")

        self.last_check = datetime.now()
        self.alert_history.extend(alerts_sent)

        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]

        return {
            "events_count": len(events),
            "alerts_sent": len(alerts_sent),
            "alerts": alerts_sent,
            "timestamp": datetime.now().isoformat()
        }

    def get_status_report(self) -> str:
        """Generate a status report"""
        report = "📊 <b>DISASTER MONITOR STATUS</b>\n\n"
        report += f"<b>Last Check:</b> {self.last_check.strftime('%Y-%m-%d %H:%M:%S') if self.last_check else 'Never'}\n"
        report += f"<b>Total Alerts Sent:</b> {len(self.alert_history)}\n\n"

        # Recent alerts
        if self.alert_history:
            report += "<b>Recent Alerts:</b>\n"
            for alert in self.alert_history[-5:]:
                status = "✅" if alert.get('sent') else "❌"
                report += f"{status} [{alert.get('time', '')[:16]}] {alert.get('type')}: {alert.get('title', '')[:50]}...\n"

        return report

    def run_scheduler(self, interval_minutes: int = 15):
        """Run the monitoring scheduler"""
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║        🌏 PHILIPPINE DISASTER MONITORING SYSTEM               ║
║                                                              ║
║  Monitoring: PHILVOLCS | PAGASA | GDACS | ABS-CBN            ║
║  Alert Triggers: State of Calamity, M5.0+ Earthquakes        ║
║  Interval: Every {interval_minutes} minutes                                        ║
╚══════════════════════════════════════════════════════════════╝
        """)

        # Run initial check
        print("\n🚀 Initializing...")
        self.run_monitoring_cycle()

        # Schedule recurring checks
        schedule.every(interval_minutes).minutes.do(self.run_monitoring_cycle)

        # Also run on the hour
        schedule.every().hour.do(self.run_monitoring_cycle)

        print(f"\n⏰ Scheduler running. Press Ctrl+C to stop.")
        print(f"   Next check in {interval_minutes} minutes...")

        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            print("\n\n🛑 Scheduler stopped.")
            print("\n📊 Final Status:")
            print(self.get_status_report())


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Philippine Disaster Monitoring System")
    parser.add_argument("--interval", "-i", type=int, default=15,
                        help="Check interval in minutes (default: 15)")
    parser.add_argument("--once", action="store_true",
                        help="Run single check and exit")
    parser.add_argument("--status", action="store_true",
                        help="Show current status and exit")

    args = parser.parse_args()

    monitor = DisasterMonitor()

    if args.status:
        print(monitor.get_status_report())
    elif args.once:
        result = monitor.run_monitoring_cycle()
        print(f"\n✅ Completed. Events: {result['events_count']}, Alerts: {result['alerts_sent']}")
    else:
        monitor.run_scheduler(interval_minutes=args.interval)


if __name__ == "__main__":
    main()