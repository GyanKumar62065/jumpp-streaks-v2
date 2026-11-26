import random
from datetime import date

from streaks.models import WatchVerdict
from streaks.watches import compose_watches, dedupe_events
from tests.conftest import make_event, make_watch


def test_duplicate_and_resent_events_count_once():
    original = make_watch("2026-11-10T14:07:53+05:30", 165, event_id="e_a",
                          received_at="2026-11-11T04:10:00+00:00")
    same_id = make_watch("2026-11-10T14:07:53+05:30", 165, event_id="e_a",
                         received_at="2026-11-11T04:10:00+00:00")
    resent_new_id = make_watch("2026-11-10T14:07:53+05:30", 165, event_id="e_b",
                               received_at="2026-11-11T04:10:40+00:00")

    kept = dedupe_events([resent_new_id, same_id, original])

    assert [event.event_id for event in kept] == ["e_a"]


def test_dedupe_is_order_independent():
    events = [make_watch(f"2026-11-0{day}T10:00:00+05:30", 60) for day in range(1, 8)]
    events += [make_watch("2026-11-03T10:00:00+05:30", 60, received_at="2026-11-04T00:00:00+00:00")]
    expected = dedupe_events(events)
    shuffled = list(events)
    random.Random(1).shuffle(shuffled)

    assert dedupe_events(list(reversed(events))) == expected
    assert dedupe_events(shuffled) == expected


def test_watch_is_assigned_to_start_day_across_midnight(videos):
    watch, = compose_watches([make_watch("2026-11-10T00:00:27+05:30", 80, video_id="v_82")], videos)

    assert watch.day == date(2026, 11, 9)
    assert watch.is_complete is True


def test_watch_before_publish_is_rejected_as_tamper(videos):
    watch, = compose_watches([make_watch("2026-11-08T20:08:20+05:30", 130, video_id="v_new",
                                         received_at="2026-11-10T14:38:13+00:00")], videos)

    assert watch.verdict is WatchVerdict.TAMPER_UNPUBLISHED


def test_clock_ahead_of_server_is_tamper(videos):
    watch, = compose_watches([make_watch("2026-11-08T20:10:00+05:30", 130,
                                         received_at="2026-11-08T14:30:00+00:00")], videos)

    assert watch.verdict is WatchVerdict.TAMPER_CLOCK_AHEAD


def test_late_sync_beyond_cap_is_rejected(videos):
    watch, = compose_watches([make_watch("2026-11-01T10:00:00+05:30", 130,
                                         received_at="2026-11-08T05:30:00+00:00")], videos)

    assert watch.verdict is WatchVerdict.TOO_LATE


def test_late_sync_within_cap_is_late(videos):
    watch, = compose_watches([make_watch("2026-11-01T10:00:00+05:30", 130,
                                         received_at="2026-11-02T17:30:00+00:00")], videos)

    assert watch.verdict is WatchVerdict.LATE


def test_watched_seconds_are_capped_at_duration(videos):
    watch, = compose_watches([make_watch("2026-11-01T10:00:00+05:30", 500, video_id="v_104")], videos)

    assert watch.counted_s == 104


def test_video_start_without_end_is_not_a_watch(videos):
    start = make_event("video_start", "2026-11-11T12:00:05+05:30", video_id="v_104")

    assert compose_watches([start], videos) == []


def test_oversized_watched_seconds_do_not_move_the_watch_day(videos):
    watch, = compose_watches([make_watch("2026-11-14T00:05:00+05:30", 600, video_id="v_104")], videos)

    assert watch.day == date(2026, 11, 14)  # 00:05 minus the capped 104s; raw 600s would give the 13th
    watch, = compose_watches([make_watch("2026-11-14T00:05:00+05:30", 6000, video_id="v_104")], videos)
    assert watch.day == date(2026, 11, 14)
    assert watch.started_at.isoformat() == "2026-11-14T00:03:16+05:30"
