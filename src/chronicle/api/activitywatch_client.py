"""Date-aware stdlib client for Chronicle's local ActivityWatch source."""

from __future__ import annotations

import json
import os
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from chronicle.models.activity_event import (
    ActivityEvent,
    BrowserCapture,
    BrowserEventSource,
    SourceBatch,
)
from chronicle.services.event_normalizer import build_events


class ActivityWatchError(RuntimeError):
    """An explicit, recoverable local API or source-discovery failure."""

    recoverable = True

    def __init__(self, operation: str, reason: str) -> None:
        self.operation = operation
        self.reason = reason
        super().__init__(f"ActivityWatch {operation} failed: {reason}")


@dataclass(frozen=True, slots=True)
class _BrowserBucket:
    bucket_id: str
    browser_id: str



@dataclass(frozen=True, slots=True)
class _SelectedBuckets:
    window: str
    browser: tuple[_BrowserBucket, ...]
    afk: str | None


class ActivityWatchClient:
    """Fetch current-host ActivityWatch payloads without blocking the UI itself."""

    def __init__(
        self,
        endpoint: str = "http://localhost:5600/api/0",
        *,
        timeout: float = 3.0,
        hostname: str | None = None,
        local_timezone: tzinfo | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._timeout = timeout
        self._hostname = hostname or socket.gethostname()
        self._local_timezone = local_timezone or _system_timezone()

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def local_timezone(self) -> tzinfo:
        return self._local_timezone

    def get_buckets(self) -> dict[str, Mapping[str, Any]]:
        payload = self._request_json("/buckets", operation="bucket discovery")
        if not isinstance(payload, Mapping):
            raise ActivityWatchError("bucket discovery", "response is not an object")
        buckets: dict[str, Mapping[str, Any]] = {}
        for key, value in payload.items():
            if not isinstance(value, Mapping):
                continue
            bucket_id = str(value.get("id") or key)
            buckets[bucket_id] = value
        return buckets

    def get_events(
        self,
        bucket_id: str,
        *,
        start: datetime,
        end: datetime,
    ) -> list[Mapping[str, Any]]:
        query = urlencode(
            {"start": start.isoformat(), "end": end.isoformat(), "limit": -1}
        )
        encoded_id = quote(bucket_id, safe="")
        payload = self._request_json(
            f"/buckets/{encoded_id}/events?{query}",
            operation=f"event fetch for {bucket_id}",
        )
        if not isinstance(payload, list):
            raise ActivityWatchError(
                f"event fetch for {bucket_id}", "response is not an array"
            )
        return [event for event in payload if isinstance(event, Mapping)]

    def load_day_sources(self, selected_day: date) -> SourceBatch:
        """Fetch a raw source batch bounded by that day's two local midnights.

        Midnights are constructed independently, rather than adding 24 hours, so
        daylight-saving transition days retain their true 23/25-hour bounds.
        """

        if isinstance(selected_day, datetime):
            selected_day = selected_day.date()
        if not isinstance(selected_day, date):
            raise TypeError("selected_day must be a date")
        next_day = selected_day + timedelta(days=1)
        start = datetime.combine(selected_day, time.min, tzinfo=self._local_timezone)
        end = datetime.combine(next_day, time.min, tzinfo=self._local_timezone)
        selected = self._select_buckets(self.get_buckets())
        window_events = tuple(self.get_events(selected.window, start=start, end=end))
        browser_events: list[BrowserEventSource] = []
        fetched_browser_ids: list[str] = []
        browser_errors: list[str] = []
        for browser_bucket in selected.browser:
            try:
                payloads = self.get_events(
                    browser_bucket.bucket_id,
                    start=start,
                    end=end,
                )
            except ActivityWatchError as error:
                browser_errors.append(
                    f"{browser_bucket.bucket_id}: {error.reason}"
                )
                continue
            fetched_browser_ids.append(browser_bucket.bucket_id)
            browser_events.extend(
                BrowserEventSource(
                    bucket_id=browser_bucket.bucket_id,
                    browser_id=browser_bucket.browser_id,
                    payload=event,
                )
                for event in payloads
            )
        capture = BrowserCapture(
            discovered_bucket_ids=tuple(
                browser_bucket.bucket_id for browser_bucket in selected.browser
            ),
            fetched_bucket_ids=tuple(fetched_browser_ids),
            event_count=len(browser_events),
            errors=tuple(browser_errors),
        )
        return SourceBatch(
            day_start=start,
            day_end=end,
            window_events=window_events,
            browser_events=tuple(browser_events),
            afk_events=(
                tuple(self.get_events(selected.afk, start=start, end=end))
                if selected.afk is not None
                else ()
            ),
            browser_capture=capture,
        )

    def load_day_events(self, selected_day: date) -> list[ActivityEvent]:
        """Fetch and canonicalize one local day."""

        return build_events(self.load_day_sources(selected_day))

    def _select_buckets(
        self, buckets: Mapping[str, Mapping[str, Any]]
    ) -> _SelectedBuckets:
        by_kind: dict[str, list[tuple[str, Mapping[str, Any]]]] = {
            "window": [],
            "browser": [],
            "afk": [],
        }
        for bucket_id, metadata in buckets.items():
            kind = _bucket_kind(bucket_id, metadata)
            if kind is None:
                continue
            if kind == "browser":
                if not _is_local_browser_bucket(bucket_id, metadata, self._hostname):
                    continue
            elif not _is_current_host(bucket_id, metadata, self._hostname):
                continue
            by_kind[kind].append((bucket_id, metadata))

        window = _latest_bucket(by_kind["window"])
        if window is None:
            raise ActivityWatchError(
                "bucket discovery",
                f"no current-host window bucket for {self._hostname}",
            )
        return _SelectedBuckets(
            window=window,
            browser=tuple(
                _BrowserBucket(
                    bucket_id=bucket_id,
                    browser_id=_browser_id(bucket_id, metadata),
                )
                for bucket_id, metadata in sorted(
                    by_kind["browser"], key=lambda item: item[0]
                )
            ),
            afk=_latest_bucket(by_kind["afk"]),
        )

    def _request_json(self, path: str, *, operation: str) -> Any:
        request = Request(
            f"{self._endpoint}{path}",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                body = response.read()
            return json.loads(body.decode("utf-8"))
        except HTTPError as error:
            raise ActivityWatchError(
                operation, f"HTTP {error.code} {error.reason}"
            ) from error
        except URLError as error:
            reason = getattr(error, "reason", error)
            raise ActivityWatchError(operation, str(reason)) from error
        except (TimeoutError, OSError) as error:
            raise ActivityWatchError(operation, str(error)) from error
        except (JSONDecodeError, UnicodeDecodeError) as error:
            raise ActivityWatchError(operation, "invalid JSON response") from error


def _bucket_kind(bucket_id: str, metadata: Mapping[str, Any]) -> str | None:
    bucket_type = str(metadata.get("type") or "").casefold()
    client = str(metadata.get("client") or "").casefold()
    text = " ".join((bucket_id.casefold(), bucket_type, client))
    if "afk" in text or "afkstatus" in bucket_type:
        return "afk"
    if "web.tab" in bucket_type or "browser" in text or "watcher-web" in text:
        return "browser"
    if "window" in text or "currentwindow" in bucket_type:
        return "window"
    return None


def _is_current_host(
    bucket_id: str, metadata: Mapping[str, Any], hostname: str
) -> bool:
    expected = hostname.casefold()
    expected_short = expected.split(".", 1)[0]
    bucket_host = str(metadata.get("hostname") or "").casefold()
    if bucket_host:
        actual_short = bucket_host.split(".", 1)[0]
        return bucket_host == expected or actual_short == expected_short
    lowered_id = bucket_id.casefold()
    return expected in lowered_id or expected_short in lowered_id

def _is_local_browser_bucket(
    bucket_id: str,
    metadata: Mapping[str, Any],
    hostname: str,
) -> bool:
    bucket_host = str(metadata.get("hostname") or "").strip().casefold()
    if bucket_host and bucket_host != "unknown":
        return _is_current_host(bucket_id, metadata, hostname)
    bucket_type = str(metadata.get("type") or "").casefold()
    client = str(metadata.get("client") or "").casefold()
    return (
        bucket_type == "web.tab.current"
        and (
            client == "aw-client-web"
            or bucket_id.casefold().startswith("aw-watcher-web-")
        )
    )


def _browser_id(bucket_id: str, metadata: Mapping[str, Any]) -> str:
    lowered = bucket_id.casefold()
    prefix = "aw-watcher-web-"
    raw = lowered[len(prefix) :] if lowered.startswith(prefix) else lowered
    bucket_host = str(metadata.get("hostname") or "").strip().casefold()
    suffixes = [
        bucket_host,
        bucket_host.split(".", 1)[0] if bucket_host else "",
    ]
    for suffix in sorted({value for value in suffixes if value and value != "unknown"}, key=len, reverse=True):
        marker = f"_{suffix}"
        if raw.endswith(marker):
            raw = raw[: -len(marker)]
            break
    return raw.strip("_-") or "unknown"


def _latest_bucket(
    candidates: list[tuple[str, Mapping[str, Any]]],
) -> str | None:
    if not candidates:
        return None
    bucket_id, _metadata = max(
        candidates,
        key=lambda item: (
            str(item[1].get("last_updated") or item[1].get("created") or ""),
            item[0],
        ),
    )
    return bucket_id


def _system_timezone() -> tzinfo:
    candidates: list[str] = []
    configured = os.environ.get("TZ", "").lstrip(":")
    if configured:
        candidates.append(configured)
    try:
        resolved = Path("/etc/localtime").resolve().as_posix()
        marker = "/zoneinfo/"
        if marker in resolved:
            candidates.append(resolved.split(marker, 1)[1])
    except OSError:
        pass
    try:
        configured_file = Path("/etc/timezone").read_text(encoding="utf-8").strip()
        if configured_file:
            candidates.append(configured_file)
    except OSError:
        pass
    for name in candidates:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            continue
    return datetime.now().astimezone().tzinfo or timezone.utc
