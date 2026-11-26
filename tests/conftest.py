"""Small builders so tests state only what matters to them."""

from datetime import datetime, timedelta
from itertools import count

import pytest

from streaks.models import Event, Outage, User, Video
from streaks import rules

IST = "Asia/Kolkata"
_ids = count()


def make_user(user_id="u_test", *, signup_at="2026-10-01T09:00:00+05:30", home_tz=IST,
              plan="free", freeze_balance=0, streak_carry_in=0) -> User:
    return User(user_id=user_id, name="Test", signup_at=datetime.fromisoformat(signup_at),
                home_tz=home_tz, plan=plan, freeze_balance=freeze_balance,
                streak_carry_in=streak_carry_in)


def make_event(event_type, client_ts, *, user_id="u_test", video_id=None, watched_s=None,
               device_tz=IST, received_at=None, meta=None, event_id=None) -> Event:
    client = datetime.fromisoformat(client_ts)
    received = datetime.fromisoformat(received_at) if received_at else client + timedelta(seconds=1)
    return Event(event_id=event_id or f"e_{next(_ids)}", user_id=user_id, event_type=event_type,
                 video_id=video_id, watched_s=watched_s, client_ts=client, device_tz=device_tz,
                 received_at=received, app_version="3.2.0", meta=meta or {})


def make_watch(client_end_ts, watched_s, *, video_id="v_long", **kwargs) -> Event:
    return make_event("video_end", client_end_ts, video_id=video_id, watched_s=watched_s, **kwargs)


def make_video(video_id, duration_s, published_at="2026-10-01T06:00:00+05:30") -> Video:
    return Video(video_id=video_id, duration_s=duration_s,
                 published_at=datetime.fromisoformat(published_at))


@pytest.fixture
def videos():
    return {
        "v_long": make_video("v_long", 600),
        "v_104": make_video("v_104", 104),
        "v_82": make_video("v_82", 82),
        "v_new": make_video("v_new", 140, published_at="2026-11-10T06:00:00+05:30"),
    }


def make_outage(*affected) -> Outage:
    return Outage(start=rules.OUTAGE_START, end=rules.OUTAGE_END, affected_uids=frozenset(affected))


def make_learned_days(days, *, tz=IST, offset="+05:30", watched_s=130, **kwargs) -> list[Event]:
    """One qualifying 130s watch at 10:00 local on each November day given."""
    return [make_watch(f"2026-11-{day:02d}T10:00:00{offset}", watched_s, device_tz=tz, **kwargs)
            for day in days]


_TEST_DATABASE = "streaks_test"


def _ensure_test_database(database_url: str) -> str:
    """Tests truncate tables, so they never touch the app's own database."""
    import psycopg

    with psycopg.connect(database_url, autocommit=True) as connection:
        exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (_TEST_DATABASE,)).fetchone()
        if not exists:
            connection.execute(f"CREATE DATABASE {_TEST_DATABASE}")
    return database_url.rsplit("/", 1)[0] + f"/{_TEST_DATABASE}"


@pytest.fixture
def store():
    """A clean Postgres store (integration tests only)."""
    import os

    from streaks.store import open_store

    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    store = open_store(_ensure_test_database(os.environ["DATABASE_URL"]))
    store.apply_schema()
    store.reset()
    yield store
    store.reset()
    store.close()


@pytest.fixture
def storage():
    """A fresh S3 bucket on Floci per test (integration tests only)."""
    import os
    import uuid

    from streaks.storage import open_storage

    if not os.environ.get("S3_ENDPOINT_URL"):
        pytest.skip("S3_ENDPOINT_URL not set")
    storage = open_storage(os.environ["S3_ENDPOINT_URL"], f"test-{uuid.uuid4().hex[:12]}")
    storage.ensure_bucket()
    return storage
