from datetime import date, datetime, timedelta, timezone
import unittest

from PySide6.QtCore import QCoreApplication

from chronicle.api.activitywatch_client import ActivityWatchError
from chronicle.controller import ChronicleController, _LoadTask
from chronicle.qtmodels.calendar_model import CalendarModel
from chronicle.qtmodels.timeline_model import TimelineModel
from chronicle.services.calendar_builder import build_calendar_events
from chronicle.services.event_normalizer import normalize_events


def events_at(start, descriptions):
    return normalize_events([
        {"timestamp": (start + timedelta(seconds=offset)).isoformat(), "duration": seconds,
         "data": {"app": app, "title": title}}
        for offset, seconds, app, title in descriptions
    ])


class DayModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_latest_first_and_snapshot_retains_group_members(self):
        events = events_at(datetime(2026, 10, 4, 9, tzinfo=timezone.utc), [
            (0, 10, "code", "one.py"), (10, 10, "terminal", "tests"),
            (20, 120, "code", "two.py"),
        ])
        model = CalendarModel(build_calendar_events(events))
        self.assertEqual(model.recordAt(0)["title"], "two.py")
        grouped = model.recordAt(1)
        self.assertEqual(grouped["activityCount"], 2)
        self.assertEqual([item["title"] for item in grouped["activities"]], ["one.py", "tests"])
        self.assertEqual(model.activityCount, 3)
        self.assertEqual(model.recordAt(100), {})

    def test_overview_uses_exact_children_and_excludes_recording_gaps(self):
        start = datetime.now().astimezone().replace(hour=9, minute=0, second=0, microsecond=0)
        events = events_at(start, [(0, 20, "code", "one"), (20, 20, "terminal", "two"), (90, 60, "code", "three")])
        model = CalendarModel(build_calendar_events(events))
        self.assertEqual(len(model.overview), 3)
        self.assertEqual(model.rowAtMinute(540.1), 1)
        self.assertEqual(model.rowAtMinute(541), -1)
        self.assertEqual(model.rowAtMinute(542), 0)
        self.assertAlmostEqual(sum((s["end"] - s["start"]) * 86400 for s in model.overview), 100)

    def test_midnight_end_does_not_wrap_to_zero(self):
        start = datetime.now().astimezone().replace(hour=23, minute=59, second=0, microsecond=0)
        events = events_at(start, [(0, 60, "code", "late session")])
        model = CalendarModel(events)
        self.assertEqual(model.recordAt(0)["endMinute"], 1440)
        self.assertEqual(model.overview[0]["end"], 1)
        self.assertEqual(model.rowAtMinute(1439.5), 0)

    def test_default_controller_can_construct_its_client(self):
        controller = ChronicleController(CalendarModel(), TimelineModel())
        self.assertTrue(controller.endpoint.startswith("http://localhost:"))

    def test_worker_connection_failure_emits_recoverable_error(self):
        class FailingClient:
            def load_day_sources(self, day):
                raise ActivityWatchError("load", "Connection refused")
        task = _LoadTask(7, date(2026, 10, 4), FailingClient())
        failed, finished = [], []
        task.signals.failed.connect(lambda *args: failed.append(args))
        task.signals.finished.connect(finished.append)
        task.run()
        self.assertEqual(failed, [(7, date(2026, 10, 4), "Connection refused")])
        self.assertEqual(finished, [7])
