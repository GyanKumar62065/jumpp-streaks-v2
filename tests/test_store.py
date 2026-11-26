import pytest

from tests.conftest import make_event, make_user

pytestmark = pytest.mark.integration


def test_add_events_is_idempotent(store):
    events = [make_event("app_open", f"2026-11-0{day}T09:00:00+05:30") for day in (1, 2, 3)]

    assert store.add_events(events) == (3, 0)
    assert store.add_events(events) == (0, 3)


def test_round_trip_keeps_tz_and_meta(store):
    store.upsert_users([make_user()])
    store.add_events([make_event("app_open", "2026-11-13T21:02:00+05:30", meta={"queue_depth": "3"})])

    event, = store.get_user_events("u_test")

    assert event.client_ts.tzinfo is not None
    assert event.meta == {"queue_depth": "3"}
    assert store.get_user("u_test").home_tz == "Asia/Kolkata"
    assert store.get_user("nope") is None
