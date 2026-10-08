from __future__ import annotations

import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from chronicle.api.activitywatch_client import ActivityWatchClient, ActivityWatchError


class RecordingClient(ActivityWatchClient):
    def __init__(self) -> None:
        super().__init__(
            hostname="workstation",
            local_timezone=ZoneInfo("America/New_York"),
        )
        self.calls: list[tuple[str, object, object]] = []

    def get_buckets(self):
        return {
            "aw-watcher-window_workstation": {
                "id": "aw-watcher-window_workstation",
                "type": "currentwindow",
                "hostname": "workstation",
            },
            "aw-watcher-window_foreign": {
                "id": "aw-watcher-window_foreign",
                "type": "currentwindow",
                "hostname": "foreign",
            },
            "aw-watcher-web-firefox_workstation": {
                "id": "aw-watcher-web-firefox_workstation",
                "type": "web.tab.current",
                "hostname": "workstation",
            },
            "aw-watcher-afk_workstation": {
                "id": "aw-watcher-afk_workstation",
                "type": "afkstatus",
                "hostname": "workstation",
            },
        }

    def get_events(self, bucket_id, *, start, end):
        self.calls.append((bucket_id, start, end))
        return [{"bucket": bucket_id}]


class ActivityWatchClientTest(unittest.TestCase):
    def test_source_batch_uses_current_host_and_independent_dst_midnights(self) -> None:
        client = RecordingClient()

        batch = client.load_day_sources(date(2026, 3, 8))

        self.assertEqual(batch.day_start.hour, 0)
        self.assertEqual(batch.day_end.hour, 0)
        self.assertEqual(batch.day_start.utcoffset().total_seconds(), -5 * 3600)
        self.assertEqual(batch.day_end.utcoffset().total_seconds(), -4 * 3600)
        self.assertEqual(batch.day_start.timestamp() + 23 * 3600, batch.day_end.timestamp())
        self.assertEqual(
            [call[0] for call in client.calls],
            [
                "aw-watcher-window_workstation",
                "aw-watcher-web-firefox_workstation",
                "aw-watcher-afk_workstation",
            ],
        )
        self.assertEqual(len(batch.window_events), 1)
        self.assertEqual(len(batch.browser_events), 1)
        self.assertEqual(len(batch.afk_events), 1)
        browser = batch.browser_events[0]
        self.assertEqual(browser.bucket_id, "aw-watcher-web-firefox_workstation")
        self.assertEqual(browser.browser_id, "firefox")
        self.assertEqual(browser.payload["bucket"], browser.bucket_id)
        self.assertEqual(
            batch.browser_capture.discovered_bucket_ids,
            ("aw-watcher-web-firefox_workstation",),
        )
        self.assertEqual(batch.browser_capture.fetched_bucket_ids, batch.browser_capture.discovered_bucket_ids)
        self.assertEqual(batch.browser_capture.event_count, 1)
        self.assertEqual(batch.browser_capture.errors, ())

    def test_missing_current_host_window_bucket_is_recoverable_error(self) -> None:
        client = ActivityWatchClient(hostname="workstation")
        with self.assertRaises(ActivityWatchError) as raised:
            client._select_buckets(
                {
                    "aw-watcher-window_foreign": {
                        "type": "currentwindow",
                        "hostname": "foreign",
                    }
                }
            )
        self.assertTrue(raised.exception.recoverable)
        self.assertIn("current-host window bucket", raised.exception.reason)

    def test_official_hostless_browser_bucket_is_accepted(self) -> None:
        client = RecordingClient()
        client.get_buckets = lambda: {  # type: ignore[method-assign]
            "aw-watcher-window_workstation": {
                "type": "currentwindow",
                "hostname": "workstation",
            },
            "aw-watcher-web-brave": {
                "type": "web.tab.current",
                "client": "aw-client-web",
                "hostname": "unknown",
            },
            "aw-watcher-web-firefox_foreign": {
                "type": "web.tab.current",
                "client": "aw-client-web",
                "hostname": "foreign",
            },
        }

        batch = client.load_day_sources(date(2026, 8, 10))

        self.assertEqual(len(batch.browser_events), 1)
        self.assertEqual(batch.browser_events[0].browser_id, "brave")
        self.assertEqual(
            batch.browser_capture.discovered_bucket_ids,
            ("aw-watcher-web-brave",),
        )

    def test_browser_fetch_failure_preserves_required_window_data(self) -> None:
        client = RecordingClient()
        original_get_events = client.get_events

        def get_events(bucket_id, *, start, end):
            if "watcher-web" in bucket_id:
                raise ActivityWatchError("event fetch", "browser unavailable")
            return original_get_events(bucket_id, start=start, end=end)

        client.get_events = get_events  # type: ignore[method-assign]
        batch = client.load_day_sources(date(2026, 8, 10))

        self.assertEqual(len(batch.window_events), 1)
        self.assertEqual(batch.browser_events, ())
        self.assertEqual(batch.browser_capture.fetched_bucket_ids, ())
        self.assertEqual(len(batch.browser_capture.errors), 1)

    def test_non_array_event_response_is_an_explicit_error(self) -> None:
        client = ActivityWatchClient(hostname="workstation")
        client._request_json = (  # type: ignore[method-assign]
            lambda *_args, **_kwargs: {"not": "events"}
        )
        with self.assertRaises(ActivityWatchError) as raised:
            client.get_events(
                "bucket",
                start=datetime(2026, 8, 10, tzinfo=ZoneInfo("UTC")),
                end=datetime(2026, 8, 11, tzinfo=ZoneInfo("UTC")),
            )
        self.assertIn("not an array", raised.exception.reason)


if __name__ == "__main__":
    unittest.main()
