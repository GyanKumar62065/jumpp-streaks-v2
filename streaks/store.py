"""Postgres adapter. The only module that runs SQL; rows leave it as domain values."""

from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from streaks.models import Dataset, Event, Outage, User, Video
from streaks.parsing import compose_outage, parse_meta

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"

_INSERT_EVENT = """
    INSERT INTO events (event_id, user_id, event_type, video_id, watched_s, client_ts,
                        device_tz, received_at, app_version, meta)
    VALUES (%(event_id)s, %(user_id)s, %(event_type)s, %(video_id)s, %(watched_s)s, %(client_ts)s,
            %(device_tz)s, %(received_at)s, %(app_version)s, %(meta)s)
    ON CONFLICT (event_id) DO NOTHING
"""
_UPSERT_USER = """
    INSERT INTO users (user_id, name, signup_at, home_tz, plan, freeze_balance, streak_as_of_2026_10_31)
    VALUES (%(user_id)s, %(name)s, %(signup_at)s, %(home_tz)s, %(plan)s, %(freeze_balance)s,
            %(streak_carry_in)s)
    ON CONFLICT (user_id) DO UPDATE SET
        name = EXCLUDED.name, signup_at = EXCLUDED.signup_at, home_tz = EXCLUDED.home_tz,
        plan = EXCLUDED.plan, freeze_balance = EXCLUDED.freeze_balance,
        streak_as_of_2026_10_31 = EXCLUDED.streak_as_of_2026_10_31
"""
_UPSERT_VIDEO = """
    INSERT INTO videos (video_id, duration_s, published_at)
    VALUES (%(video_id)s, %(duration_s)s, %(published_at)s)
    ON CONFLICT (video_id) DO UPDATE SET
        duration_s = EXCLUDED.duration_s, published_at = EXCLUDED.published_at
"""


def _to_user(row: dict) -> User:
    return User(
        user_id=row["user_id"], name=row["name"], signup_at=row["signup_at"], home_tz=row["home_tz"],
        plan=row["plan"], freeze_balance=row["freeze_balance"],
        streak_carry_in=row["streak_as_of_2026_10_31"],
    )


def _to_event(row: dict) -> Event:
    return Event(**{**row, "meta": parse_meta(row["meta"])})


def _event_params(event: Event) -> dict:
    return {**asdict(event), "meta": Jsonb(event.meta)}


class Store:
    def __init__(self, connection: psycopg.Connection):
        self._connection = connection

    def close(self) -> None:
        self._connection.close()

    def apply_schema(self) -> None:
        self._connection.execute(_SCHEMA_PATH.read_text())

    def reset(self) -> None:
        self._connection.execute("TRUNCATE events, users, videos, affected_uids")

    def upsert_users(self, users: Iterable[User]) -> None:
        with self._connection.cursor() as cursor:
            cursor.executemany(_UPSERT_USER, [asdict(user) for user in users])

    def upsert_videos(self, videos: Iterable[Video]) -> None:
        with self._connection.cursor() as cursor:
            cursor.executemany(_UPSERT_VIDEO, [asdict(video) for video in videos])

    def replace_affected_uids(self, uids: frozenset[str]) -> None:
        with self._connection.transaction(), self._connection.cursor() as cursor:
            cursor.execute("DELETE FROM affected_uids")
            cursor.executemany("INSERT INTO affected_uids (user_id) VALUES (%s)", [(uid,) for uid in sorted(uids)])

    def add_events(self, events: list[Event]) -> tuple[int, int]:
        """Returns (inserted, duplicate). Idempotent on event_id."""
        if not events:
            return 0, 0
        with self._connection.transaction(), self._connection.cursor() as cursor:
            cursor.executemany(_INSERT_EVENT, [_event_params(event) for event in events])
            inserted = cursor.rowcount  # psycopg 3 sums rowcount across executemany
        return inserted, len(events) - inserted

    def get_user(self, user_id: str) -> User | None:
        row = self._connection.execute("SELECT * FROM users WHERE user_id = %s", (user_id,)).fetchone()
        return _to_user(row) if row else None

    def get_users(self) -> dict[str, User]:
        rows = self._connection.execute("SELECT * FROM users ORDER BY user_id").fetchall()
        return {row["user_id"]: _to_user(row) for row in rows}

    def get_user_ids(self) -> set[str]:
        return {row["user_id"] for row in self._connection.execute("SELECT user_id FROM users")}

    def get_video_ids(self) -> set[str]:
        return {row["video_id"] for row in self._connection.execute("SELECT video_id FROM videos")}

    def count_events(self) -> int:
        return self._connection.execute("SELECT count(*) AS n FROM events").fetchone()["n"]

    def get_videos(self) -> dict[str, Video]:
        rows = self._connection.execute("SELECT * FROM videos").fetchall()
        return {row["video_id"]: Video(**row) for row in rows}

    def get_outage(self) -> Outage:
        rows = self._connection.execute("SELECT user_id FROM affected_uids").fetchall()
        return compose_outage(frozenset(row["user_id"] for row in rows))

    def get_user_events(self, user_id: str) -> list[Event]:
        rows = self._connection.execute("SELECT * FROM events WHERE user_id = %s", (user_id,)).fetchall()
        return [_to_event(row) for row in rows]

    def get_dataset(self) -> Dataset:
        rows = self._connection.execute("SELECT * FROM events").fetchall()
        return Dataset(
            users=self.get_users(), videos=self.get_videos(),
            events=[_to_event(row) for row in rows], outage=self.get_outage(),
        )


def open_store(database_url: str) -> Store:
    return Store(psycopg.connect(database_url, autocommit=True, row_factory=dict_row))
