"""
Disaster Monitoring Dashboard
Aggregates RSS/XML feeds from PHILVOLCS, PAGASA, GDACS, and ABS-CBN Calamity Hub
Features:
- Live monitoring dashboard with severity filtering
- Provincial hazard status sidebar (Mindanao focus)
- Telegram alerts for State of Calamity and M5.0+ earthquakes
"""

import feedparser
import requests
from datetime import datetime, timedelta
from typing import Optional
import re
import json
import os

# ==================== FEED CONFIGURATION ====================

# Working RSS feeds (verified 2026-05-22)
FEEDS = {
    "PHILVOLCS": {
        "name": "PHILVOLCS Seismic",
        "feeds": [
            # PHILVOLCS site has SSL issues - use Google News for PH seismic coverage
            {
                "url": "https://news.google.com/rss?q=PHILVOLCS+earthquake+Philippines&hl=en-PH&gl=PH&ceid=PH:en",
                "type": "earthquake",
                "source": "PHILVOLCS"
            },
            {
                "url": "https://news.google.com/rss?q=Philippines+seismic+activity+volcano&hl=en-PH&gl=PH&ceid=PH:en",
                "type": "volcanic",
                "source": "PHILVOLCS"
            }
        ]
    },
    "PAGASA": {
        "name": "PAGASA Weather",
        "feeds": [
            {
                "url": "https://news.google.com/rss?q=PAGASA+weather+Philippines&hl=en-PH&gl=PH&ceid=PH:en",
                "type": "weather",
                "source": "PAGASA"
            },
            {
                "url": "https://news.google.com/rss?q=tropical+cyclone+Philippines+PAGASA&hl=en-PH&gl=PH&ceid=PH:en",
                "type": "cyclone",
                "source": "PAGASA"
            }
        ]
    },
    "GDACS": {
        "name": "GDACS Global Disasters",
        "feeds": [
            {
                "url": "https://www.gdacs.org/rss/alertRSS/Asia.xml",
                "type": "disaster",
                "source": "GDACS"
            }
        ]
    },
    "NEWS": {
        "name": "Philippine Disaster News",
        "feeds": [
            {
                "url": "https://news.google.com/rss?q=Philippines+earthquake+typhoon+flood+disaster&hl=en-PH&gl=PH&ceid=PH:en",
                "type": "general",
                "source": "Google News PH"
            },
            {
                "url": "https://news.google.com/rss?q=Mindanao+earthquake+flood+landslide+typhoon&hl=en-PH&gl=PH&ceid=PH:en",
                "type": "mindanao",
                "source": "Google News PH"
            },
            {
                "url": "https://news.google.com/rss?q=Philippines+state+of+calamity+declared&hl=en-PH&gl=PH&ceid=PH:en",
                "type": "calamity",
                "source": "Google News PH"
            },
            {
                "url": "https://news.google.com/rss?q=Luzon+Visayas+typhoon+flood+landslide&hl=en-PH&gl=PH&ceid=PH:en",
                "type": "luzon_visayas",
                "source": "Google News PH"
            }
        ]
    }
}

# Philippine provinces for sidebar (with risk levels)
HIGH_RISK_PROVINCES = {
    # Mindanao - highest seismic risk
    "Davao Oriental": {"region": "Davao", "risk": "high", "hazards": ["earthquake", "landslide", "flood"]},
    "Davao del Norte": {"region": "Davao", "risk": "high", "hazards": ["flood", "landslide"]},
    "Davao del Sur": {"region": "Davao", "risk": "high", "hazards": ["earthquake", "flood"]},
    "Davao de Oro": {"region": "Davao", "risk": "high", "hazards": ["landslide", "flood"]},
    "Compostela Valley": {"region": "Davao", "risk": "high", "hazards": ["landslide", "flood"]},
    "Surigao del Norte": {"region": "Caraga", "risk": "high", "hazards": ["earthquake", "tsunami"]},
    "Surigao del Sur": {"region": "Caraga", "risk": "high", "hazards": ["earthquake", "flood"]},
    "Agusan del Norte": {"region": "Caraga", "risk": "medium", "hazards": ["flood", "landslide"]},
    "Agusan del Sur": {"region": "Caraga", "risk": "medium", "hazards": ["flood"]},
    "Bukidnon": {"region": "Northern Mindanao", "risk": "high", "hazards": ["landslide", "earthquake"]},
    "Lanao del Norte": {"region": "Northern Mindanao", "risk": "high", "hazards": ["flood", "landslide"]},
    "Lanao del Sur": {"region": "ARMM", "risk": "high", "hazards": ["conflict", "flood"]},
    "Maguindanao": {"region": "ARMM", "risk": "medium", "hazards": ["flood"]},
    "Sultan Kudarat": {"region": "Soccsksargen", "risk": "medium", "hazards": ["flood", "landslide"]},
    "South Cotabato": {"region": "Soccsksargen", "risk": "medium", "hazards": ["earthquake", "flood"]},
    "Sultan Kudarat": {"region": "Soccsksargen", "risk": "medium", "hazards": ["flood", "landslide"]},
    "Zamboanga del Norte": {"region": "Zamboanga", "risk": "high", "hazards": ["earthquake", "flood"]},
    "Zamboanga del Sur": {"region": "Zamboanga", "risk": "high", "hazards": ["earthquake", "landslide"]},
    "Zamboanga Sibuguey": {"region": "Zamboanga", "risk": "medium", "hazards": ["flood"]},
    "Misamis Occidental": {"region": "Northern Mindanao", "risk": "medium", "hazards": ["flood"]},
    "Misamis Oriental": {"region": "Northern Mindanao", "risk": "high", "hazards": ["earthquake", "flood"]},
    # Luzon - volcanic and seismic
    "Bulacan": {"region": "Central Luzon", "risk": "medium", "hazards": ["flood"]},
    "Pampanga": {"region": "Central Luzon", "risk": "high", "hazards": ["volcanic", "flood"]},
    "Tarlac": {"region": "Central Luzon", "risk": "medium", "hazards": ["flood"]},
    "Bataan": {"region": "Central Luzon", "risk": "medium", "hazards": ["flood"]},
    "Nueva Ecija": {"region": "Central Luzon", "risk": "high", "hazards": ["flood", "earthquake"]},
    "Quezon": {"region": "CALABARZON", "risk": "high", "hazards": ["typhoon", "flood", "landslide"]},
    "Aurora": {"region": "Central Luzon", "risk": "high", "hazards": ["typhoon", "flood"]},
    # Visayas
    "Leyte": {"region": "Eastern Visayas", "risk": "high", "hazards": ["typhoon", "storm surge", "landslide"]},
    "Samar": {"region": "Eastern Visayas", "risk": "high", "hazards": ["typhoon", "flood"]},
    "Cebu": {"region": "Central Visayas", "risk": "medium", "hazards": ["earthquake", "flood"]},
    "Iloilo": {"region": "Western Visayas", "risk": "medium", "hazards": ["flood", "typhoon"]},
    "Negros Occidental": {"region": "Western Visayas", "risk": "medium", "hazards": ["flood", "landslide"]},
}

# Severity thresholds
MAJOR_EARTHQUAKE_MAG = 5.0
MAJOR_WEATHER_CODE = ["TCWS-3", "TCWS-4", "TCWS-5", "STORM-3", "STORM-4", "STORM-5"]  # typhoon signal


# ==================== SCRAPER FUNCTIONS ====================

def parse_rss_feed(url: str, feed_type: str = "general", source: str = "UNKNOWN") -> list:
    """Parse RSS/XML feed and return structured events"""
    events = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # Parse feed content
        feed = feedparser.parse(response.content)

        for entry in feed.entries[:30]:  # Limit to 30 latest
            # Extract description/summary
            desc = entry.get("summary", entry.get("description", ""))
            if hasattr(entry, 'content') and entry.content:
                desc = entry.content[0].value if entry.content else desc

            # For Google News, extract from content snippet
            if source == "Google News PH":
                # Parse Google News-specific format
                title = entry.get("title", "No Title")
                # Clean up title (often has source at end)
                if " - " in title:
                    title = title.split(" - ")[0]

                event = {
                    "title": title,
                    "description": clean_html(desc),
                    "link": entry.get("link", ""),
                    "published": parse_date(entry.get("published", entry.get("updated", ""))),
                    "source": source,
                    "type": feed_type,
                    "severity": "low",
                    "raw": entry
                }
            else:
                event = {
                    "title": entry.get("title", "No Title"),
                    "description": clean_html(desc),
                    "link": entry.get("link", ""),
                    "published": parse_date(entry.get("published", entry.get("updated", ""))),
                    "source": source,
                    "type": feed_type,
                    "severity": "low",
                    "raw": entry
                }

            # Determine severity based on type and content
            event["severity"] = determine_severity(event, feed_type)

            events.append(event)

    except Exception as e:
        print(f"Error fetching {url}: {e}")

    return events


def clean_html(text: str) -> str:
    """Remove HTML tags and clean text"""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Decode HTML entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    return text[:500]  # Limit length


def parse_date(date_str: str) -> datetime:
    """Parse various date formats"""
    if not date_str:
        return datetime.now()

    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%d %b %Y %H:%M:%S",
        "%Y-%m-%d"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue

    return datetime.now()


def determine_severity(event: dict, feed_type: str) -> str:
    """Determine event severity based on content analysis"""
    title = event.get("title", "").lower()
    desc = event.get("description", "").lower()

    text = title + " " + desc

    if feed_type == "earthquake":
        # Extract magnitude from text
        mag_match = re.search(r'(?:magnitude|mag|m)\s*[:\s]*(\d+\.?\d*)', text)
        if mag_match:
            mag = float(mag_match.group(1))
            if mag >= MAJOR_EARTHQUAKE_MAG:
                return "critical"
            elif mag >= 4.0:
                return "high"
            elif mag >= 3.0:
                return "medium"

    if feed_type in ["cyclone", "weather", "flood"]:
        for code in MAJOR_WEATHER_CODE:
            if code.lower() in text:
                return "critical"

    # Check for calamity declarations
    if any(kw in text for kw in ["state of calamity", "calamity declared", "national disaster"]):
        return "critical"

    # Check for warning keywords
    warning_keywords = ["warning", "alert", "danger", "severe", "extreme", "major"]
    if any(kw in text for kw in warning_keywords):
        return "high"

    return "low"


def scrape_all_feeds() -> list:
    """Scrape all configured feeds and return aggregated events"""
    all_events = []

    for source_key, source_data in FEEDS.items():
        for feed_config in source_data["feeds"]:
            events = parse_rss_feed(
                feed_config["url"],
                feed_config["type"],
                feed_config["source"]
            )
            all_events.extend(events)

    # Sort by date (newest first)
    all_events.sort(key=lambda x: x.get("published", datetime.now()), reverse=True)

    return all_events


def filter_by_severity(events: list, min_severity: str = "low") -> list:
    """Filter events by minimum severity level"""
    severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    min_level = severity_order.get(min_severity, 0)

    return [
        e for e in events
        if severity_order.get(e.get("severity", "low"), 0) >= min_level
    ]


def extract_location(text: str) -> str:
    """Extract location from text (Philippine provinces)"""
    for province in HIGH_RISK_PROVINCES.keys():
        if province.lower() in text.lower():
            return province
    return "Unknown"


def get_province_status(province: str, events: list) -> dict:
    """Get hazard status for a province based on recent events"""
    province_lower = province.lower()
    matching_events = [
        e for e in events
        if province_lower in (e.get("title", "") + " " + e.get("description", "")).lower()
    ]

    if not matching_events:
        return {"status": "normal", "active_events": 0, "severity": "low"}

    max_severity = max(matching_events, key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(x.get("severity", "low"), 0))

    severity = max_severity.get("severity", "low")
    status_map = {
        "low": "normal",
        "medium": "advisory",
        "high": "watch",
        "critical": "emergency"
    }

    return {
        "status": status_map.get(severity, "normal"),
        "active_events": len(matching_events),
        "severity": severity,
        "latest_event": matching_events[0].get("title", "")[:100]
    }


# ==================== TELEGRAM ALERTS ====================

def send_telegram_alert(message: str, bot_token: str = None, chat_id: str = None) -> bool:
    """Send alert via Telegram bot"""
    if not bot_token:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram credentials not configured. Skipping alert.")
        return False

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram alert failed: {e}")
        return False


def check_and_alert(events: list) -> list:
    """Check events for alert conditions and send Telegram alerts"""
    alerts_sent = []

    for event in events:
        should_alert = False
        alert_type = None
        severity = event.get("severity", "low")

        # Check for State of Calamity
        text = (event.get("title", "") + " " + event.get("description", "")).lower()
        if "state of calamity" in text or "calamity declared" in text:
            should_alert = True
            alert_type = "STATE OF CALAMITY"

        # Check for major earthquake (M5.0+)
        if event.get("type") == "earthquake" and severity in ["high", "critical"]:
            # Extract magnitude
            mag_match = re.search(r'(?:magnitude|mag|m)\s*[:\s]*(\d+\.?\d*)', text)
            if mag_match and float(mag_match.group(1)) >= MAJOR_EARTHQUAKE_MAG:
                should_alert = True
                alert_type = f"MAJOR EARTHQUAKE M{mag_match.group(1)}"

        if should_alert:
            # Format alert message
            location = extract_location(event.get("title", "") + " " + event.get("description", ""))
            province_info = HIGH_RISK_PROVINCES.get(location, {})

            alert_msg = f"🚨 <b>{alert_type}</b>\n\n"
            alert_msg += f"<b>Location:</b> {location}\n"
            if province_info:
                alert_msg += f"<b>Region:</b> {province_info.get('region', 'N/A')}\n"
                alert_msg += f"<b>Hazard Types:</b> {', '.join(province_info.get('hazards', []))}\n"
            alert_msg += f"<b>Source:</b> {event.get('source', 'UNKNOWN')}\n"
            alert_msg += f"<b>Time:</b> {event.get('published', datetime.now()).strftime('%Y-%m-%d %H:%M')}\n\n"
            alert_msg += f"<b>Details:</b> {event.get('title', 'No title')}\n\n"
            alert_msg += f"🔗 <a href='{event.get('link', '')}'>View Official Source</a>\n\n"
            alert_msg += "⚠️ <b>Recommended Actions:</b>\n"
            alert_msg += "• Stay alert and monitor official channels\n"
            alert_msg += "• Prepare emergency supplies\n"
            alert_msg += "• Know your evacuation routes\n"

            success = send_telegram_alert(alert_msg)
            alerts_sent.append({
                "event": event.get("title"),
                "type": alert_type,
                "sent": success
            })

    return alerts_sent


# ==================== DASHBOARD DATA ====================

def get_dashboard_data():
    """Get all data needed for the dashboard"""
    events = scrape_all_feeds()

    # Aggregate by source
    by_source = {}
    for event in events:
        source = event.get("source", "Unknown")
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(event)

    # Get province statuses
    province_statuses = {}
    for province, info in HIGH_RISK_PROVINCES.items():
        province_statuses[province] = {
            **info,
            **get_province_status(province, events)
        }

    return {
        "events": events,
        "by_source": by_source,
        "province_statuses": province_statuses,
        "total_events": len(events),
        "timestamp": datetime.now()
    }


if __name__ == "__main__":
    # Test scraper
    print("Testing disaster monitoring scraper...")
    data = get_dashboard_data()
    print(f"Total events: {data['total_events']}")
    print(f"Sources: {list(data['by_source'].keys())}")