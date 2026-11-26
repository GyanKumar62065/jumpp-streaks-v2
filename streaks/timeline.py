"""Which local calendar days a user lived through, and when each one started and ended.

A user's timezone is the last `device_tz` seen on any event (a `tz_change` or any other).
Flying west repeats part of a date (merged into one span); flying east cuts a date short
(a short span the engine may treat as travel). All instants are UTC, so a DST day has its
real length (23h or 25h) and windows added to it are real elapsed time.
"""

from collections import defaultdict
from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from streaks import rules
from streaks.models import DaySpan, Event, User

_Segment = tuple[str, datetime, datetime]  # (timezone, start, end)
_Piece = tuple[date, datetime, datetime]


def get_local_date(instant: datetime, tz: str) -> date:
    return instant.astimezone(ZoneInfo(tz)).date()


def get_local_midnight(day: date, tz: str) -> datetime:
    """As a UTC instant: arithmetic on it is elapsed time, not wall-clock time."""
    return datetime.combine(day, time.min, ZoneInfo(tz)).astimezone(UTC)


def get_full_day_span(day: date, tz: str) -> DaySpan:
    start, end = get_local_midnight(day, tz), get_local_midnight(day + timedelta(days=1), tz)
    return DaySpan(date=day, start=start, end=end, length=end - start)


def _compose_tz_starts(user: User, device_events: list[Event], as_of: datetime) -> list[tuple[str, datetime]]:
    """(timezone, from instant) each time the device timezone changes, starting at home_tz."""
    first_midnight = get_local_midnight(get_local_date(user.signup_at, user.home_tz), user.home_tz)
    starts = [(user.home_tz, first_midnight)]
    seen = sorted(
        (event for event in device_events if user.signup_at < event.client_ts < as_of),
        key=lambda event: (event.client_ts, event.event_id),
    )
    for event in seen:
        if event.device_tz != starts[-1][0]:
            starts.append((event.device_tz, event.client_ts))
    return starts


def _compose_segments(user: User, device_events: list[Event], as_of: datetime) -> list[_Segment]:
    if as_of < user.signup_at:
        return []
    starts = _compose_tz_starts(user, device_events, as_of)

    final_tz = starts[-1][0]
    end_of_today = get_local_midnight(get_local_date(as_of, final_tz) + timedelta(days=1), final_tz)
    ends = [start for _, start in starts[1:]] + [end_of_today]
    return [(tz, start, end) for (tz, start), end in zip(starts, ends) if end > start]


def _split_into_pieces(segment: _Segment) -> Iterator[_Piece]:
    tz, start, end = segment
    day = get_local_date(start, tz)
    while True:
        next_midnight = get_local_midnight(day + timedelta(days=1), tz)
        piece_start = max(start, get_local_midnight(day, tz))
        piece_end = min(end, next_midnight)
        if piece_end > piece_start:
            yield day, piece_start, piece_end
        if next_midnight >= end:
            return
        day += timedelta(days=1)


def _merge_pieces(pieces: list[_Piece]) -> list[DaySpan]:
    by_date: dict[date, list[_Piece]] = defaultdict(list)
    for piece in pieces:
        by_date[piece[0]].append(piece)
    return [
        DaySpan(
            date=day,
            start=min(start for _, start, _ in group),
            end=max(end for _, _, end in group),
            length=sum((end - start for _, start, end in group), timedelta()),
        )
        for day, group in sorted(by_date.items())
    ]


def get_day_spans(user: User, device_events: list[Event], as_of: datetime) -> list[DaySpan]:
    """Local days from max(signup date, HISTORY_START_DATE) through the local date of `as_of`.

    `device_events` are any of the user's events; their `device_tz` drives the timeline.
    """
    segments = _compose_segments(user, device_events, as_of)
    pieces = [piece for segment in segments for piece in _split_into_pieces(segment)]
    return [span for span in _merge_pieces(pieces) if span.date >= rules.HISTORY_START_DATE]
