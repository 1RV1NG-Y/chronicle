from __future__ import annotations

from dataclasses import replace
import math
import sys
import unittest

from PySide6.QtCore import QCoreApplication, QObject
from chronicle.controller import ChronicleController, _website_capture_health
from chronicle.models.activity_event import BrowserCapture, BrowserEventSource, SourceBatch
from chronicle.qtmodels.calendar_model import CalendarModel
from chronicle.qtmodels.timeline_model import TimelineModel
from chronicle.services.event_normalizer import normalize_events


class _Client:
    endpoint = "http://localhost:5600/api/0"


class QtBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])

    def setUp(self) -> None:
        self.events = normalize_events(
            [
                {
                    "timestamp": "2026-08-10T09:00:00+00:00",
                    "duration": 60,
                    "data": {"app": "code", "title": "Chronicle controller"},
                },
                {
                    "timestamp": "2026-08-10T10:00:00+00:00",
                    "duration": 60,
                    "data": {"app": "org.gnome.Terminal", "title": "pytest"},
                },
            ]
        )

    def test_models_publish_exact_integration_roles(self) -> None:
        expected = {
            "eventId",
            "displayName",
            "primaryLabel",
            "appId",
            "title",
            "subtitle",
            "domain",
            "url",
            "startTime",
            "endTime",
            "timeLabel",
            "durationLabel",
            "durationSeconds",
            "accent",
            "isIdle",
            "isBrowser",
            "rawJson",
            "sourceCount",
            "startMinute",
            "endMinute",
            "activityCount",
        }
        calendar = CalendarModel(self.events)
        timeline = TimelineModel(self.events)

        self.assertEqual({bytes(role).decode() for role in calendar.roleNames().values()}, expected)
        self.assertEqual({bytes(role).decode() for role in timeline.roleNames().values()}, expected)

    def test_datetime_and_calendar_minute_use_system_local_time(self) -> None:
        calendar = CalendarModel(self.events)
        roles = {
            bytes(name).decode(): role for role, name in calendar.roleNames().items()
        }
        event = self.events[-1]
        local = event.start_time.astimezone()
        qdatetime = calendar.data(calendar.index(0), roles["startTime"])

        self.assertEqual(
            qdatetime.toMSecsSinceEpoch(),
            round(event.start_time.timestamp() * 1000),
        )
        self.assertEqual(qdatetime.time().hour(), local.hour)
        self.assertAlmostEqual(
            calendar.data(calendar.index(0), roles["startMinute"]),
            local.hour * 60 + local.minute,
        )

    def test_timeline_filtering_is_python_side_and_updates_counts(self) -> None:
        timeline = TimelineModel(self.events)
        self.assertFalse(timeline.hasActiveFilters)
        self.assertEqual(timeline.totalCount, 2)
        self.assertEqual(timeline.resultCount, 2)

        timeline.filterText = "terminal pytest"

        self.assertTrue(timeline.hasActiveFilters)
        self.assertEqual(timeline.filterText, "terminal pytest")
        self.assertEqual(timeline.totalCount, 2)
        self.assertEqual(timeline.resultCount, 1)
        self.assertEqual(timeline.rowCount(), 1)

    def test_website_roles_and_url_filter_keep_page_detail_available(self) -> None:
        browser = BrowserEventSource(
            bucket_id="aw-watcher-web-brave_host",
            browser_id="brave",
            payload={
                "timestamp": "2026-08-10T09:00:00+00:00",
                "duration": 60,
                "data": {
                    "title": "Discord | #general | Chronicle",
                    "url": "https://discord.com/channels/123/456",
                },
            },
        )
        events = normalize_events(
            [
                {
                    "timestamp": "2026-08-10T09:00:00+00:00",
                    "duration": 60,
                    "data": {"app": "brave-browser", "title": "Discord"},
                },
            ],
            [browser],
        )
        timeline = TimelineModel(events)
        roles = {
            bytes(name).decode(): role for role, name in timeline.roleNames().items()
        }

        self.assertEqual(
            timeline.data(timeline.index(0), roles["primaryLabel"]),
            "discord.com",
        )
        self.assertEqual(timeline.data(timeline.index(0), roles["displayName"]), "Brave")
        self.assertEqual(
            timeline.data(timeline.index(0), roles["url"]),
            "https://discord.com/channels/123/456",
        )
        self.assertTrue(timeline.data(timeline.index(0), roles["isBrowser"]))
        timeline.filterText = "channels/123"
        self.assertEqual(timeline.resultCount, 1)

    def test_controller_exposes_contract_properties_and_slots(self) -> None:
        calendar = CalendarModel()
        timeline = TimelineModel()
        controller = ChronicleController(calendar, timeline, _Client())  # type: ignore[arg-type]
        meta = controller.metaObject()
        property_names = {
            meta.property(index).name()
            for index in range(QObject.staticMetaObject.propertyCount(), meta.propertyCount())
        }
        self.assertEqual(
            property_names,
            {
                "selectedDate",
                "dateLabel",
                "status",
                "statusDetail",
                "isLoading",
                "lastRefreshLabel",
                "firstActivityMinute",
                "lastActivityMinute",
                "endpoint",
                "websiteCaptureStatus",
                "websiteCaptureDetail",
            },
        )
        for signature in (
            "previousDay()",
            "nextDay()",
            "goToday()",
            "retry()",
            "setInteractionActive(bool)",
        ):
            self.assertGreaterEqual(meta.indexOfMethod(signature), 0)
        self.assertIn(controller.status, {"loading", "ready", "empty", "error"})

    def test_controller_tracks_latest_activity_minute(self) -> None:
        calendar = CalendarModel()
        timeline = TimelineModel()
        controller = ChronicleController(calendar, timeline, _Client())  # type: ignore[arg-type]

        controller._load_succeeded(  # noqa: SLF001
            0,
            controller._selected_date,  # noqa: SLF001
            self.events,
            self.events,
            self.events[0].start_time,
        )

        latest = max(event.end_time for event in self.events).astimezone()
        expected = math.ceil(
            latest.hour * 60
            + latest.minute
            + latest.second / 60
            + latest.microsecond / 60_000_000
        )
        self.assertEqual(controller.lastActivityMinute, expected)

    def test_website_capture_health_distinguishes_source_states(self) -> None:
        first = self.events[0]
        missing = SourceBatch(
            day_start=first.start_time,
            day_end=first.end_time,
            window_events=(),
        )
        self.assertEqual(_website_capture_health(missing, self.events)[0], "not-detected")

        capture = BrowserCapture(
            discovered_bucket_ids=("aw-watcher-web-brave_host",),
            fetched_bucket_ids=("aw-watcher-web-brave_host",),
            event_count=1,
        )
        no_events = replace(capture, event_count=0)
        self.assertEqual(
            _website_capture_health(
                replace(missing, browser_capture=no_events),
                self.events,
            )[0],
            "no-events",
        )
        self.assertEqual(
            _website_capture_health(
                replace(missing, browser_capture=capture),
                self.events,
            )[0],
            "unmatched",
        )
        failed = BrowserCapture(
            discovered_bucket_ids=("aw-watcher-web-brave_host",),
            errors=("aw-watcher-web-brave_host: unavailable",),
        )
        self.assertEqual(
            _website_capture_health(
                replace(missing, browser_capture=failed),
                self.events,
            )[0],
            "error",
        )
        observed = replace(first, domain="example.com")
        captured = replace(missing, browser_capture=capture)
        status, detail = _website_capture_health(captured, [observed])
        self.assertEqual(status, "capturing")
        self.assertIn("1 attributed interval", detail)

    def test_active_interaction_defers_periodic_refresh(self) -> None:
        calendar = CalendarModel()
        timeline = TimelineModel()
        controller = ChronicleController(calendar, timeline, _Client())  # type: ignore[arg-type]
        controller._load_succeeded(  # noqa: SLF001
            0,
            controller._selected_date,  # noqa: SLF001
            self.events,
            self.events,
            self.events[0].start_time,
        )
        generation = controller._generation  # noqa: SLF001

        controller.setInteractionActive(True)
        controller._refresh_current_day()  # noqa: SLF001

        self.assertEqual(controller._generation, generation)  # noqa: SLF001
        self.assertEqual(calendar.rowCount(), len(self.events))

    def test_background_refresh_keeps_existing_rows_and_status(self) -> None:
        class _Pool:
            def start(self, task: object) -> None:
                self.task = task

        calendar = CalendarModel(self.events)
        timeline = TimelineModel(self.events)
        pool = _Pool()
        controller = ChronicleController(  # type: ignore[arg-type]
            calendar,
            timeline,
            _Client(),
            thread_pool=pool,
        )
        controller._load_succeeded(  # noqa: SLF001
            0,
            controller._selected_date,  # noqa: SLF001
            self.events,
            self.events,
            self.events[0].start_time,
        )

        controller._request_load(preserve_existing=True)  # noqa: SLF001
        generation = controller._generation  # noqa: SLF001
        controller._load_failed(  # noqa: SLF001
            generation,
            controller._selected_date,  # noqa: SLF001
            "temporary failure",
        )

        self.assertEqual(calendar.rowCount(), len(self.events))
        self.assertEqual(timeline.rowCount(), len(self.events))
        self.assertEqual(controller.status, "ready")


    def test_inflight_background_result_is_ignored_while_scrolling(self) -> None:
        class _Pool:
            def start(self, task: object) -> None:
                self.task = task

        calendar = CalendarModel(self.events)
        timeline = TimelineModel(self.events)
        controller = ChronicleController(  # type: ignore[arg-type]
            calendar,
            timeline,
            _Client(),
            thread_pool=_Pool(),
        )
        controller._load_succeeded(  # noqa: SLF001
            0,
            controller._selected_date,  # noqa: SLF001
            self.events,
            self.events,
            self.events[0].start_time,
        )
        controller._request_load(preserve_existing=True)  # noqa: SLF001
        controller.setInteractionActive(True)

        controller._load_succeeded(  # noqa: SLF001
            controller._generation,  # noqa: SLF001
            controller._selected_date,  # noqa: SLF001
            [],
            [],
            self.events[0].start_time,
        )

        self.assertEqual(calendar.rowCount(), len(self.events))
        self.assertEqual(timeline.rowCount(), len(self.events))
        self.assertEqual(controller.status, "ready")

if __name__ == "__main__":
    unittest.main()
