"""Turn untrusted rows (CSV or JSON) into domain values. The only place that decodes input."""

import csv
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from streaks import rules
from streaks.models import Dataset, Event, EventType, Outage, ParseError, User, Video

_REQUIRED_EVENT_FIELDS = ("event_id", "user_id", "event_type", "client_ts", "device_tz")
_OPTIONAL_TEXT_FIELDS = ("video_id", "received_at", "app_version")
_EVENT_TYPES = {event_type.value for event_type in EventType}
# Sanity bounds: values outside them are corrupt input, and would overflow Postgres or date maths.
_MAX_WATCHED_S = 86_400
_EARLIEST_TIMESTAMP = datetime(2020, 1, 1, tzinfo=UTC)
_LATEST_TIMESTAMP = datetime(2100, 1, 1, tzinfo=UTC)


class _InvalidField(ValueError):
    """Internal signal while decoding one event; surfaced to callers as a ParseError value."""


def parse_meta(raw: str | dict | None) -> dict[str, str]:
    if raw is not None and not isinstance(raw, (str, dict)):
        raise _InvalidField("meta: must be a 'k=v;k=v' string or a JSON object")
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    if not raw:
        return {}
    pairs = (part.split("=", 1) for part in raw.split(";") if "=" in part)
    return {key.strip(): value.strip() for key, value in pairs}


def parse_timestamp(raw: str, field_name: str) -> datetime:
    """Parse an ISO-8601 timestamp that must carry an offset."""
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError) as error:
        raise _InvalidField(f"{field_name}: not an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise _InvalidField(f"{field_name}: timestamp has no timezone offset")
    if not _EARLIEST_TIMESTAMP <= parsed < _LATEST_TIMESTAMP:
        raise _InvalidField(f"{field_name}: outside {_EARLIEST_TIMESTAMP.year}–{_LATEST_TIMESTAMP.year}")
    return parsed


def _parse_optional_int(raw: str | int | None, field_name: str) -> int | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        raise _InvalidField(f"{field_name}: not an integer")
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise _InvalidField(f"{field_name}: not an integer") from error
    if not 0 <= value <= _MAX_WATCHED_S:
        raise _InvalidField(f"{field_name}: must be between 0 and {_MAX_WATCHED_S}")
    return value


def _check_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise _InvalidField(f"device_tz: unknown timezone {name!r}") from error
    return name


def _check_text_fields(raw: dict) -> None:
    for name in _REQUIRED_EVENT_FIELDS + _OPTIONAL_TEXT_FIELDS:
        value = raw.get(name)
        if value is not None and not isinstance(value, str):
            raise _InvalidField(f"{name}: must be a string")
        if isinstance(value, str) and "\x00" in value:
            raise _InvalidField(f"{name}: contains a NUL character")


def _decode_event(raw: dict, received_at_default: datetime | None) -> Event:
    missing = [name for name in _REQUIRED_EVENT_FIELDS if not raw.get(name)]
    if missing:
        raise _InvalidField(f"missing fields: {', '.join(missing)}")
    _check_text_fields(raw)
    if raw["event_type"] not in _EVENT_TYPES:
        raise _InvalidField(f"event_type: unknown {raw['event_type']!r}")

    raw_received_at = raw.get("received_at")
    if raw_received_at:
        received_at = parse_timestamp(raw_received_at, "received_at")
    elif received_at_default is not None:
        received_at = received_at_default
    else:
        raise _InvalidField("missing fields: received_at")

    return Event(
        event_id=raw["event_id"],
        user_id=raw["user_id"],
        event_type=raw["event_type"],
        video_id=raw.get("video_id") or None,
        watched_s=_parse_optional_int(raw.get("watched_s"), "watched_s"),
        client_ts=parse_timestamp(raw["client_ts"], "client_ts"),
        device_tz=_check_timezone(raw["device_tz"]),
        received_at=received_at,
        app_version=raw.get("app_version") or "",
        meta=parse_meta(raw.get("meta")),
    )


def parse_event(
    raw: dict, index: int, received_at_default: datetime | None = None
) -> Event | ParseError:
    if not isinstance(raw, dict):
        return ParseError(index=index, message="event must be a JSON object")
    try:
        return _decode_event(raw, received_at_default)
    except _InvalidField as error:
        return ParseError(index=index, message=str(error))


def parse_user_row(row: dict) -> User:
    return User(
        user_id=row["user_id"],
        name=row["name"],
        signup_at=datetime.fromisoformat(row["signup_at"]),
        home_tz=row["home_tz"],
        plan=row["plan"],
        freeze_balance=int(row["freeze_balance"]),
        streak_carry_in=int(row["streak_as_of_2026_10_31"]),
    )


def parse_video_row(row: dict) -> Video:
    return Video(
        video_id=row["video_id"],
        duration_s=int(row["duration_s"]),
        published_at=datetime.fromisoformat(row["published_at"]),
    )


def parse_events_csv(text: str) -> list[Event]:
    """Parse the trusted seed file. A bad row there is a data bug, so fail loudly."""
    events = []
    for index, row in enumerate(csv.DictReader(text.splitlines())):
        result = parse_event(row, index)
        if isinstance(result, ParseError):
            raise ValueError(f"events.csv row {index}: {result.message}")
        events.append(result)
    return events


def parse_users_csv(text: str) -> dict[str, User]:
    users = (parse_user_row(row) for row in csv.DictReader(text.splitlines()))
    return {user.user_id: user for user in users}


def parse_videos_csv(text: str) -> dict[str, Video]:
    videos = (parse_video_row(row) for row in csv.DictReader(text.splitlines()))
    return {video.video_id: video for video in videos}


def parse_affected_uids_csv(text: str) -> frozenset[str]:
    return frozenset(row["user_id"] for row in csv.DictReader(text.splitlines()))


def compose_outage(affected_uids: frozenset[str]) -> Outage:
    return Outage(start=rules.OUTAGE_START, end=rules.OUTAGE_END, affected_uids=affected_uids)


def compose_dataset(
    users_csv: str, videos_csv: str, events_csv: str, affected_uids_csv: str
) -> Dataset:
    return Dataset(
        users=parse_users_csv(users_csv),
        videos=parse_videos_csv(videos_csv),
        events=parse_events_csv(events_csv),
        outage=compose_outage(parse_affected_uids_csv(affected_uids_csv)),
    )


def load_dataset(data_dir: Path, affected_uids_path: Path) -> Dataset:
    return compose_dataset(
        users_csv=(data_dir / "users.csv").read_text(),
        videos_csv=(data_dir / "videos.csv").read_text(),
        events_csv=(data_dir / "events.csv").read_text(),
        affected_uids_csv=affected_uids_path.read_text(),
    )


def parse_timestamp_value(raw: str, field_name: str) -> datetime | ParseError:
    """Value-returning variant for HTTP query parameters."""
    try:
        return parse_timestamp(raw, field_name)
    except _InvalidField as error:
        return ParseError(index=-1, message=str(error))


def parse_date_value(raw: str, field_name: str) -> date | ParseError:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return ParseError(index=-1, message=f"{field_name}: expected YYYY-MM-DD")
