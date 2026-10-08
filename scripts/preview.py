"""Render and exercise the real QML UI using explicitly labeled sample data.

QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software PYTHONPATH=src \
    .venv/bin/python scripts/preview.py /tmp/chronicle-preview
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from shiboken6 import delete

from chronicle.controller import ChronicleController, _website_capture_health
from chronicle.demo import DemoClient
from chronicle.qtmodels.calendar_model import CalendarModel
from chronicle.qtmodels.timeline_model import TimelineModel
from chronicle.services.calendar_builder import build_calendar_events
from chronicle.services.event_normalizer import build_events, normalize_events

output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/chronicle-preview")
output.mkdir(parents=True, exist_ok=True)
messages = []

def log(kind, context, message):
    messages.append(message)
    print(message, file=sys.stderr)

qInstallMessageHandler(log)
QQuickStyle.setStyle("Basic")
app = QGuiApplication([])
calendar, timeline = CalendarModel(), TimelineModel()
controller = ChronicleController(calendar, timeline, DemoClient())
controller._selected_date = date(2026, 10, 4)
batch = controller._client.load_day_sources(controller._selected_date)
events = build_events(batch)
controller._load_succeeded(0, controller._selected_date, build_calendar_events(events), events, datetime.now().astimezone(), _website_capture_health(batch, events))
engine = QQmlApplicationEngine()
for name, value in [("calendarModel", calendar), ("timelineModel", timeline), ("controller", controller), ("previewMode", True)]:
    engine.rootContext().setContextProperty(name, value)
engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "src/chronicle/qml/Main.qml")))
assert engine.rootObjects(), "QML failed to load"
window = engine.rootObjects()[0]


def save(name):
    QTest.qWait(180)
    image = window.grabWindow()
    assert not image.isNull(), "Window did not render"
    assert image.save(str(output / name))


def find_item(name, item=None):
    item = item or window.contentItem()
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = find_item(name, child)
        if found is not None:
            return found
    return None


def click(name):
    item = find_item(name)
    assert item is not None, name
    point = item.mapToScene(QPoint(round(item.width() / 2), round(item.height() / 2)))
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point.toPoint())
    QTest.qWait(100)

save("day.png")
click("dayCard1")
record = window.property("selectedEvent")
if hasattr(record, "toVariant"):
    record = record.toVariant()
assert len(record["activities"]) == 3, record
save("group.png")
click("inspectorEntry0")
save("expanded.png")
window.setWidth(960)
save("compact.png")
QTest.keyClick(window, Qt.Key_Escape)
selection = window.property("selectedEvent")
assert selection is None or (hasattr(selection, "isNull") and selection.isNull())
window.setWidth(1280)
window.setProperty("currentPage", 1)
timeline.filterText = "CalendarPage.qml"
QTest.qWait(100)
assert timeline.resultCount == 2
save("timeline.png")
window.setProperty("currentPage", 2)
save("settings.png")
window.setProperty("currentPage", 0)
controller.previousDay()
for _ in range(50):
    if controller.status != "loading":
        break
    QTest.qWait(20)
assert controller.status == "ready"
assert controller.selectedDate.day() == 3
assert calendar.recordAt(0)["startTime"].date().day() == 3
controller.goToday()
for _ in range(50):
    if controller.status != "loading":
        break
    QTest.qWait(20)
assert controller.status == "ready"
controller._load_succeeded(controller._generation, controller._selected_date, [], [], datetime.now().astimezone())
save("empty.png")
controller._load_failed(controller._generation, controller._selected_date, "ActivityWatch is not running")
save("error.png")
# Large days must not instantiate a card for every recorded event.
start = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
dense_events = normalize_events([
    {"timestamp": (start + timedelta(minutes=i)).isoformat(), "duration": 60,
     "data": {"app": "code" if i % 2 else "terminal", "title": f"Sample task {i}"}}
    for i in range(1200)
])
controller._load_succeeded(controller._generation, controller._selected_date,
                           build_calendar_events(dense_events), dense_events, datetime.now().astimezone())
QTest.qWait(150)
assert calendar.rowCount() == 1200

def card_count(item):
    return int(item.objectName().startswith("dayCard")) + sum(card_count(child) for child in item.childItems())

assert card_count(window.contentItem()) < 50, "Day feed is not virtualized"
delete(engine)
assert not messages, messages
print(f"UI checks passed. Screenshots: {output}")
