"""Build canonical, mutually-exclusive Chronicle records from ActivityWatch heartbeats."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from chronicle.models.activity_event import ActivityEvent, BrowserEventSource, SourceBatch

# Window watcher pulses describe coverage until the next pulse. Gaps larger than this
# are deliberately left empty instead of inventing activity while a watcher was down.
MAX_HEARTBEAT_GAP_SECONDS = 15.0

_ACCENTS = (
    "#72B7F2",
    "#B59AF4",
    "#7CCB9B",
    "#E58AA8",
    "#67C6D1",
    "#D7A6E8",
    "#9BCB6B",
    "#F1C75B",
)
_KNOWN_ACCENTS = {
    "brave": "#F2A65A",
    "brave-browser": "#F2A65A",
    "chromium": "#76A7FA",
    "code": "#67C6D1",
    "codex-widget": "#9BCB6B",
    "firefox": "#E58AA8",
    "google-chrome": "#7FA8F5",
    "idle": "#414A57",
    "org.gnome.nautilus": "#7CCB9B",
    "org.gnome.terminal": "#B59AF4",
    "terminal": "#B59AF4",
    "thorium": "#72B7F2",
    "thorium-browser": "#72B7F2",
}
_DISPLAY_NAMES = {
    "brave": "Brave",
    "brave-browser": "Brave",
    "chromium": "Chromium",
    "code": "Visual Studio Code",
    "codex-widget": "Codex Widget",
    "firefox": "Firefox",
    "google-chrome": "Google Chrome",
    "kitty": "Terminal",
    "org.gnome.console": "Console",
    "org.gnome.nautilus": "Files",
    "org.gnome.terminal": "Terminal",
    "org.telegram.desktop": "Telegram",
    "telegram-desktop": "Telegram",
    "thorium-browser": "Thorium",
}
_BROWSER_MARKERS = (
    "brave",
    "browser",
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "librewolf",
    "opera",
    "thorium",
    "vivaldi",
)


@dataclass(frozen=True, slots=True)
class _WindowSource:
    source_id: int
    start: datetime
    end: datetime
    app_id: str
    title: str
    subtitle: str
    payload: Mapping[str, Any]
    rank: str


@dataclass(frozen=True, slots=True)
class _BrowserSource:
    source_id: int
    bucket_id: str
    browser_id: str
    start: datetime
    end: datetime
    title: str
    domain: str
    url: str
    payload: Mapping[str, Any]
    rank: str


@dataclass(slots=True)
class _Segment:
    start: datetime
    end: datetime
    app_id: str
    title: str
    subtitle: str
    context_rank: tuple[datetime, str]
    window_sources: list[_WindowSource] = field(default_factory=list)
    browser_sources: list[_BrowserSource] = field(default_factory=list)


@dataclass(slots=True)
class _IdleSpan:
    start: datetime
    end: datetime
    payloads: list[Mapping[str, Any]] = field(default_factory=list)


def build_events(batch: SourceBatch) -> list[ActivityEvent]:
    """Project one raw source batch through the canonical segment pipeline."""

    return normalize_events(
        batch.window_events,
        batch.browser_events,
        batch.afk_events,
        day_start=batch.day_start,
        day_end=batch.day_end,
    )


def normalize_events(
    window_events: Iterable[Mapping[str, Any]] = (),
    browser_events: Iterable[Mapping[str, Any] | BrowserEventSource] = (),
    afk_events: Iterable[Mapping[str, Any]] = (),
    *,
    day_start: datetime | None = None,
    day_end: datetime | None = None,
) -> list[ActivityEvent]:
    """Return positive, ordered records with AFK removed from active activity.

    Zero-duration window heartbeats cover only the interval to the next sample and
    only when that gap is at most :data:`MAX_HEARTBEAT_GAP_SECONDS`. A final or
    otherwise unattached instant is dropped. Browser payloads are context, never
    standalone activity. Known browser sources enrich matching foreground spans;
    ambiguous browser sources are assigned only to the best matching span.
    """

    bounds = _bounds(day_start, day_end)
    windows = _window_sources(tuple(window_events), bounds)
    active = _atomize_windows(windows)
    active = _coalesce_same_app(active)

    idle = _idle_spans(tuple(afk_events), bounds)
    active = _subtract_idle(active, idle)
    active = _coalesce_same_app(active)

    browsers = _browser_sources(tuple(browser_events), bounds)
    active = _apply_browser_context(active, browsers)

    records: list[ActivityEvent] = []
    records.extend(_activity_event(segment) for segment in active)
    records.extend(_idle_event(span) for span in idle)
    records.sort(key=lambda event: (event.start_time, event.end_time, event.is_idle, event.id))
    return records


def accent_for_app(app_id: str, *, idle: bool = False) -> str:
    """Return a deterministic, application-specific accent."""

    key = "idle" if idle else app_id.strip().lower()
    if key in _KNOWN_ACCENTS:
        return _KNOWN_ACCENTS[key]
    digest = hashlib.blake2s(key.encode("utf-8"), digest_size=1).digest()[0]
    return _ACCENTS[digest % len(_ACCENTS)]


def display_name_for_app(app_id: str) -> str:
    """Turn executable and reverse-DNS application identifiers into readable names."""

    key = app_id.strip().lower()
    if key in _DISPLAY_NAMES:
        return _DISPLAY_NAMES[key]
    base = Path(app_id.strip()).name.removesuffix(".desktop")
    reverse_dns = base.split(".")
    if len(reverse_dns) >= 3 and reverse_dns[0].lower() in {"com", "io", "net", "org"}:
        base = reverse_dns[-1]
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", base)
    words = re.sub(r"[_-]+", " ", words).strip().split()
    if not words:
        return "Unknown app"
    return " ".join(word.upper() if len(word) <= 2 else word.capitalize() for word in words)


def format_time_label(start: datetime, end: datetime) -> str:
    return f"{start.astimezone():%H:%M}–{end.astimezone():%H:%M}"


def format_duration_label(seconds: float) -> str:
    if seconds < 60:
        return "<1 min"
    minutes = max(1, int(math.floor((seconds + 30) / 60)))
    hours, minutes = divmod(minutes, 60)
    if not hours:
        return f"{minutes} min"
    if not minutes:
        return f"{hours} hr"
    return f"{hours} hr {minutes} min"


def _bounds(
    day_start: datetime | None, day_end: datetime | None
) -> tuple[datetime, datetime] | None:
    if day_start is None and day_end is None:
        return None
    if day_start is None or day_end is None or day_end <= day_start:
        raise ValueError("day_start and day_end must form a positive interval")
    return day_start, day_end


def _window_sources(
    payloads: tuple[Mapping[str, Any], ...],
    bounds: tuple[datetime, datetime] | None,
) -> list[_WindowSource]:
    parsed: list[tuple[int, datetime, float, datetime | None, Mapping[str, Any], str]] = []
    for source_id, payload in enumerate(payloads):
        start = _parse_timestamp(payload.get("timestamp") or payload.get("start"))
        if start is None:
            continue
        duration = max(0.0, _number(payload.get("duration")))
        explicit_end = _parse_timestamp(payload.get("end") or payload.get("endTime"))
        parsed.append((source_id, start, duration, explicit_end, payload, _payload_key(payload)))
    parsed.sort(key=lambda item: (item[1], item[5], item[0]))

    unique_starts = sorted({item[1] for item in parsed})
    next_start = {start: unique_starts[index + 1] for index, start in enumerate(unique_starts[:-1])}
    sources: list[_WindowSource] = []
    for source_id, start, duration, explicit_end, payload, rank in parsed:
        if explicit_end is not None and explicit_end > start:
            end = explicit_end
        elif duration > 0:
            end = start + timedelta(seconds=duration)
        else:
            end = next_start.get(start)
            if end is None or (end - start).total_seconds() > MAX_HEARTBEAT_GAP_SECONDS:
                continue
        following = next_start.get(start)
        if following is not None:
            end = min(end, following)
        clipped = _clip(start, end, bounds)
        if clipped is None:
            continue
        data = _event_data(payload)
        app_id = _string(data.get("app") or data.get("app_id") or "unknown")
        sources.append(
            _WindowSource(
                source_id=source_id,
                start=clipped[0],
                end=clipped[1],
                app_id=app_id,
                title=_string(data.get("title") or data.get("window") or "Untitled window"),
                subtitle=_string(data.get("subtitle") or data.get("project")),
                payload=payload,
                rank=rank,
            )
        )
    return sources


def _atomize_windows(sources: list[_WindowSource]) -> list[_Segment]:
    if not sources:
        return []
    boundaries = sorted({point for source in sources for point in (source.start, source.end)})
    ordered_sources = sorted(sources, key=lambda source: (source.start, source.end, source.rank))
    active: list[_WindowSource] = []
    cursor = 0
    segments: list[_Segment] = []
    for start, end in zip(boundaries, boundaries[1:]):
        active = [source for source in active if source.end > start]
        while cursor < len(ordered_sources) and ordered_sources[cursor].start <= start:
            source = ordered_sources[cursor]
            cursor += 1
            if source.end > start:
                active.append(source)
        covering = [source for source in active if source.start < end and source.end > start]
        if not covering:
            continue
        winner = max(covering, key=lambda source: (source.start, source.rank))
        same_app = [
            source for source in covering if source.app_id.casefold() == winner.app_id.casefold()
        ]
        segments.append(
            _Segment(
                start=start,
                end=end,
                app_id=winner.app_id,
                title=winner.title,
                subtitle=winner.subtitle,
                context_rank=(winner.start, winner.rank),
                window_sources=_unique_window_sources(same_app),
            )
        )
    return segments


def _coalesce_same_app(segments: list[_Segment]) -> list[_Segment]:
    merged: list[_Segment] = []
    for segment in segments:
        gap_seconds = (
            (segment.start - merged[-1].end).total_seconds() if merged else math.inf
        )
        if (
            merged
            and gap_seconds == 0
            and merged[-1].app_id.casefold() == segment.app_id.casefold()
            and merged[-1].title == segment.title
            and merged[-1].subtitle == segment.subtitle
        ):
            _merge_segment(merged[-1], segment)
        else:
            merged.append(_clone_segment(segment))
    return merged


def _idle_spans(
    payloads: tuple[Mapping[str, Any], ...],
    bounds: tuple[datetime, datetime] | None,
) -> list[_IdleSpan]:
    spans: list[_IdleSpan] = []
    for payload in payloads:
        data = _event_data(payload)
        status = _string(data.get("status")).lower()
        if status not in {"afk", "away", "idle"} and data.get("afk") is not True:
            continue
        interval = _positive_interval(payload, bounds)
        if interval is not None:
            spans.append(_IdleSpan(interval[0], interval[1], [payload]))
    spans.sort(key=lambda span: (span.start, span.end, _payload_key(span.payloads[0])))
    merged: list[_IdleSpan] = []
    for span in spans:
        if merged and span.start <= merged[-1].end:
            merged[-1].end = max(merged[-1].end, span.end)
            merged[-1].payloads.extend(span.payloads)
        else:
            merged.append(_IdleSpan(span.start, span.end, list(span.payloads)))
    return merged


def _subtract_idle(active: list[_Segment], idle: list[_IdleSpan]) -> list[_Segment]:
    result: list[_Segment] = []
    for segment in active:
        pieces = [(segment.start, segment.end)]
        for span in idle:
            if span.end <= segment.start:
                continue
            if span.start >= segment.end:
                break
            next_pieces: list[tuple[datetime, datetime]] = []
            for start, end in pieces:
                if span.end <= start or span.start >= end:
                    next_pieces.append((start, end))
                    continue
                if start < span.start:
                    next_pieces.append((start, span.start))
                if span.end < end:
                    next_pieces.append((span.end, end))
            pieces = next_pieces
        for start, end in pieces:
            if end > start:
                piece = _clone_segment(segment)
                piece.start = start
                piece.end = end
                result.append(piece)
    result.sort(key=lambda segment: (segment.start, segment.end, segment.app_id.casefold()))
    return result


def _browser_sources(
    entries: tuple[Mapping[str, Any] | BrowserEventSource, ...],
    bounds: tuple[datetime, datetime] | None,
) -> list[_BrowserSource]:
    sources: list[_BrowserSource] = []
    for source_id, entry in enumerate(entries):
        if isinstance(entry, BrowserEventSource):
            payload = entry.payload
            bucket_id = entry.bucket_id
            browser_id = entry.browser_id
        else:
            payload = entry
            data = _event_data(payload)
            bucket_id = _string(payload.get("bucket_id"))
            browser_id = _string(data.get("browser") or payload.get("browser_id"))
        interval = _positive_interval(payload, bounds)
        if interval is None:
            continue
        data = _event_data(payload)
        url = _string(data.get("url") or data.get("uri"))
        domain = _domain_from_url(url) or _string(data.get("domain"))
        sources.append(
            _BrowserSource(
                source_id=source_id,
                bucket_id=bucket_id,
                browser_id=browser_id.casefold() or "unknown",
                start=interval[0],
                end=interval[1],
                title=_string(data.get("title") or domain or "Browser activity"),
                domain=domain,
                url=url,
                payload=payload,
                rank=_payload_key(payload),
            )
        )
    return sorted(sources, key=lambda source: (source.start, source.end, source.rank))


def _apply_browser_context(
    active: list[_Segment],
    browsers: list[_BrowserSource],
) -> list[_Segment]:
    assigned: dict[int, list[_BrowserSource]] = {}
    for browser in browsers:
        matches = [
            (index, segment, _overlap(segment.start, segment.end, browser.start, browser.end))
            for index, segment in enumerate(active)
            if _is_browser_app(segment.app_id)
            and _browser_source_matches(browser, segment)
        ]
        matches = [match for match in matches if match[2] > 0]
        if not matches:
            continue
        if browser.browser_id == "unknown":
            index, _segment, _seconds = max(
                matches,
                key=lambda match: (match[2], match[1].start, -match[0]),
            )
            assigned.setdefault(index, []).append(browser)
        else:
            for index, _segment, _seconds in matches:
                assigned.setdefault(index, []).append(browser)

    output: list[_Segment] = []
    for index, segment in enumerate(active):
        sources = assigned.get(index, [])
        if not sources:
            output.append(_clone_segment(segment))
            continue
        boundaries = {segment.start, segment.end}
        for source in sources:
            boundaries.add(max(segment.start, source.start))
            boundaries.add(min(segment.end, source.end))
        ordered = sorted(boundaries)
        for start, end in zip(ordered, ordered[1:]):
            if end <= start:
                continue
            piece = _clone_segment(segment)
            piece.start = start
            piece.end = end
            piece.browser_sources = []
            covering = [
                source
                for source in sources
                if source.start < end and source.end > start
            ]
            if covering:
                representative = max(
                    covering,
                    key=lambda source: (source.start, source.rank, source.source_id),
                )
                piece.browser_sources = [representative]
                piece.title = representative.title or piece.title
                piece.subtitle = representative.domain or piece.subtitle
            output.append(piece)
    return _coalesce_website_context(output)


def _coalesce_website_context(segments: list[_Segment]) -> list[_Segment]:
    merged: list[_Segment] = []
    for segment in segments:
        if (
            merged
            and merged[-1].end == segment.start
            and merged[-1].app_id.casefold() == segment.app_id.casefold()
            and _website_context_key(merged[-1]) == _website_context_key(segment)
        ):
            _merge_segment(merged[-1], segment)
        else:
            merged.append(_clone_segment(segment))
    return merged


def _website_context_key(segment: _Segment) -> tuple[str, str, str]:
    url = segment.browser_sources[-1].url if segment.browser_sources else ""
    return url, segment.title, segment.subtitle

def _activity_event(segment: _Segment) -> ActivityEvent:
    browser_sources = _unique_browser_sources(segment.browser_sources)
    window_sources = _unique_window_sources(segment.window_sources)
    provenance = {
        "window": [source.payload for source in window_sources],
        "browser": [
            {
                "bucket_id": source.bucket_id,
                "browser_id": source.browser_id,
                "url": source.url,
                "event": source.payload,
            }
            for source in browser_sources
        ],
        "afk": [],
    }
    return _make_event(
        app_id=segment.app_id,
        title=segment.title,
        subtitle=segment.subtitle,
        domain=browser_sources[-1].domain if browser_sources else "",
        url=browser_sources[-1].url if browser_sources else "",
        start=segment.start,
        end=segment.end,
        idle=False,
        provenance=provenance,
        source_count=len(window_sources) + len(browser_sources),
    )


def _idle_event(span: _IdleSpan) -> ActivityEvent:
    return _make_event(
        app_id="idle",
        title="Away from computer",
        subtitle="No active input",
        domain="",
        url="",
        start=span.start,
        end=span.end,
        idle=True,
        provenance={"window": [], "browser": [], "afk": span.payloads},
        source_count=len(span.payloads),
    )


def _make_event(
    *,
    app_id: str,
    title: str,
    subtitle: str,
    domain: str,
    url: str,
    start: datetime,
    end: datetime,
    idle: bool,
    provenance: Mapping[str, Any],
    source_count: int,
) -> ActivityEvent:
    duration = (end - start).total_seconds()
    stable_key = f"{int(idle)}\0{app_id.casefold()}\0{start.isoformat()}"
    event_id = hashlib.sha1(stable_key.encode("utf-8")).hexdigest()[:16]
    return ActivityEvent(
        id=event_id,
        display_name="Idle" if idle else display_name_for_app(app_id),
        app_id=app_id,
        title=title,
        subtitle=subtitle,
        domain=domain,
        url=url,
        start_time=start,
        end_time=end,
        time_label=format_time_label(start, end),
        duration_label=format_duration_label(duration),
        duration_seconds=duration,
        accent=accent_for_app(app_id, idle=idle),
        is_browser=not idle and _is_browser_app(app_id),
        is_idle=idle,
        raw_json=json.dumps(
            provenance,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ),
        source_count=source_count,
    )


def _positive_interval(
    payload: Mapping[str, Any], bounds: tuple[datetime, datetime] | None
) -> tuple[datetime, datetime] | None:
    start = _parse_timestamp(payload.get("timestamp") or payload.get("start"))
    if start is None:
        return None
    explicit_end = _parse_timestamp(payload.get("end") or payload.get("endTime"))
    if explicit_end is not None and explicit_end > start:
        end = explicit_end
    else:
        duration = _number(payload.get("duration"))
        if duration <= 0:
            return None
        end = start + timedelta(seconds=duration)
    return _clip(start, end, bounds)


def _clip(
    start: datetime,
    end: datetime,
    bounds: tuple[datetime, datetime] | None,
) -> tuple[datetime, datetime] | None:
    if end <= start:
        return None
    if bounds is not None:
        start = max(start, bounds[0])
        end = min(end, bounds[1])
    return (start, end) if end > start else None


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith(("Z", "z")):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _event_data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, Mapping) else {}


def _payload_key(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _domain_from_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
        if not parsed.scheme:
            parsed = urlsplit(f"https://{url}")
    except ValueError:
        return ""
    if parsed.scheme.casefold() not in {"http", "https"}:
        return ""
    domain = (parsed.hostname or "").lower().rstrip(".")
    return domain[4:] if domain.startswith("www.") else domain
def _browser_source_matches(browser: _BrowserSource, segment: _Segment) -> bool:
    if _browser_identity_matches(browser.browser_id, segment.app_id):
        return True
    if browser.browser_id not in {"chrome", "chromium"}:
        return False
    if "thorium" not in segment.app_id.casefold():
        return False
    page_title = browser.title.casefold().strip()
    window_title = segment.title.casefold().strip()
    for suffix in (" - thorium", " — thorium", " – thorium"):
        if window_title.endswith(suffix):
            window_title = window_title[: -len(suffix)].rstrip()
            break
    return bool(page_title and page_title == window_title)




def _is_browser_app(app_id: str) -> bool:
    lowered = app_id.casefold()
    return any(marker in lowered for marker in _BROWSER_MARKERS)

def _browser_identity_matches(browser_id: str, app_id: str) -> bool:
    browser = browser_id.casefold().strip()
    app = app_id.casefold()
    if not browser or browser == "unknown":
        return True
    if browser == "brave":
        return "brave" in app
    if browser in {"firefox", "librewolf"}:
        return browser in app
    if browser in {"chrome", "chromium"}:
        return (
            "google-chrome" in app
            or app == "chrome"
            or "chromium" in app
        )
    if browser in {"opera", "safari", "edge", "vivaldi", "thorium"}:
        return browser in app
    return browser in app


def _overlap(
    left_start: datetime, left_end: datetime, right_start: datetime, right_end: datetime
) -> float:
    return max(0.0, (min(left_end, right_end) - max(left_start, right_start)).total_seconds())


def _merge_segment(target: _Segment, incoming: _Segment) -> None:
    target.end = incoming.end
    target.window_sources = _unique_window_sources(target.window_sources + incoming.window_sources)
    target.browser_sources = _unique_browser_sources(target.browser_sources + incoming.browser_sources)
    if incoming.context_rank >= target.context_rank:
        target.app_id = incoming.app_id
        target.title = incoming.title
        target.subtitle = incoming.subtitle
        target.context_rank = incoming.context_rank


def _clone_segment(segment: _Segment) -> _Segment:
    return _Segment(
        start=segment.start,
        end=segment.end,
        app_id=segment.app_id,
        title=segment.title,
        subtitle=segment.subtitle,
        context_rank=segment.context_rank,
        window_sources=list(segment.window_sources),
        browser_sources=list(segment.browser_sources),
    )


def _unique_window_sources(sources: list[_WindowSource]) -> list[_WindowSource]:
    return list({source.source_id: source for source in sources}.values())


def _unique_browser_sources(sources: list[_BrowserSource]) -> list[_BrowserSource]:
    return list({source.source_id: source for source in sources}.values())


def _string(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0
