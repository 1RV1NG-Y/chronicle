"""Canonical source batches and UI-facing Chronicle activity records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class BrowserEventSource:
    """One browser-watcher event with its bucket identity preserved."""

    bucket_id: str
    browser_id: str
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class BrowserCapture:
    """Factual discovery and fetch diagnostics for optional website capture."""

    discovered_bucket_ids: tuple[str, ...] = ()
    fetched_bucket_ids: tuple[str, ...] = ()
    event_count: int = 0
    errors: tuple[str, ...] = ()



@dataclass(frozen=True, slots=True)
class SourceBatch:
    """Raw ActivityWatch payloads fetched for one independently bounded local day."""

    day_start: datetime
    day_end: datetime
    window_events: tuple[Mapping[str, Any], ...]
    browser_events: tuple[BrowserEventSource, ...] = ()
    afk_events: tuple[Mapping[str, Any], ...] = ()
    browser_capture: BrowserCapture = BrowserCapture()


@dataclass(frozen=True, slots=True)
class ActivityEvent:
    """A positive, mutually-exclusive interval exposed by Chronicle's Qt models."""

    id: str
    display_name: str
    app_id: str
    title: str
    subtitle: str
    domain: str
    url: str
    start_time: datetime
    end_time: datetime
    time_label: str
    duration_label: str
    duration_seconds: float
    accent: str
    is_idle: bool
    is_browser: bool
    raw_json: str
    source_count: int
    activities: tuple[ActivityEvent, ...] = ()
