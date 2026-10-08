"""Navigation and asynchronous load state for Chronicle's QML surface."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone, tzinfo
from enum import Enum

from PySide6.QtCore import (
    Property,
    QDate,
    QObject,
    QRunnable,
    QThreadPool,
    QTimer,
    Signal,
    Slot,
)

from chronicle.api.activitywatch_client import ActivityWatchClient, ActivityWatchError
from chronicle.models.activity_event import ActivityEvent, SourceBatch
from chronicle.qtmodels.calendar_model import CalendarModel
from chronicle.qtmodels.timeline_model import TimelineModel
from chronicle.services.calendar_builder import build_calendar_events
from chronicle.services.event_normalizer import build_events


class _LoadStatus(str, Enum):
    LOADING = "loading"
    READY = "ready"
    EMPTY = "empty"
    ERROR = "error"


class _LoadSignals(QObject):
    succeeded = Signal(int, object, object, object, object, object)
    failed = Signal(int, object, str)
    finished = Signal(int)


class _LoadTask(QRunnable):
    def __init__(
        self,
        generation: int,
        selected_day: date,
        client: ActivityWatchClient,
    ) -> None:
        super().__init__()
        self.generation = generation
        self.selected_day = selected_day
        self.client = client
        self.signals = _LoadSignals()

    def run(self) -> None:
        try:
            batch = self.client.load_day_sources(self.selected_day)
            timeline_events = build_events(batch)
            calendar_events = build_calendar_events(timeline_events)
            website_health = _website_capture_health(batch, timeline_events)
            self.signals.succeeded.emit(
                self.generation,
                self.selected_day,
                calendar_events,
                timeline_events,
                datetime.now().astimezone(),
                website_health,
            )
        except ActivityWatchError as error:
            self.signals.failed.emit(self.generation, self.selected_day, error.reason)
        except Exception as error:  # keep worker exceptions out of Qt's event loop
            self.signals.failed.emit(
                self.generation,
                self.selected_day,
                f"Unexpected local data error: {error}",
            )
        finally:
            self.signals.finished.emit(self.generation)


class ChronicleController(QObject):
    """Typed controller implementing Chronicle's complete QML backend contract."""

    selectedDateChanged = Signal()
    dateLabelChanged = Signal()
    statusChanged = Signal()
    statusDetailChanged = Signal()
    lastRefreshLabelChanged = Signal()
    firstActivityMinuteChanged = Signal()
    lastActivityMinuteChanged = Signal()
    websiteCaptureChanged = Signal()

    def __init__(
        self,
        calendar_model: CalendarModel,
        timeline_model: TimelineModel,
        client: ActivityWatchClient | None = None,
        *,
        thread_pool: QThreadPool | None = None,
        refresh_interval_ms: int = 60_000,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._calendar_model = calendar_model
        self._timeline_model = timeline_model
        self._client = client or ActivityWatchClient()
        self._timezone: tzinfo = (
            getattr(self._client, "local_timezone", None)
            or datetime.now().astimezone().tzinfo
            or timezone.utc
        )
        self._selected_date = datetime.now(self._timezone).date()
        self._status = _LoadStatus.LOADING
        self._status_detail = "Loading local activity…"
        self._last_refresh_label = ""
        self._first_activity_minute = 0
        self._website_capture_status = "checking"
        self._website_capture_detail = "Checking for browser-watcher data…"
        self._last_activity_minute = -1
        self._generation = 0
        self._started = False
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._workers: dict[int, _LoadTask] = {}
        self._background_generations: set[int] = set()
        self._interaction_active = False

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(max(1_000, refresh_interval_ms))
        self._refresh_timer.timeout.connect(self._refresh_current_day)

    @Property(QDate, notify=selectedDateChanged)
    def selectedDate(self) -> QDate:  # noqa: N802
        return QDate(
            self._selected_date.year,
            self._selected_date.month,
            self._selected_date.day,
        )

    @Property(str, notify=dateLabelChanged)
    def dateLabel(self) -> str:  # noqa: N802
        day = self._selected_date
        formatted = f"{day:%A}, {day:%B} {day.day}, {day.year}"
        if day == self._today():
            return f"Today · {formatted}"
        return formatted

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status.value

    @Property(str, notify=statusDetailChanged)
    def statusDetail(self) -> str:  # noqa: N802
        return self._status_detail

    @Property(bool, notify=statusChanged)
    def isLoading(self) -> bool:  # noqa: N802
        return self._status is _LoadStatus.LOADING

    @Property(str, notify=lastRefreshLabelChanged)
    def lastRefreshLabel(self) -> str:  # noqa: N802
        return self._last_refresh_label

    @Property(int, notify=firstActivityMinuteChanged)
    def firstActivityMinute(self) -> int:  # noqa: N802
        return self._first_activity_minute

    @Property(int, notify=lastActivityMinuteChanged)
    def lastActivityMinute(self) -> int:  # noqa: N802
        return self._last_activity_minute

    @Property(str, notify=websiteCaptureChanged)
    def websiteCaptureStatus(self) -> str:  # noqa: N802
        return self._website_capture_status

    @Property(str, notify=websiteCaptureChanged)
    def websiteCaptureDetail(self) -> str:  # noqa: N802
        return self._website_capture_detail

    @Property(str, constant=True)
    def endpoint(self) -> str:
        return self._client.endpoint

    def start(self) -> None:
        """Begin loading only after the QML root has been created."""

        if self._started:
            return
        self._started = True
        self._refresh_timer.start()
        self._request_load()

    @Slot()
    def previousDay(self) -> None:  # noqa: N802
        self._select_day(self._selected_date - timedelta(days=1))

    @Slot()
    def nextDay(self) -> None:  # noqa: N802
        self._select_day(self._selected_date + timedelta(days=1))

    @Slot()
    def goToday(self) -> None:  # noqa: N802
        self._select_day(self._today(), force=self._status is _LoadStatus.ERROR)

    @Slot()
    def retry(self) -> None:
        self._request_load()

    @Slot(bool)
    def setInteractionActive(self, active: bool) -> None:  # noqa: N802
        self._interaction_active = active

    def _select_day(self, selected_day: date, *, force: bool = False) -> None:
        if selected_day == self._selected_date and not force:
            return
        self._selected_date = selected_day
        self.selectedDateChanged.emit()
        self.dateLabelChanged.emit()
        self._request_load()

    def _request_load(self, *, preserve_existing: bool = False) -> None:
        self._generation += 1
        generation = self._generation
        selected_day = self._selected_date
        if preserve_existing:
            self._background_generations.add(generation)
        else:
            self._replace_records([], [])
            self._set_first_activity_minute(0)
            self._set_last_activity_minute(-1)
            self._set_website_capture(
                "checking",
                "Checking for browser-watcher data…",
            )
            self._set_last_refresh_label("")
            self._set_status(_LoadStatus.LOADING, "Loading local activity…")

        task = _LoadTask(generation, selected_day, self._client)
        task.signals.succeeded.connect(self._load_succeeded)
        task.signals.failed.connect(self._load_failed)
        task.signals.finished.connect(self._load_finished)
        self._workers[generation] = task
        self._thread_pool.start(task)

    def _load_succeeded(
        self,
        generation: int,
        selected_day: date,
        calendar_events: list[ActivityEvent],
        timeline_events: list[ActivityEvent],
        refreshed_at: datetime,
        website_health: tuple[str, str] | None = None,
    ) -> None:
        if generation != self._generation or selected_day != self._selected_date:
            return
        if generation in self._background_generations and self._interaction_active:
            return
        self._replace_records(calendar_events, timeline_events)
        if timeline_events:
            first = min(event.start_time for event in timeline_events).astimezone(self._timezone)
            self._set_first_activity_minute(first.hour * 60 + first.minute)
            last = max(event.end_time for event in timeline_events).astimezone(self._timezone)
            if last.date() > self._selected_date:
                last_minute = 1440
            else:
                last_minute = min(
                    1440,
                    math.ceil(
                        last.hour * 60
                        + last.minute
                        + last.second / 60
                        + last.microsecond / 60_000_000
                    ),
                )
            self._set_last_activity_minute(last_minute)
            self._set_status(
                _LoadStatus.READY,
                f"{len(calendar_events)} day groups · {len(timeline_events)} activities",
            )
        else:
            self._set_first_activity_minute(0)
            self._set_last_activity_minute(-1)
            self._set_status(_LoadStatus.EMPTY, "No activity recorded for this day")
        self._set_last_refresh_label(f"Updated {refreshed_at.astimezone(self._timezone):%H:%M}")
        if website_health is not None:
            self._set_website_capture(*website_health)

    def _load_failed(self, generation: int, selected_day: date, reason: str) -> None:
        if generation != self._generation or selected_day != self._selected_date:
            return
        if generation in self._background_generations:
            self._set_last_refresh_label("Refresh failed")
            return
        self._replace_records([], [])
        self._set_first_activity_minute(0)
        self._set_last_activity_minute(-1)
        self._set_website_capture(
            "error",
            f"Website capture could not be checked: {reason}",
        )
        self._set_status(_LoadStatus.ERROR, reason)

    def _load_finished(self, generation: int) -> None:
        self._workers.pop(generation, None)
        self._background_generations.discard(generation)

    def _refresh_current_day(self) -> None:
        if (
            self._selected_date == self._today()
            and not self.isLoading
            and not self._interaction_active
            and not self._workers
        ):
            self._request_load(preserve_existing=True)

    def _replace_records(
        self,
        calendar_events: list[ActivityEvent],
        timeline_events: list[ActivityEvent],
    ) -> None:
        self._calendar_model.replace_events(calendar_events)
        self._timeline_model.replace_events(timeline_events)

    def _set_status(self, status: _LoadStatus, detail: str) -> None:
        if status is not self._status:
            self._status = status
            self.statusChanged.emit()
        if detail != self._status_detail:
            self._status_detail = detail
            self.statusDetailChanged.emit()

    def _set_last_refresh_label(self, label: str) -> None:
        if label != self._last_refresh_label:
            self._last_refresh_label = label
            self.lastRefreshLabelChanged.emit()

    def _set_website_capture(self, status: str, detail: str) -> None:
        if (
            status != self._website_capture_status
            or detail != self._website_capture_detail
        ):
            self._website_capture_status = status
            self._website_capture_detail = detail
            self.websiteCaptureChanged.emit()

    def _set_first_activity_minute(self, minute: int) -> None:
        if minute != self._first_activity_minute:
            self._first_activity_minute = minute
            self.firstActivityMinuteChanged.emit()

    def _set_last_activity_minute(self, minute: int) -> None:
        if minute != self._last_activity_minute:
            self._last_activity_minute = minute
            self.lastActivityMinuteChanged.emit()

    def _today(self) -> date:
        return datetime.now(self._timezone).date()


def _website_capture_health(
    batch: SourceBatch,
    timeline_events: list[ActivityEvent],
) -> tuple[str, str]:
    capture = batch.browser_capture
    discovered = len(capture.discovered_bucket_ids)
    fetched = len(capture.fetched_bucket_ids)
    attributed = sum(bool(event.domain) for event in timeline_events)
    if discovered == 0:
        return (
            "not-detected",
            "No browser-watcher data bucket was detected for this computer.",
        )
    if capture.errors and fetched == 0:
        return (
            "error",
            "Browser-watcher buckets were detected, but none could be read: "
            + "; ".join(capture.errors),
        )
    if capture.event_count == 0:
        return (
            "no-events",
            f"{fetched} browser-watcher bucket(s) were read, but they contain no events for this day.",
        )
    if attributed == 0:
        return (
            "unmatched",
            f"{capture.event_count} browser event(s) were read, but none matched the foreground browser.",
        )
    detail = (
        f"Capturing websites: {attributed} attributed interval(s) from "
        f"{capture.event_count} browser event(s) across {fetched} bucket(s)."
    )
    if capture.errors:
        detail += " Some browser buckets could not be read."
    return "capturing", detail
