"""Shared exact-role Qt projection for Chronicle activity records."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from PySide6.QtCore import QByteArray, QAbstractListModel, QDateTime, QModelIndex, Qt, QTimeZone, Slot

from chronicle.models.activity_event import ActivityEvent


class ActivityListModel(QAbstractListModel):
    """Read-only list projection with the role contract consumed by QML."""

    IdRole = int(Qt.ItemDataRole.UserRole) + 1
    DisplayNameRole = IdRole + 1
    PrimaryLabelRole = DisplayNameRole + 1
    AppIdRole = PrimaryLabelRole + 1
    TitleRole = AppIdRole + 1
    SubtitleRole = TitleRole + 1
    DomainRole = SubtitleRole + 1
    UrlRole = DomainRole + 1
    StartTimeRole = UrlRole + 1
    EndTimeRole = StartTimeRole + 1
    TimeLabelRole = EndTimeRole + 1
    DurationLabelRole = TimeLabelRole + 1
    DurationSecondsRole = DurationLabelRole + 1
    AccentRole = DurationSecondsRole + 1
    IsIdleRole = AccentRole + 1
    IsBrowserRole = IsIdleRole + 1
    RawJsonRole = IsBrowserRole + 1
    SourceCountRole = RawJsonRole + 1
    StartMinuteRole = SourceCountRole + 1
    EndMinuteRole = StartMinuteRole + 1
    ActivityCountRole = EndMinuteRole + 1

    _ROLE_NAMES = {
        IdRole: QByteArray(b"eventId"),
        DisplayNameRole: QByteArray(b"displayName"),
        PrimaryLabelRole: QByteArray(b"primaryLabel"),
        AppIdRole: QByteArray(b"appId"),
        TitleRole: QByteArray(b"title"),
        SubtitleRole: QByteArray(b"subtitle"),
        DomainRole: QByteArray(b"domain"),
        UrlRole: QByteArray(b"url"),
        StartTimeRole: QByteArray(b"startTime"),
        EndTimeRole: QByteArray(b"endTime"),
        TimeLabelRole: QByteArray(b"timeLabel"),
        DurationLabelRole: QByteArray(b"durationLabel"),
        DurationSecondsRole: QByteArray(b"durationSeconds"),
        AccentRole: QByteArray(b"accent"),
        IsIdleRole: QByteArray(b"isIdle"),
        IsBrowserRole: QByteArray(b"isBrowser"),
        RawJsonRole: QByteArray(b"rawJson"),
        SourceCountRole: QByteArray(b"sourceCount"),
        StartMinuteRole: QByteArray(b"startMinute"),
        EndMinuteRole: QByteArray(b"endMinute"),
        ActivityCountRole: QByteArray(b"activityCount"),
    }

    def __init__(
        self,
        events: Iterable[ActivityEvent] = (),
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self._events = _sorted_events(events)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._events)

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802
        return self._ROLE_NAMES

    def data(
        self,
        index: QModelIndex,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._events):
            return None
        event = self._events[index.row()]
        if role == self.IdRole:
            return event.id
        if role in (int(Qt.ItemDataRole.DisplayRole), self.DisplayNameRole):
            return event.display_name
        if role == self.PrimaryLabelRole:
            return event.domain or event.display_name
        if role == self.AppIdRole:
            return event.app_id
        if role == self.TitleRole:
            return event.title
        if role == self.SubtitleRole:
            return event.subtitle
        if role == self.DomainRole:
            return event.domain
        if role == self.StartTimeRole:
            return _to_local_qdatetime(event.start_time)
        if role == self.UrlRole:
            return event.url
        if role == self.EndTimeRole:
            return _to_local_qdatetime(event.end_time)
        if role == self.TimeLabelRole:
            return event.time_label
        if role == self.DurationLabelRole:
            return event.duration_label
        if role == self.DurationSecondsRole:
            return event.duration_seconds
        if role == self.AccentRole:
            return event.accent
        if role == self.IsIdleRole:
            return event.is_idle
        if role == self.IsBrowserRole:
            return event.is_browser
        if role == self.RawJsonRole:
            return event.raw_json
        if role == self.SourceCountRole:
            return event.source_count
        if role == self.StartMinuteRole:
            return _local_minute(event.start_time)
        if role == self.EndMinuteRole:
            return 1440.0 if event.end_time.astimezone().date() > event.start_time.astimezone().date() else _local_minute(event.end_time)
        if role == self.ActivityCountRole:
            return len(event.activities) or 1
        return None

    @Slot(int, result="QVariantMap")
    def recordAt(self, row: int) -> dict[str, Any]:  # noqa: N802
        if not 0 <= row < len(self._events):
            return {}
        event = self._events[row]
        result = {
            bytes(name).decode(): self.data(self.index(row), role)
            for role, name in self._ROLE_NAMES.items()
        }
        result["activities"] = [snapshot(item) for item in event.activities]
        return result

    def replace_events(self, events: Iterable[ActivityEvent]) -> None:
        replacement = _sorted_events(events)
        self.beginResetModel()
        self._events = replacement
        self.endResetModel()


def _sorted_events(events: Iterable[ActivityEvent]) -> list[ActivityEvent]:
    return sorted(
        events,
        key=lambda event: (
            event.start_time,
            event.end_time,
            event.is_idle,
            event.id,
        ),
    )


def _to_local_qdatetime(value: Any) -> QDateTime:
    milliseconds = round(value.timestamp() * 1000)
    return QDateTime.fromMSecsSinceEpoch(milliseconds, QTimeZone.systemTimeZone())


def _local_minute(value: Any) -> float:
    local = value.astimezone()
    return (
        local.hour * 60
        + local.minute
        + local.second / 60
        + local.microsecond / 60_000_000
    )


def snapshot(event: ActivityEvent) -> dict[str, Any]:
    """Exact child record for the inspector; no raw-data parsing in QML."""
    return {
        "eventId": event.id, "displayName": event.display_name,
        "primaryLabel": event.domain or event.display_name,
        "title": event.title, "subtitle": event.subtitle,
        "domain": event.domain, "url": event.url, "appId": event.app_id,
        "startTime": _to_local_qdatetime(event.start_time),
        "endTime": _to_local_qdatetime(event.end_time),
        "timeLabel": event.time_label, "durationLabel": event.duration_label,
        "durationSeconds": event.duration_seconds, "accent": event.accent,
        "isIdle": event.is_idle, "isBrowser": event.is_browser,
        "rawJson": event.raw_json, "sourceCount": event.source_count,
        "activityCount": 1, "activities": [],
    }
