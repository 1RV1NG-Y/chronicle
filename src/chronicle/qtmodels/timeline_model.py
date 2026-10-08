"""Filterable Python-side timeline projection for Chronicle QML."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from PySide6.QtCore import Property, Signal

from chronicle.models.activity_event import ActivityEvent
from chronicle.qtmodels.activity_model import ActivityListModel, _sorted_events


class TimelineModel(ActivityListModel):
    """Timeline projection whose filtering and counts are authoritative in Python."""

    filterTextChanged = Signal()
    resultCountChanged = Signal()
    totalCountChanged = Signal()

    def __init__(
        self,
        events: Iterable[ActivityEvent] = (),
        parent: Any | None = None,
    ) -> None:
        self._all_events = _sorted_events(events)
        self._filter_text = ""
        super().__init__(self._all_events, parent)

    @Property(str, notify=filterTextChanged)
    def filterText(self) -> str:  # noqa: N802
        return self._filter_text

    @filterText.setter
    def filterText(self, value: str) -> None:  # noqa: N802
        replacement = str(value or "")
        if replacement == self._filter_text:
            return
        previous_count = len(self._events)
        self._filter_text = replacement
        self._apply_filter()
        self.filterTextChanged.emit()
        if len(self._events) != previous_count:
            self.resultCountChanged.emit()

    @Property(bool, notify=filterTextChanged)
    def hasActiveFilters(self) -> bool:  # noqa: N802
        return bool(self._filter_text.strip())

    @Property(int, notify=resultCountChanged)
    def resultCount(self) -> int:  # noqa: N802
        return len(self._events)

    @Property(int, notify=totalCountChanged)
    def totalCount(self) -> int:  # noqa: N802
        return len(self._all_events)

    def replace_events(self, events: Iterable[ActivityEvent]) -> None:
        replacement = _sorted_events(events)
        previous_result = len(self._events)
        previous_total = len(self._all_events)
        self._all_events = replacement
        self._apply_filter()
        if len(self._all_events) != previous_total:
            self.totalCountChanged.emit()
        if len(self._events) != previous_result:
            self.resultCountChanged.emit()

    def _apply_filter(self) -> None:
        terms = self._filter_text.casefold().split()
        if terms:
            visible = [
                event
                for event in self._all_events
                if all(term in _search_text(event) for term in terms)
            ]
        else:
            visible = list(self._all_events)
        self.beginResetModel()
        self._events = visible
        self.endResetModel()


def _search_text(event: ActivityEvent) -> str:
    return " ".join(
        (
            event.display_name,
            event.app_id,
            event.title,
            event.subtitle,
            event.domain,
            event.url,
            event.time_label,
            event.duration_label,
        )
    ).casefold()
