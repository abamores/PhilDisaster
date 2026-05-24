import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import scraper


class EventSortingTests(unittest.TestCase):
    def test_scrape_all_feeds_orders_events_newest_first_by_published_date(self):
        feeds = {
            "TEST": {
                "feeds": [
                    {"url": "https://example.com/one.xml", "type": "general", "source": "ONE"},
                    {"url": "https://example.com/two.xml", "type": "general", "source": "TWO"},
                ]
            }
        }
        middle_event = {"title": "middle", "published": "2024-05-02T02:00:00Z"}
        undated_event = {"title": "undated"}
        old_event = {"title": "old", "published": datetime(2024, 5, 1, 12, tzinfo=timezone.utc)}
        newest_event = {"title": "newest", "published": datetime(2024, 5, 3, 8)}

        with patch.object(scraper, "FEEDS", feeds), patch.object(
            scraper,
            "parse_rss_feed",
            side_effect=[[middle_event, undated_event], [old_event, newest_event]],
        ):
            events = scraper.scrape_all_feeds()

        self.assertEqual(
            [event["title"] for event in events],
            ["newest", "middle", "old", "undated"],
        )

    def test_pagasa_titles_sort_by_event_date_when_feed_dates_match(self):
        feed_timestamp = datetime(2026, 5, 24, 20, tzinfo=timezone.utc)
        events = [
            {
                "title": 'may 9',
                "description": 'As of 8:00 AM today, 09 May 2026, Tropical Storm "HAGUPIT" is monitored.',
                "published": feed_timestamp,
            },
            {
                "title": 'april 9',
                "description": 'As of 2:00 AM today, 09 April 2026, the Tropical Depression is monitored.',
                "published": feed_timestamp,
            },
            {
                "title": 'may 5',
                "description": 'As of 8:00 PM today, 05 May 2026, the Low Pressure Area is monitored.',
                "published": feed_timestamp,
            },
            {
                "title": 'may 14',
                "description": 'As of 8:00 AM today, 14 May 2026, a Low Pressure Area is monitored.',
                "published": feed_timestamp,
            },
        ]

        sorted_events = scraper.sort_events_by_published(events)

        self.assertEqual(
            [event["title"] for event in sorted_events],
            ["may 14", "may 9", "may 5", "april 9"],
        )


if __name__ == "__main__":
    unittest.main()
