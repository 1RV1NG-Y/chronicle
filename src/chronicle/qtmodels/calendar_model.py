"""Latest-first day groups and an exact, duration-proportional day overview."""

from PySide6.QtCore import Property, Signal, Slot

from chronicle.qtmodels.activity_model import ActivityListModel, _local_minute, _sorted_events
from chronicle.services.event_normalizer import format_duration_label


class CalendarModel(ActivityListModel):
    summaryChanged = Signal()

    def __init__(self, events=(), parent=None):
        super().__init__(events, parent)
        self._events.reverse()

    def replace_events(self, events):
        self.beginResetModel()
        self._events = list(reversed(_sorted_events(events)))
        self.endResetModel()
        self.summaryChanged.emit()

    @Property(str, notify=summaryChanged)
    def activeLabel(self):  # noqa: N802
        seconds = sum(event.duration_seconds for event in self._events if not event.is_idle)
        return format_duration_label(seconds) if seconds else "0 min"

    @Property(str, notify=summaryChanged)
    def idleLabel(self):  # noqa: N802
        seconds = sum(event.duration_seconds for event in self._events if event.is_idle)
        return format_duration_label(seconds) if seconds else "0 min"

    @Property(int, notify=summaryChanged)
    def activityCount(self):  # noqa: N802
        return sum(len(event.activities) or 1 for event in self._events)

    @Property("QVariantList", notify=summaryChanged)
    def overview(self):
        return [
            {"start": _local_minute(item.start_time) / 1440,
             "end": (1440 if item.end_time.astimezone().date() > item.start_time.astimezone().date() else _local_minute(item.end_time)) / 1440,
             "color": item.accent if not item.is_idle else "#48484E", "row": row}
            for row, group in enumerate(self._events)
            for item in (group.activities or (group,))
        ]

    @Slot(float, result=int)
    def rowAtMinute(self, minute):  # noqa: N802
        for segment in self.overview:
            if segment["start"] <= minute / 1440 < segment["end"]:
                return segment["row"]
        return -1
