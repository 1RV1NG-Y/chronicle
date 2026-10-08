"""Readable day groups that retain every exact activity for inspection."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import replace

from chronicle.models.activity_event import ActivityEvent
from chronicle.services.event_normalizer import format_duration_label, format_time_label


def build_calendar_events(events: Iterable[ActivityEvent]) -> list[ActivityEvent]:
    """Group contiguous same-app/site sessions and bursts of short switches.

    Never bridge missing recordings or idle boundaries. Mixed-app bursts contain
    only records shorter than a minute and span at most five minutes. Grouping is
    presentation only: original records remain attached in chronological order.
    """
    groups: list[list[ActivityEvent]] = []
    for event in sorted(events, key=lambda event: (event.start_time, event.end_time)):
        previous = groups[-1] if groups else []
        contiguous = previous and previous[-1].end_time == event.start_time
        same_context = previous and all(
            item.app_id.casefold() == event.app_id.casefold()
            and item.domain == event.domain
            for item in previous
        )
        short_burst = previous and all(item.duration_seconds < 60 for item in previous)
        short_burst = short_burst and event.duration_seconds < 60
        short_burst = short_burst and (event.end_time - previous[0].start_time).total_seconds() <= 300
        if contiguous and not event.is_idle and not previous[-1].is_idle and (same_context or short_burst):
            previous.append(event)
        else:
            groups.append([event])
    return [_group(items) for items in groups]


def _group(items: list[ActivityEvent]) -> ActivityEvent:
    if len(items) == 1:
        return items[0]
    first, last = items[0], items[-1]
    same_app = len({item.app_id.casefold() for item in items}) == 1
    same_domain = len({item.domain for item in items}) == 1
    names = list(dict.fromkeys(item.domain or item.display_name for item in items))
    duration = sum(item.duration_seconds for item in items)
    return replace(
        last,
        id="group-" + hashlib.blake2s("|".join(item.id for item in items).encode(), digest_size=8).hexdigest(),
        display_name=last.display_name if same_app else "Quick switches",
        app_id=last.app_id if same_app else "activity-group",
        title=last.title if same_app and same_domain else " · ".join(names),
        subtitle=f"{len(items)} activities",
        domain=last.domain if same_app and same_domain else "",
        url="",
        start_time=first.start_time,
        end_time=last.end_time,
        duration_seconds=duration,
        duration_label=format_duration_label(duration),
        time_label=format_time_label(first.start_time, last.end_time),
        is_browser=all(item.is_browser for item in items),
        accent=last.accent if same_app else "#A6A6AD",
        raw_json=json.dumps({"projection": "day", "record_ids": [item.id for item in items]}),
        source_count=sum(item.source_count for item in items),
        activities=tuple(items),
    )
