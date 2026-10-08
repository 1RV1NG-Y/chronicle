"""Chronicle desktop application bootstrap."""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from chronicle.api.activitywatch_client import ActivityWatchClient
from chronicle.controller import ChronicleController
from chronicle.qtmodels.calendar_model import CalendarModel
from chronicle.qtmodels.timeline_model import TimelineModel


def main() -> int:
    """Create the UI first, then begin local ActivityWatch loading asynchronously."""

    parser = argparse.ArgumentParser(description="Chronicle — your computer day, remembered")
    parser.add_argument("--demo", action="store_true", help="Preview the design with clearly labeled sample activity")
    args = parser.parse_args()
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Chronicle")
    app.setApplicationDisplayName("Chronicle")
    app.setOrganizationName("Chronicle")

    calendar_model = CalendarModel()
    timeline_model = TimelineModel()
    if args.demo:
        from chronicle.demo import DemoClient
        client = DemoClient()
    else:
        client = ActivityWatchClient()
    controller = ChronicleController(
        calendar_model,
        timeline_model,
        client,
    )

    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("controller", controller)
    context.setContextProperty("calendarModel", calendar_model)
    context.setContextProperty("timelineModel", timeline_model)
    context.setContextProperty("previewMode", args.demo)

    qml_file = Path(__file__).with_name("qml") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        return 1
    QTimer.singleShot(0, controller.start)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
