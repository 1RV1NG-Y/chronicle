from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from chronicle.models.activity_event import BrowserEventSource
from chronicle.services.event_normalizer import (
    accent_for_app,
    display_name_for_app,
    normalize_events,
)


UTC = timezone.utc


def heartbeat(second: int, app: str, duration: float = 0) -> dict[str, object]:
    return {
        "id": second,
        "timestamp": (datetime(2026, 8, 10, 9, tzinfo=UTC) + timedelta(seconds=second)).isoformat(),
        "duration": duration,
        "data": {"app": app, "title": f"{app} window"},
    }


class NormalizeEventsTest(unittest.TestCase):
    def test_zero_duration_pulses_consolidate_into_one_positive_run(self) -> None:
        events = normalize_events(heartbeat(second, "code") for second in range(101))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].app_id, "code")
        self.assertEqual(events[0].duration_seconds, 100)
        self.assertEqual(events[0].source_count, 100)

    def test_unrecorded_gap_is_not_claimed_as_activity(self) -> None:
        events = normalize_events(
            [heartbeat(0, "brave-browser", 5), heartbeat(10, "brave-browser", 5)]
        )

        self.assertEqual(len(events), 2)
        self.assertEqual(sum(event.duration_seconds for event in events), 10)

    def test_meaningful_app_transitions_remain_distinct(self) -> None:
        events = normalize_events(
            [
                heartbeat(0, "code"),
                heartbeat(10, "org.gnome.Terminal"),
                heartbeat(20, "code"),
                heartbeat(30, "code"),
            ]
        )

        self.assertEqual([event.app_id for event in events], ["code", "org.gnome.Terminal", "code"])
        self.assertEqual([event.duration_seconds for event in events], [10, 10, 10])

    def test_even_two_second_app_switches_remain_inspectable(self) -> None:
        events = normalize_events(
            [
                heartbeat(0, "code"),
                heartbeat(10, "Codex-widget"),
                heartbeat(12, "code"),
                heartbeat(20, "code"),
            ]
        )

        self.assertEqual([event.app_id for event in events], ["code", "Codex-widget", "code"])
        self.assertEqual([event.duration_seconds for event in events], [10, 2, 8])

    def test_different_files_in_the_same_app_remain_separate(self) -> None:
        first = heartbeat(0, "code", 60)
        second = heartbeat(60, "code", 60)
        first["data"]["title"] = "controller.py — Chronicle"
        second["data"]["title"] = "Main.qml — Chronicle"
        events = normalize_events([first, second])
        self.assertEqual([event.title for event in events], ["controller.py — Chronicle", "Main.qml — Chronicle"])
        self.assertEqual([event.duration_seconds for event in events], [60, 60])

    def test_same_title_on_different_urls_remains_separate(self) -> None:
        sources = [
            BrowserEventSource("aw-watcher-web-brave_host", "brave", {
                "timestamp": f"2026-08-10T09:00:{second:02d}+00:00",
                "duration": 30,
                "data": {"title": "GitHub", "url": f"https://github.com/{path}"},
            })
            for second, path in [(0, "one"), (30, "two")]
        ]
        events = normalize_events([heartbeat(0, "brave-browser", 60)], sources)
        self.assertEqual([event.url for event in events], ["https://github.com/one", "https://github.com/two"])

    def test_unattached_or_large_gap_zero_duration_instants_are_dropped(self) -> None:
        events = normalize_events([heartbeat(0, "code"), heartbeat(30, "code")])
        self.assertEqual(events, [])

    def test_duplicate_afk_is_coalesced_and_masks_activity(self) -> None:
        windows = [heartbeat(0, "code", duration=600)]
        afk = [
            {
                "id": "afk-a",
                "timestamp": "2026-08-10T09:02:00+00:00",
                "duration": 120,
                "data": {"status": "afk"},
            },
            {
                "id": "afk-b",
                "timestamp": "2026-08-10T09:02:30+00:00",
                "duration": 90,
                "data": {"status": "afk"},
            },
        ]

        events = normalize_events(windows, afk_events=afk)
        idle = [event for event in events if event.is_idle]
        active = [event for event in events if not event.is_idle]

        self.assertEqual(len(idle), 1)
        self.assertEqual(idle[0].duration_seconds, 120)
        self.assertEqual(idle[0].source_count, 2)
        self.assertEqual([event.duration_seconds for event in active], [120, 360])
        for event in active:
            self.assertTrue(event.end_time <= idle[0].start_time or event.start_time >= idle[0].end_time)

    def test_all_outputs_are_positive_ordered_and_pairwise_non_overlapping(self) -> None:
        events = normalize_events(
            [heartbeat(0, "code", 40), heartbeat(20, "org.gnome.Terminal", 40)],
            afk_events=[
                {
                    "timestamp": "2026-08-10T09:00:25+00:00",
                    "duration": 10,
                    "data": {"status": "afk"},
                }
            ],
        )

        self.assertTrue(all(event.duration_seconds > 0 for event in events))
        for previous, current in zip(events, events[1:]):
            self.assertLessEqual(previous.end_time, current.start_time)

    def test_browser_context_is_provenance_and_is_not_reused(self) -> None:
        windows = [heartbeat(0, "brave-browser", 10), heartbeat(30, "brave-browser", 10)]
        browser = {
            "id": "tab-1",
            "timestamp": "2026-08-10T09:00:01+00:00",
            "duration": 8,
            "data": {
                "browser": "brave",
                "title": "Chronicle repository",
                "url": "https://github.com/example/chronicle",
            },
        }

        events = normalize_events(windows, [browser])

        website = [event for event in events if event.domain]
        self.assertEqual(len(events), 4)
        self.assertEqual(len(website), 1)
        self.assertEqual(website[0].domain, "github.com")
        self.assertEqual(website[0].title, "Chronicle repository")
        self.assertEqual(website[0].source_count, 2)
        provenance = json.loads(website[0].raw_json)
        self.assertEqual(provenance["browser"][0]["event"]["id"], "tab-1")
        self.assertEqual(provenance["browser"][0]["browser_id"], "brave")
        self.assertTrue(
            all("tab-1" not in event.raw_json for event in events if not event.domain)
        )


    def test_browser_run_is_split_into_exact_website_intervals(self) -> None:
        windows = [heartbeat(0, "brave-browser", 60)]
        browser = [
            BrowserEventSource(
                bucket_id="aw-watcher-web-brave_host",
                browser_id="brave",
                payload={
                    "id": "github",
                    "timestamp": "2026-08-10T09:00:00+00:00",
                    "duration": 30,
                    "data": {
                        "title": "GitHub",
                        "url": "https://github.com/example",
                    },
                },
            ),
            BrowserEventSource(
                bucket_id="aw-watcher-web-brave_host",
                browser_id="brave",
                payload={
                    "id": "chatgpt",
                    "timestamp": "2026-08-10T09:00:30+00:00",
                    "duration": 30,
                    "data": {
                        "title": "ChatGPT",
                        "url": "https://chatgpt.com/c/example",
                    },
                },
            ),
        ]

        events = normalize_events(windows, browser)

        self.assertEqual([event.domain for event in events], ["github.com", "chatgpt.com"])
        self.assertEqual(
            [event.url for event in events],
            ["https://github.com/example", "https://chatgpt.com/c/example"],
        )
        self.assertEqual([event.duration_seconds for event in events], [30, 30])
        self.assertEqual(sum(event.duration_seconds for event in events), 60)
        provenance = json.loads(events[0].raw_json)["browser"][0]
        self.assertEqual(provenance["bucket_id"], "aw-watcher-web-brave_host")
        self.assertEqual(provenance["url"], "https://github.com/example")

    def test_known_browser_identity_mismatch_fails_closed(self) -> None:
        browser = BrowserEventSource(
            bucket_id="aw-watcher-web-firefox_host",
            browser_id="firefox",
            payload={
                "timestamp": "2026-08-10T09:00:00+00:00",
                "duration": 30,
                "data": {"title": "Wrong browser", "url": "https://example.com"},
            },
        )

        events = normalize_events([heartbeat(0, "brave-browser", 30)], [browser])

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].domain, "")

    def test_ambiguous_chrome_bucket_does_not_claim_thorium(self) -> None:
        browser = BrowserEventSource(
            bucket_id="aw-watcher-web-chrome_host",
            browser_id="chrome",
            payload={
                "timestamp": "2026-08-10T09:00:00+00:00",
                "duration": 30,
                "data": {"title": "Page", "url": "https://example.com"},
            },
        )

        events = normalize_events([heartbeat(0, "thorium-browser", 30)], [browser])

        self.assertEqual(events[0].domain, "")

    def test_chrome_family_source_can_be_title_verified_for_thorium(self) -> None:
        browser = BrowserEventSource(
            bucket_id="aw-watcher-web-chrome_host",
            browser_id="chrome",
            payload={
                "timestamp": "2026-08-10T09:00:00+00:00",
                "duration": 30,
                "data": {"title": "ChatGPT", "url": "https://chatgpt.com/c/example"},
            },
        )
        windows = [
            {
                "timestamp": "2026-08-10T09:00:00+00:00",
                "duration": 30,
                "data": {"app": "Thorium-browser", "title": "ChatGPT - Thorium"},
            },
        ]

        event = normalize_events(windows, [browser])[0]

        self.assertEqual(event.domain, "chatgpt.com")
        self.assertEqual(event.url, "https://chatgpt.com/c/example")

    def test_internal_browser_pages_are_not_presented_as_websites(self) -> None:
        for url in ("brave://newtab", "chrome://newtab", "about:blank"):
            with self.subTest(url=url):
                browser = BrowserEventSource(
                    bucket_id="aw-watcher-web-brave_host",
                    browser_id="brave",
                    payload={
                        "timestamp": "2026-08-10T09:00:00+00:00",
                        "duration": 30,
                        "data": {"title": "Internal page", "url": url},
                    },
                )

                event = normalize_events(
                    [heartbeat(0, "brave-browser", 30)],
                    [browser],
                )[0]

                self.assertEqual(event.domain, "")
                self.assertEqual(event.url, url)
                self.assertTrue(event.is_browser)

    def test_reverse_dns_and_live_app_ids_are_readable(self) -> None:
        self.assertEqual(display_name_for_app("org.gnome.Terminal"), "Terminal")
        self.assertEqual(display_name_for_app("Thorium-browser"), "Thorium")
        self.assertEqual(display_name_for_app("Codex-widget"), "Codex Widget")

    def test_application_accents_are_distinct_and_stable(self) -> None:
        self.assertEqual(accent_for_app("brave-browser"), "#F2A65A")
        self.assertEqual(accent_for_app("Thorium-browser"), "#72B7F2")
        self.assertEqual(accent_for_app("org.gnome.Terminal"), "#B59AF4")
        self.assertEqual(accent_for_app("anything-else"), accent_for_app("anything-else"))
        self.assertEqual(accent_for_app("brave-browser", idle=True), "#414A57")

    def test_day_bounds_clip_intervals(self) -> None:
        start = datetime(2026, 8, 10, tzinfo=UTC)
        end = start + timedelta(days=1)
        events = normalize_events(
            [
                {
                    "timestamp": (start - timedelta(seconds=30)).isoformat(),
                    "duration": 60,
                    "data": {"app": "code", "title": "Editor"},
                }
            ],
            day_start=start,
            day_end=end,
        )
        self.assertEqual(events[0].start_time, start)
        self.assertEqual(events[0].duration_seconds, 30)


if __name__ == "__main__":
    unittest.main()
