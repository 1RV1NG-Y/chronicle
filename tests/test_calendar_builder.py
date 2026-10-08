from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from chronicle.models.activity_event import BrowserEventSource
from chronicle.services.calendar_builder import build_calendar_events
from chronicle.services.event_normalizer import normalize_events


def window(second, duration, app, title=None):
    return {
        "timestamp": (datetime(2026, 8, 10, 9, tzinfo=timezone.utc) + timedelta(seconds=second)).isoformat(),
        "duration": duration,
        "data": {"app": app, "title": title or f"{app} context"},
    }


class CalendarBuilderTest(unittest.TestCase):
    def test_short_switches_group_without_assigning_time_to_a_different_app(self):
        ledger = normalize_events([
            window(0, 20, "code"), window(20, 20, "org.gnome.Terminal"), window(40, 120, "code"),
        ])
        calendar = build_calendar_events(ledger)
        self.assertEqual(len(calendar), 2)
        self.assertEqual(calendar[0].display_name, "Quick switches")
        self.assertEqual(calendar[0].duration_seconds, 40)
        self.assertEqual(calendar[0].activities, tuple(ledger[:2]))
        self.assertEqual(calendar[1], ledger[2])

    def test_same_app_session_retains_each_file_change(self):
        ledger = normalize_events([window(0, 120, "code", "one.py"), window(120, 120, "code", "two.py")])
        calendar = build_calendar_events(ledger)
        self.assertEqual(len(calendar), 1)
        self.assertEqual([item.title for item in calendar[0].activities], ["one.py", "two.py"])
        self.assertEqual(calendar[0].duration_seconds, 240)

    def test_gaps_are_not_bridged_or_counted_as_activity(self):
        ledger = normalize_events([window(0, 20, "code"), window(25, 20, "code")])
        self.assertEqual(build_calendar_events(ledger), ledger)

    def test_mixed_switch_groups_are_bounded(self):
        ledger = normalize_events([window(i * 40, 40, "code" if i % 2 else "terminal") for i in range(12)])
        calendar = build_calendar_events(ledger)
        self.assertTrue(all(item.duration_seconds <= 300 for item in calendar))
        self.assertEqual([child for group in calendar for child in (group.activities or (group,))], ledger)

    def test_idle_remains_an_exact_non_mergeable_boundary(self):
        ledger = normalize_events([window(0, 120, "code")], afk_events=[{
            "timestamp": "2026-08-10T09:00:40+00:00", "duration": 20, "data": {"status": "afk"},
        }])
        calendar = build_calendar_events(ledger)
        self.assertEqual(calendar, ledger)
        self.assertEqual(calendar[1].duration_seconds, 20)
        self.assertTrue(calendar[1].is_idle)

    def test_different_websites_remain_available_inside_a_short_group(self):
        ledger = normalize_events([window(0, 60, "brave-browser")], [
            BrowserEventSource("web-brave", "brave", {
                "timestamp": f"2026-08-10T09:00:{second:02d}+00:00", "duration": 30,
                "data": {"title": domain, "url": f"https://{domain}"},
            }) for second, domain in [(0, "github.com"), (30, "chatgpt.com")]
        ])
        calendar = build_calendar_events(ledger)
        flattened = [child for group in calendar for child in (group.activities or (group,))]
        self.assertEqual(flattened, ledger)
        self.assertEqual([item.domain for item in flattened], ["github.com", "chatgpt.com"])
        self.assertEqual(calendar[0].domain, "")


if __name__ == "__main__":
    unittest.main()
