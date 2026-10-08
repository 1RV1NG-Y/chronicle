"""Explicit preview data. Never used by the real ActivityWatch client."""

from datetime import datetime, time, timedelta

from chronicle.models.activity_event import BrowserCapture, BrowserEventSource, SourceBatch
from chronicle.api.activitywatch_client import _system_timezone


class DemoClient:
    endpoint = "Preview — sample activity"

    def __init__(self):
        self.local_timezone = _system_timezone()

    def load_day_sources(self, day):
        start = datetime.combine(day, time.min, self.local_timezone)
        windows, browser, idle = [], [], []
        rows = [
            ("08:42", "09:05", "firefox", "Morning reading — Kottke", "https://kottke.org"),
            ("09:05", "09:42", "code", "calendar_builder.py — Chronicle", ""),
            ("09:42", "10:18", "code", "CalendarPage.qml — Chronicle", ""),
            ("10:18", "10:30", "org.gnome.Terminal", "Running the test suite", ""),
            ("10:30", "10:48", "firefox", "Qt Quick documentation", "https://doc.qt.io/qt-6/qtquick-index.html"),
            ("10:48", "11:05", "idle", "", ""),
            ("11:05", "11:50", "code", "ActivityInspector.qml — Chronicle", ""),
            ("11:50", "12:05", "firefox", "Chronicle · pull requests", "https://github.com/example/chronicle/pulls"),
            ("12:05", "13:10", "idle", "", ""),
            ("13:10", "13:45", "firefox", "Design notes — a better day view", "https://www.figma.com/design/example"),
            ("13:45", "14:28", "code", "Main.qml — Chronicle", ""),
            ("14:28", "14:56", "code", "Theme.qml — Chronicle", ""),
            ("14:56", "15:12", "org.gnome.Terminal", "chronicle --demo", ""),
            ("15:12", "15:35", "firefox", "Preserving the detail in your day", "https://github.com/example/chronicle/issues/12"),
            ("15:35", "15:40", "org.gnome.Nautilus", "Chronicle / references", ""),
            ("15:40", "16:08", "code", "CalendarPage.qml — Chronicle", ""),
            ("16:08", "16:24", "code", "ActivityInspector.qml — Chronicle", ""),
            ("16:24", "16:34", "idle", "", ""),
            ("16:34", "16:34:20", "org.gnome.Nautilus", "Preview captures", ""),
            ("16:34:20", "16:34:40", "org.gnome.Terminal", "python -m unittest", ""),
            ("16:34:40", "16:34:55", "code", "test_calendar_builder.py — Chronicle", ""),
            ("16:34:55", "16:42", "firefox", "Chronicle · day view review", "https://github.com/example/chronicle/pull/24"),
        ]
        for begin, finish, app, title, url in rows:
            a = datetime.combine(day, time.fromisoformat(begin), self.local_timezone)
            b = datetime.combine(day, time.fromisoformat(finish), self.local_timezone)
            payload = {"timestamp": a.isoformat(), "duration": (b - a).total_seconds(), "data": {"app": app, "title": title}}
            if app == "idle":
                payload["data"] = {"status": "afk"}
                idle.append(payload)
            else:
                windows.append(payload)
                if url:
                    browser.append(BrowserEventSource("preview-firefox", "firefox", {
                        "timestamp": a.isoformat(), "duration": (b - a).total_seconds(),
                        "data": {"url": url, "title": title},
                    }))
        return SourceBatch(start, start + timedelta(days=1), tuple(windows), tuple(browser), tuple(idle),
                           BrowserCapture(("preview-firefox",), ("preview-firefox",), len(browser)))
