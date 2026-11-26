import random
from datetime import date, datetime
from pathlib import Path

import pytest

from streaks.engine import compute_streak
from streaks.models import DayCode, StreakStatus
from streaks.parsing import load_dataset
from tests.conftest import make_event, make_learned_days, make_outage, make_user, make_watch

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime.fromisoformat("2026-11-15T10:00:00+05:30")
NO_OUTAGE = make_outage()


def _code_on(result, day: int) -> DayCode:
    return next(row.code for row in result.days if row.date == date(2026, 11, day))


def _all_days_except(*missed):
    return [day for day in range(1, 15) if day not in missed]


@pytest.mark.parametrize(
    ("watches", "expected"),
    [
        ([(60, "v_long", "10:00"), (60, "v_long", "11:00")], DayCode.LEARNED),
        ([(101, "v_104", "10:00")], DayCode.LEARNED),
        ([(30, "v_long", "10:00"), (30, "v_long", "11:00"), (30, "v_long", "12:00")], DayCode.BELOW_THRESHOLD),
    ],
    ids=["two_partials_reach_120s", "one_lesson_over_90_percent", "three_swipes"],
)
def test_day_counts_with_120s_total_or_one_complete_lesson(videos, watches, expected):
    events = [make_watch(f"2026-11-10T{clock}:00+05:30", seconds, video_id=video) for seconds, video, clock in watches]

    result = compute_streak(make_user(), events, videos, NO_OUTAGE, NOW)

    assert _code_on(result, 10) is expected


def test_outage_day_bridges_without_adding(videos):
    user = make_user("u08", streak_carry_in=300)
    events = make_learned_days(_all_days_except(9), user_id="u08")

    result = compute_streak(user, events, videos, make_outage("u08"), NOW)

    assert _code_on(result, 9) is DayCode.PROTECTED_OUTAGE
    assert result.current_streak == 313


def test_missed_day_is_pending_for_48h(videos):
    user = make_user(streak_carry_in=5)

    pending = compute_streak(user, make_learned_days(_all_days_except(13)), videos, NO_OUTAGE, NOW)
    final = compute_streak(user, make_learned_days(_all_days_except(12)), videos, NO_OUTAGE, NOW)

    assert _code_on(pending, 13) is DayCode.PENDING
    assert pending.status is StreakStatus.PENDING
    assert _code_on(final, 12) is DayCode.NO_ACTIVITY


@pytest.mark.parametrize(("queue_depth", "expected"), [("3", DayCode.PENDING), ("0", DayCode.NO_ACTIVITY)])
def test_unsynced_queue_keeps_day_pending(videos, queue_depth, expected):
    events = make_learned_days(_all_days_except(10))
    events.append(make_event("app_open", "2026-11-14T09:00:00+05:30", meta={"queue_depth": queue_depth}))

    result = compute_streak(make_user(streak_carry_in=5), events, videos, NO_OUTAGE, NOW)

    assert _code_on(result, 10) is expected


def test_late_sync_returns_used_freeze(videos):
    user = make_user(plan="premium", streak_carry_in=58)
    events = make_learned_days(_all_days_except(7))
    events.append(make_event("freeze_purchase", "2026-11-08T09:02:00+05:30", received_at="2026-11-08T03:32:02+00:00"))
    events.append(make_watch("2026-11-07T21:17:13+05:30", 125, received_at="2026-11-08T06:30:00+00:00"))

    before_sync = compute_streak(user, events, videos, NO_OUTAGE, datetime.fromisoformat("2026-11-08T08:00:00+05:30"))
    after_sync = compute_streak(user, events, videos, NO_OUTAGE, NOW)

    assert _code_on(before_sync, 7) is DayCode.PENDING
    assert _code_on(after_sync, 7) is DayCode.LEARNED_LATE_SYNC
    assert (after_sync.freezes_purchased, after_sync.freezes_used, after_sync.freezes_unused) == (1, 0, 1)
    assert after_sync.current_streak == 72


def test_final_miss_uses_freeze_from_balance(videos):
    user = make_user(plan="premium", freeze_balance=1, streak_carry_in=10)

    result = compute_streak(user, make_learned_days(_all_days_except(5)), videos, NO_OUTAGE, NOW)

    assert _code_on(result, 5) is DayCode.PROTECTED_FREEZE
    assert result.freezes_used == 1
    assert result.current_streak == 23


def test_freeze_is_never_spent_on_zero_streak(videos):
    user = make_user(freeze_balance=1, streak_carry_in=0)

    result = compute_streak(user, make_learned_days(_all_days_except(1)), videos, NO_OUTAGE, NOW)

    assert _code_on(result, 1) is DayCode.NO_ACTIVITY
    assert result.freezes_used == 0


def test_short_travel_day_is_skipped(videos):
    user = make_user(home_tz="America/Los_Angeles", signup_at="2026-08-20T09:00:00-07:00", streak_carry_in=17)
    events = make_learned_days(range(1, 10), tz="America/Los_Angeles", offset="-08:00")
    events.append(make_event("tz_change", "2026-11-11T07:40:00+13:00", device_tz="Pacific/Auckland"))
    events += make_learned_days(range(11, 15), tz="Pacific/Auckland", offset="+13:00")

    result = compute_streak(user, events, videos, NO_OUTAGE, NOW)

    assert _code_on(result, 10) is DayCode.SKIPPED_TRAVEL
    assert result.current_streak == 30


def test_result_is_independent_of_event_order():
    dataset = load_dataset(ROOT / "data", ROOT / "config" / "affected_uids.csv")
    shuffler = random.Random(1)
    for user in dataset.users.values():
        events = dataset.get_user_events(user.user_id)
        expected = compute_streak(user, events, dataset.videos, dataset.outage, NOW)
        for _ in range(5):
            shuffled = list(events)
            shuffler.shuffle(shuffled)
            assert compute_streak(user, shuffled, dataset.videos, dataset.outage, NOW) == expected


def test_events_received_after_as_of_are_ignored(videos):
    events = make_learned_days(_all_days_except(14))
    events.append(make_watch("2026-11-14T10:00:00+05:30", 130, received_at="2026-11-16T00:00:00+00:00"))

    result = compute_streak(make_user(streak_carry_in=5), events, videos, NO_OUTAGE, NOW)

    assert _code_on(result, 14) is DayCode.PENDING


def test_as_of_before_signup_returns_carry_in_and_no_days(videos):
    user = make_user(signup_at="2026-11-13T23:50:00+05:30", streak_carry_in=0)

    result = compute_streak(user, [], videos, NO_OUTAGE, datetime.fromisoformat("2026-11-10T10:00:00+05:30"))

    assert result.days == []
    assert result.current_streak == 0
    assert result.status is StreakStatus.BROKEN


def test_status_precedence_broken_wins_over_pending(videos):
    result = compute_streak(make_user(streak_carry_in=0), [], videos, NO_OUTAGE, NOW)

    assert _code_on(result, 13) is DayCode.PENDING
    assert result.status is StreakStatus.BROKEN


def test_today_learned_makes_status_active(videos):
    events = make_learned_days(range(1, 16))

    result = compute_streak(make_user(streak_carry_in=5), events, videos, NO_OUTAGE,
                            datetime.fromisoformat("2026-11-15T12:00:00+05:30"))

    assert _code_on(result, 15) is DayCode.LEARNED
    assert result.status is StreakStatus.ACTIVE
    assert result.current_streak == 20


# --- Open issues 1–7 -------------------------------------------------------------


def test_freeze_never_bridges_a_tampered_day(videos):
    user = make_user(plan="premium", freeze_balance=1, streak_carry_in=10)
    events = make_learned_days(_all_days_except(9))
    events.append(make_watch("2026-11-09T20:00:00+05:30", 130, video_id="v_new",
                             received_at="2026-11-10T14:38:13+00:00"))

    result = compute_streak(user, events, videos, NO_OUTAGE, NOW)

    assert _code_on(result, 9) is DayCode.REJECTED_TAMPER
    assert result.freezes_used == 0
    assert result.current_streak == 5  # reset on the 9th, then 10–14


def test_refund_only_for_a_freeze_bought_while_the_day_looked_missed(videos):
    user = make_user(plan="premium", streak_carry_in=58)
    events = make_learned_days(_all_days_except(7))
    events.append(make_event("freeze_purchase", "2026-11-08T09:02:00+05:30", received_at="2026-11-08T03:32:02+00:00"))
    events.append(make_watch("2026-11-07T21:17:13+05:30", 125, received_at="2026-11-08T06:30:00+00:00"))

    result = compute_streak(user, events, videos, NO_OUTAGE, NOW)

    assert result.freezes_refundable == 1


def test_unrelated_purchase_and_late_sync_are_not_refundable(videos):
    user = make_user(plan="premium", streak_carry_in=20)
    events = make_learned_days(_all_days_except(10))
    events.append(make_event("freeze_purchase", "2026-11-03T09:00:00+05:30"))
    events.append(make_watch("2026-11-10T21:00:00+05:30", 130, received_at="2026-11-11T09:00:00+00:00"))

    result = compute_streak(user, events, videos, NO_OUTAGE, NOW)

    assert _code_on(result, 10) is DayCode.LEARNED_LATE_SYNC
    assert result.freezes_refundable == 0


def test_small_late_watch_does_not_relabel_an_on_time_day(videos):
    events = [make_watch("2026-11-10T10:00:00+05:30", 130),
              make_watch("2026-11-10T11:00:00+05:30", 30, received_at="2026-11-11T09:00:00+00:00")]

    result = compute_streak(make_user(), events, videos, NO_OUTAGE, NOW)

    assert _code_on(result, 10) is DayCode.LEARNED


def test_today_uses_last_known_device_tz_without_tz_change(videos):
    events = make_learned_days(range(1, 8))
    events += make_learned_days(range(8, 15), tz="America/Los_Angeles", offset="-08:00")

    result = compute_streak(make_user(streak_carry_in=5), events, videos, NO_OUTAGE, NOW)

    # 10:00 IST on 15 Nov is 20:30 on 14 Nov in LA, so the 14th is today and already learned.
    assert result.days[-1].date == date(2026, 11, 14)
    assert result.status is StreakStatus.ACTIVE


def test_tamper_detail_names_the_failed_check(videos):
    unpublished = make_watch("2026-11-08T20:08:20+05:30", 130, video_id="v_new",
                             received_at="2026-11-10T14:38:13+00:00")
    clock_ahead = make_watch("2026-11-07T20:10:00+05:30", 130, received_at="2026-11-07T14:30:00+00:00")

    result = compute_streak(make_user(), [unpublished, clock_ahead], videos, NO_OUTAGE, NOW)
    details = {row.date.day: row.detail for row in result.days}

    assert "published" in details[8]
    assert "ahead of server" in details[7]


def test_as_of_before_signup_on_the_same_day_returns_no_days(videos):
    user = make_user(signup_at="2026-11-13T23:50:00+05:30")

    result = compute_streak(user, [], videos, NO_OUTAGE, datetime.fromisoformat("2026-11-13T12:00:00+05:30"))

    assert result.days == []
