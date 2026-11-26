"""Domain values. Parsed once at the boundary, immutable afterwards."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import StrEnum


class EventType(StrEnum):
    APP_OPEN = "app_open"
    VIDEO_START = "video_start"
    VIDEO_END = "video_end"
    TZ_CHANGE = "tz_change"
    FREEZE_PURCHASE = "freeze_purchase"
    FREEZE_APPLIED = "freeze_applied"


class DayCode(StrEnum):
    LEARNED = "LEARNED"
    LEARNED_LATE_SYNC = "LEARNED_LATE_SYNC"
    TODAY_OPEN = "TODAY_OPEN"
    PENDING = "PENDING"
    PROTECTED_OUTAGE = "PROTECTED_OUTAGE"
    PROTECTED_FREEZE = "PROTECTED_FREEZE"
    SKIPPED_TRAVEL = "SKIPPED_TRAVEL"
    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    REJECTED_TAMPER = "REJECTED_TAMPER"
    REJECTED_TOO_LATE = "REJECTED_TOO_LATE"
    NO_ACTIVITY = "NO_ACTIVITY"


class StreakStatus(StrEnum):
    BROKEN = "BROKEN"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    AT_RISK = "AT_RISK"


class WatchVerdict(StrEnum):
    TRUSTED = "TRUSTED"
    LATE = "LATE"
    TAMPER_UNPUBLISHED = "TAMPER_UNPUBLISHED"
    TAMPER_CLOCK_AHEAD = "TAMPER_CLOCK_AHEAD"
    TOO_LATE = "TOO_LATE"

    @property
    def is_counted(self) -> bool:
        return self in (WatchVerdict.TRUSTED, WatchVerdict.LATE)


@dataclass(frozen=True)
class Event:
    event_id: str
    user_id: str
    event_type: str
    video_id: str | None
    watched_s: int | None
    client_ts: datetime
    device_tz: str
    received_at: datetime
    app_version: str
    meta: dict[str, str] = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True)
class User:
    user_id: str
    name: str
    signup_at: datetime
    home_tz: str
    plan: str
    freeze_balance: int
    streak_carry_in: int


@dataclass(frozen=True)
class Video:
    video_id: str
    duration_s: int
    published_at: datetime


@dataclass(frozen=True)
class Outage:
    start: datetime
    end: datetime
    affected_uids: frozenset[str]


@dataclass(frozen=True)
class Dataset:
    users: dict[str, User]
    videos: dict[str, Video]
    events: list[Event]
    outage: Outage

    def get_user_events(self, user_id: str) -> list[Event]:
        return [event for event in self.events if event.user_id == user_id]


@dataclass(frozen=True)
class ParseError:
    index: int
    message: str


@dataclass(frozen=True)
class DaySpan:
    """The instants a user spent on one local calendar date."""

    date: date
    start: datetime
    end: datetime
    length: timedelta


@dataclass(frozen=True)
class Watch:
    event_id: str
    video_id: str
    day: date
    started_at: datetime
    received_at: datetime
    counted_s: int
    is_complete: bool
    verdict: WatchVerdict


@dataclass(frozen=True)
class DayRow:
    date: date
    code: DayCode
    counted_watch_s: int
    detail: str


@dataclass(frozen=True)
class StreakResult:
    user_id: str
    as_of: datetime
    current_streak: int
    status: StreakStatus
    reason: str
    days: list[DayRow]
    freezes_purchased: int
    freezes_used: int
    freezes_unused: int
    freezes_refundable: int  # bought while a day looked missed, and that day later synced
