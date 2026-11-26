"""Duplicate removal and the rules for trusting a watch's client clock (spec §3.2 to §3.4)."""

from collections.abc import Callable, Hashable, Iterable
from datetime import datetime, timedelta

from streaks import rules
from streaks.models import Event, EventType, Video, Watch, WatchVerdict
from streaks.timeline import get_local_date

_MAX_OFFLINE_DELAY = timedelta(hours=rules.MAX_OFFLINE_DELAY_H)
_MAX_CLOCK_AHEAD = timedelta(seconds=rules.MAX_CLOCK_AHEAD_S)
_LATE_SYNC_THRESHOLD = timedelta(hours=rules.LATE_SYNC_THRESHOLD_H)


def _sort_key_earliest_received(event: Event) -> tuple:
    # Earliest arrival wins, so the kept copy never depends on the order rows reached us.
    return (event.received_at, event.event_id)


def _keep_earliest_per_key(events: Iterable[Event], get_key: Callable[[Event], Hashable]) -> list[Event]:
    kept: dict[Hashable, Event] = {}
    for event in sorted(events, key=_sort_key_earliest_received):
        kept.setdefault(get_key(event), event)
    return list(kept.values())


def _get_content_key(event: Event) -> tuple:
    # 3.1.x resent batches with fresh event_ids; same content = same real-world event.
    return (event.user_id, event.event_type, event.video_id, event.client_ts)


def dedupe_events(events: list[Event]) -> list[Event]:
    by_id = _keep_earliest_per_key(events, lambda event: event.event_id)
    by_content = _keep_earliest_per_key(by_id, _get_content_key)
    return sorted(by_content, key=lambda event: (event.client_ts, event.event_id))


def _judge_watch(event: Event, video: Video, started_at: datetime) -> WatchVerdict:
    if video.published_at > started_at:
        return WatchVerdict.TAMPER_UNPUBLISHED
    if event.client_ts > event.received_at + _MAX_CLOCK_AHEAD:
        return WatchVerdict.TAMPER_CLOCK_AHEAD
    delay = event.received_at - event.client_ts
    if delay > _MAX_OFFLINE_DELAY:
        return WatchVerdict.TOO_LATE
    if delay > _LATE_SYNC_THRESHOLD:
        return WatchVerdict.LATE
    return WatchVerdict.TRUSTED


def _compose_watch(event: Event, video: Video) -> Watch:
    # Capped first: an inflated watched_s must not push the watch onto an earlier day.
    counted_s = min(event.watched_s, video.duration_s)
    # The day is where the user pressed play: end time minus watched seconds (u05 at 23:59).
    started_at = event.client_ts - timedelta(seconds=counted_s)
    return Watch(
        event_id=event.event_id,
        video_id=video.video_id,
        day=get_local_date(started_at, event.device_tz),
        started_at=started_at,
        received_at=event.received_at,
        counted_s=counted_s,
        is_complete=counted_s >= rules.COMPLETION_RATIO * video.duration_s,
        verdict=_judge_watch(event, video, started_at),
    )


def _is_watch_event(event: Event, videos: dict[str, Video]) -> bool:
    return (
        event.event_type == EventType.VIDEO_END
        and (event.watched_s or 0) > 0
        and event.video_id in videos
    )


def compose_watches(events: list[Event], videos: dict[str, Video]) -> list[Watch]:
    """Watches from already-deduped events. Unknown videos are rejected earlier, at ingest."""
    return [_compose_watch(event, videos[event.video_id]) for event in events if _is_watch_event(event, videos)]
