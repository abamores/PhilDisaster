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


if __name__ == "__main__":
    unittest.main()
