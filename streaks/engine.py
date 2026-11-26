"""The streak engine: events in, day rows and a streak out. Pure; see spec §3.0 to §3.6.

Order of work:
  1. keep what we knew at `as_of`, dedupe
  2. classify each local day without freezes (§3.5 rows 2 to 6 and 8 to 10)
  3. walk the days: count, bridge, spend freezes on final misses, reset
  4. status and a one-line reason
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from streaks import rules
from streaks.models import (
    DayCode,
    DayRow,
    DaySpan,
    Event,
    EventType,
    Outage,
    StreakResult,
    StreakStatus,
    User,
    Video,
    Watch,
    WatchVerdict,
)
from streaks.timeline import get_day_spans, get_full_day_span
from streaks.watches import compose_watches, dedupe_events

LEARNED_CODES = frozenset({DayCode.LEARNED, DayCode.LEARNED_LATE_SYNC})
FINAL_MISS_CODES = frozenset(
    {DayCode.BELOW_THRESHOLD, DayCode.REJECTED_TAMPER, DayCode.REJECTED_TOO_LATE, DayCode.NO_ACTIVITY}
)
# Cheating is never bridged: a freeze can cover any other final miss.
_FREEZABLE_CODES = FINAL_MISS_CODES - {DayCode.REJECTED_TAMPER}

_PENDING_WINDOW = timedelta(hours=rules.PENDING_WINDOW_H)
_MAX_OFFLINE_DELAY = timedelta(hours=rules.MAX_OFFLINE_DELAY_H)
_MIN_DAY_LENGTH = timedelta(hours=rules.MIN_DAY_LENGTH_H)
_REASON_LOOKBACK_DAYS = 7


@dataclass(frozen=True)
class _DayContext:
    """What a day's classification needs beyond its own watches."""

    is_outage_user: bool
    outage: Outage
    as_of: datetime
    today: date
    latest_app_open: Event | None


def _get_queue_depth(app_open: Event) -> int:
    try:
        return int(app_open.meta.get("queue_depth", 0))
    except ValueError:
        return 0


def _get_pending_deadline(span: DaySpan, context: _DayContext) -> datetime | None:
    """When this missed day becomes final, or None if it already is."""
    if context.as_of < span.end + _PENDING_WINDOW:
        return span.end + _PENDING_WINDOW
    app_open = context.latest_app_open
    # u07 rule: the phone said events were still queued after this day ended.
    has_unsynced_events = (
        app_open is not None and app_open.received_at > span.end and _get_queue_depth(app_open) > 0
    )
    if has_unsynced_events and context.as_of < span.end + _MAX_OFFLINE_DELAY:
        return span.end + _MAX_OFFLINE_DELAY
    return None


def _is_learning_day(counted: list[Watch], counted_s: int) -> bool:
    return counted_s >= rules.MIN_DAILY_WATCH_S or any(watch.is_complete for watch in counted)


def _classify_final_miss(watches: list[Watch], counted: list[Watch], counted_s: int) -> tuple[DayCode, str]:
    if counted:
        return DayCode.BELOW_THRESHOLD, f"Watched {counted_s}s, under {rules.MIN_DAILY_WATCH_S}s and no lesson finished"
    unpublished = [watch for watch in watches if watch.verdict is WatchVerdict.TAMPER_UNPUBLISHED]
    if unpublished:
        return DayCode.REJECTED_TAMPER, f"Watch rejected: lesson {unpublished[0].video_id} was published after the claimed watch time"
    if any(watch.verdict is WatchVerdict.TAMPER_CLOCK_AHEAD for watch in watches):
        return DayCode.REJECTED_TAMPER, "Watch rejected: device clock was ahead of server time"
    if watches:
        return DayCode.REJECTED_TOO_LATE, f"Watch synced more than {rules.MAX_OFFLINE_DELAY_H}h late"
    return DayCode.NO_ACTIVITY, "No lesson watched"


def _classify_day(span: DaySpan, watches: list[Watch], context: _DayContext) -> DayRow:
    """Spec §3.5 in order. Freezes are applied later, in the streak walk."""
    counted = [watch for watch in watches if watch.verdict.is_counted]
    counted_s = sum(watch.counted_s for watch in counted)

    def row(code: DayCode, detail: str) -> DayRow:
        return DayRow(date=span.date, code=code, counted_watch_s=counted_s, detail=detail)

    if _is_learning_day(counted, counted_s):
        on_time = [watch for watch in counted if watch.verdict is WatchVerdict.TRUSTED]
        if not _is_learning_day(on_time, sum(watch.counted_s for watch in on_time)):
            return row(DayCode.LEARNED_LATE_SYNC, f"Watched {counted_s}s offline, synced later")
        return row(DayCode.LEARNED, f"Watched {counted_s}s")
    if span.date == context.today:
        return row(DayCode.TODAY_OPEN, "Today, no qualifying lesson yet")
    overlaps_outage = context.outage.start < span.end and context.outage.end > span.start
    if context.is_outage_user and overlaps_outage:
        return row(DayCode.PROTECTED_OUTAGE, f"Our {context.outage.start:%d %b} ingestion outage lost events; day protected")
    if span.length < _MIN_DAY_LENGTH:
        hours = span.length.total_seconds() / 3600
        return row(DayCode.SKIPPED_TRAVEL, f"Timezone change made this day only {hours:.1f}h long")
    deadline = _get_pending_deadline(span, context)
    if deadline is not None:
        return row(DayCode.PENDING, f"No lesson synced yet; final at {deadline.isoformat()}")
    return row(*_classify_final_miss(watches, counted, counted_s))


def _apply_streak_and_freezes(
    rows: list[DayRow], carry_in: int, freezes_available: int
) -> tuple[list[DayRow], int, int]:
    """Walk days oldest first. Returns (rows with freezes applied, streak, freezes used)."""
    streak, freezes_used, walked = carry_in, 0, []
    for day in rows:
        if day.code in LEARNED_CODES:
            streak += 1
        elif day.code in FINAL_MISS_CODES:
            # Never burn a freeze on a streak that is already 0.
            if day.code in _FREEZABLE_CODES and streak > 0 and freezes_used < freezes_available:
                freezes_used += 1
                day = replace(day, code=DayCode.PROTECTED_FREEZE, detail=f"Freeze used. {day.detail}")
            else:
                streak = 0
        walked.append(day)
    return walked, streak, freezes_used


def _compose_status(rows: list[DayRow], streak: int) -> StreakStatus:
    if streak == 0:
        return StreakStatus.BROKEN
    if any(day.code is DayCode.PENDING for day in rows):
        return StreakStatus.PENDING
    if rows and rows[-1].code in LEARNED_CODES:
        return StreakStatus.ACTIVE
    return StreakStatus.AT_RISK


def _compose_reason(rows: list[DayRow], streak: int, status: StreakStatus) -> str:
    if status is StreakStatus.BROKEN:
        resets = [day for day in rows if day.code in FINAL_MISS_CODES]
        if not resets:
            return "No learning day yet"
        last = resets[-1]
        return f"Streak reset on {last.date}: {last.code} ({last.detail})"
    if status is StreakStatus.PENDING:
        pending = next(day for day in rows if day.code is DayCode.PENDING)
        return f"{pending.date} is pending: {pending.detail}"
    notable = [
        day for day in rows[-_REASON_LOOKBACK_DAYS:]
        if day.code not in (DayCode.LEARNED, DayCode.TODAY_OPEN)
    ]
    if notable:
        last = notable[-1]
        return f"{streak}-day streak; {last.date} {last.code}: {last.detail}"
    return f"{streak}-day streak, learned every recent day"


def _count_purchases_for_synced_days(
    purchases: list[Event], rows: list[DayRow], spans: list[DaySpan], watches_by_day: dict[date, list[Watch]]
) -> int:
    """Purchases made after a day ended but before its late lesson arrived (u07)."""
    span_end_by_date = {span.date: span.end for span in spans}
    windows = []
    for day in rows:
        if day.code is DayCode.LEARNED_LATE_SYNC:
            synced_at = min(watch.received_at for watch in watches_by_day[day.date] if watch.verdict is WatchVerdict.LATE)
            windows.append((span_end_by_date[day.date], synced_at))
    return sum(
        1 for purchase in purchases
        if any(day_end <= purchase.received_at < synced_at for day_end, synced_at in windows)
    )


def _group_watches_by_day(watches: list[Watch]) -> dict[date, list[Watch]]:
    grouped: dict[date, list[Watch]] = defaultdict(list)
    for watch in watches:
        grouped[watch.day].append(watch)
    return grouped


def _add_spans_for_unmapped_watch_days(
    spans: list[DaySpan], watch_days: set[date], tz: str
) -> list[DaySpan]:
    """A watch whose device_tz never got a tz_change can land on a date the timeline lacks."""
    if not spans:
        return spans
    known = {span.date for span in spans}
    first, today = spans[0].date, spans[-1].date
    missing = [day for day in watch_days if first <= day <= today and day not in known]
    extra = [get_full_day_span(day, tz) for day in missing]
    return sorted(spans + extra, key=lambda span: span.date)


def compute_streak(
    user: User, events: list[Event], videos: dict[str, Video], outage: Outage, as_of: datetime
) -> StreakResult:
    """`events` are this user's raw events, unfiltered and undeduped."""
    known = dedupe_events([event for event in events if event.received_at <= as_of])
    watches_by_day = _group_watches_by_day(compose_watches(known, videos))
    spans = _add_spans_for_unmapped_watch_days(get_day_spans(user, known, as_of), set(watches_by_day), user.home_tz)
    app_opens = [event for event in known if event.event_type == EventType.APP_OPEN]
    context = _DayContext(
        is_outage_user=user.user_id in outage.affected_uids,
        outage=outage,
        as_of=as_of,
        today=spans[-1].date if spans else as_of.date(),
        latest_app_open=max(app_opens, key=lambda event: event.received_at, default=None),
    )
    rows = [_classify_day(span, watches_by_day.get(span.date, []), context) for span in spans]

    purchases = [event for event in known if event.event_type == EventType.FREEZE_PURCHASE]
    freezes_purchased = len(purchases)
    freezes_available = user.freeze_balance + freezes_purchased
    rows, streak, freezes_used = _apply_streak_and_freezes(rows, user.streak_carry_in, freezes_available)
    status = _compose_status(rows, streak)
    return StreakResult(
        user_id=user.user_id,
        as_of=as_of,
        current_streak=streak,
        status=status,
        reason=_compose_reason(rows, streak, status),
        days=rows,
        freezes_purchased=freezes_purchased,
        freezes_used=freezes_used,
        freezes_unused=freezes_available - freezes_used,
        freezes_refundable=min(
            _count_purchases_for_synced_days(purchases, rows, spans, watches_by_day),
            freezes_available - freezes_used,
        ),
    )
