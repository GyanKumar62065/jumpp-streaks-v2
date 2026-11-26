"""Shape engine results for people: the graded CSV and the support agent's table."""

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from datetime import date, datetime

from streaks import rules
from streaks.engine import FINAL_MISS_CODES, LEARNED_CODES, compute_streak
from streaks.models import Dataset, DayCode, DayRow, StreakResult, StreakStatus, User

ACTION_BY_CODE: dict[DayCode, str] = {
    DayCode.LEARNED: "No action.",
    DayCode.LEARNED_LATE_SYNC: "No action. The offline lesson counted.",
    DayCode.TODAY_OPEN: "No action. The day is still open.",
    DayCode.PENDING: "Wait. Don't restore or sell a freeze until it's final.",
    DayCode.PROTECTED_OUTAGE: "No action. Our outage, the day is protected.",
    DayCode.PROTECTED_FREEZE: "No action. A freeze covered this day.",
    DayCode.SKIPPED_TRAVEL: "No action. Timezone travel, the day is bridged.",
    DayCode.BELOW_THRESHOLD: (
        f"Don't restore. Explain the rule: {rules.MIN_DAILY_WATCH_S}s total "
        f"or one lesson ≥{rules.COMPLETION_RATIO:.0%} watched."
    ),
    DayCode.REJECTED_TAMPER: "Don't restore. The device clock didn't match lesson publish time or server time.",
    DayCode.REJECTED_TOO_LATE: f"Don't restore. Explain the {rules.MAX_OFFLINE_DELAY_H // 24}-day sync limit.",
    DayCode.NO_ACTIVITY: "Don't restore. Suggest a freeze next time.",
}


CSV_COLUMNS = ("user_id", "current_streak", "status", "reason")


@dataclass(frozen=True)
class SupportRow:
    date: date
    code: DayCode
    what_happened: str
    what_to_do: str


def compute_all_streaks(dataset: Dataset, as_of: datetime) -> list[StreakResult]:
    events_by_user = defaultdict(list)
    for event in dataset.events:
        events_by_user[event.user_id].append(event)
    return [
        compute_streak(user, events_by_user[user_id], dataset.videos, dataset.outage, as_of)
        for user_id, user in sorted(dataset.users.items())
    ]


def compose_streak_summary(result: StreakResult) -> dict:
    """One shape for the CSV row and the /streak response."""
    return {
        "user_id": result.user_id,
        "current_streak": result.current_streak,
        "status": result.status.value,
        "reason": result.reason,
    }


def compose_csv_rows(results: list[StreakResult]) -> list[dict]:
    return [compose_streak_summary(result) for result in results]


def compose_support_rows(result: StreakResult) -> list[SupportRow]:
    """Newest day first: agents usually ask about the last few days."""
    return [
        SupportRow(date=day.date, code=day.code, what_happened=day.detail, what_to_do=ACTION_BY_CODE[day.code])
        for day in reversed(result.days)
    ]


class ActionKind(StrEnum):
    REFUND = "REFUND"
    TAMPER = "TAMPER"
    BROKEN = "BROKEN"
    PENDING = "PENDING"


class ListFilter(StrEnum):
    ALL = "all"
    ACTION = "action"
    BROKEN = "broken"
    PENDING = "pending"


@dataclass(frozen=True)
class UserAction:
    kind: ActionKind
    text: str


@dataclass(frozen=True)
class UserListing:
    user: User
    result: StreakResult
    action: UserAction | None


def _get_streak_ending_day(days: list[DayRow]) -> DayRow | None:
    """The miss that ended the last run of counted days (u04: 6 Nov, not the latest failed day)."""
    last_learned = max((index for index, day in enumerate(days) if day.code in LEARNED_CODES), default=-1)
    return next((day for day in days[last_learned + 1:] if day.code in FINAL_MISS_CODES), None)


def compose_user_action(result: StreakResult) -> UserAction | None:
    """The one thing an agent should do for this user, most urgent first."""
    if result.freezes_refundable:
        amount = result.freezes_refundable * rules.FREEZE_PRICE_INR
        return UserAction(ActionKind.REFUND, f"Refund ₹{amount}: freeze bought for a day that later synced")
    tampered = [day.date for day in result.days if day.code is DayCode.REJECTED_TAMPER]
    if tampered:
        dates = ", ".join(f"{day:%d %b}" for day in tampered)
        return UserAction(ActionKind.TAMPER, f"Don't restore {dates}: the device clock didn't match. Flag to Trust & Safety")
    if result.status is StreakStatus.BROKEN:
        reset = _get_streak_ending_day(result.days)
        if reset is None:
            return UserAction(ActionKind.BROKEN, "No learning day yet. Point them to today's lesson")
        return UserAction(ActionKind.BROKEN, f"Explain the reset on {reset.date:%d %b}: {reset.detail}")
    if result.status is StreakStatus.PENDING:
        return UserAction(ActionKind.PENDING, f"Wait before replying. {result.reason}")
    return None


def compose_user_listings(dataset: Dataset, as_of: datetime) -> list[UserListing]:
    return [
        UserListing(user=dataset.users[result.user_id], result=result, action=compose_user_action(result))
        for result in compute_all_streaks(dataset, as_of)
    ]


def _matches_filter(listing: UserListing, list_filter: ListFilter) -> bool:
    if list_filter is ListFilter.ACTION:
        return listing.action is not None
    if list_filter is ListFilter.BROKEN:
        return listing.result.status is StreakStatus.BROKEN
    if list_filter is ListFilter.PENDING:
        return listing.result.status is StreakStatus.PENDING
    return True


def filter_listings(listings: list[UserListing], list_filter: ListFilter, query: str = "") -> list[UserListing]:
    needle = query.strip().lower()
    return [
        listing for listing in listings
        if _matches_filter(listing, list_filter)
        and (not needle or needle in listing.user.user_id.lower() or needle in listing.user.name.lower())
    ]
