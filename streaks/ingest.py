"""Moving data in: seed files to S3, S3 to Postgres, and POSTed batches (archived first)."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from streaks.models import Event, EventType, ParseError
from streaks.parsing import compose_dataset, parse_event
from streaks.storage import Storage
from streaks.store import Store

INPUT_FILES = ("users.csv", "videos.csv", "events.csv", "affected_uids.csv")
_References = tuple[set[str], set[str]]  # (known user ids, known video ids)
_VIDEO_EVENT_TYPES = frozenset({EventType.VIDEO_START, EventType.VIDEO_END})


@dataclass(frozen=True)
class IngestReport:
    inserted: int
    duplicate: int
    invalid: int
    errors: list[ParseError] = field(default_factory=list)
    # Events sent without received_at got this server time; GETs with an earlier as_of won't see them.
    default_received_at: str | None = None


def seed_inputs(storage: Storage, data_dir: Path, affected_uids_path: Path) -> None:
    sources = {name: data_dir / name for name in INPUT_FILES} | {"affected_uids.csv": affected_uids_path}
    for name, path in sources.items():
        storage.put_input_file(name, path.read_bytes())


def load_inputs(store: Store, storage: Storage) -> None:
    files = {name: storage.get_input_file(name).decode() for name in INPUT_FILES}
    dataset = compose_dataset(files["users.csv"], files["videos.csv"], files["events.csv"], files["affected_uids.csv"])
    store.upsert_users(dataset.users.values())
    store.upsert_videos(dataset.videos.values())
    store.replace_affected_uids(dataset.outage.affected_uids)
    store.add_events(dataset.events)


def _check_references(event: Event, index: int, user_ids: set[str], video_ids: set[str]) -> Event | ParseError:
    if event.user_id not in user_ids:
        return ParseError(index=index, message=f"user_id: unknown {event.user_id!r}")
    if event.event_type in _VIDEO_EVENT_TYPES and event.video_id not in video_ids:
        return ParseError(index=index, message=f"video_id: unknown {event.video_id!r}")
    return event


def _get_references(store: Store) -> _References:
    return store.get_user_ids(), store.get_video_ids()


def _parse_batch(
    raw_body: bytes, references: _References, received_at_default: datetime
) -> list[Event | ParseError] | ParseError:
    try:
        items = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError):
        return ParseError(index=-1, message="body is not valid JSON")
    if not isinstance(items, list):
        return ParseError(index=-1, message="body must be a JSON list of events")
    user_ids, video_ids = references
    results = []
    for index, item in enumerate(items):
        parsed = parse_event(item, index, received_at_default)
        results.append(parsed if isinstance(parsed, ParseError) else _check_references(parsed, index, user_ids, video_ids))
    return results


def _add_parsed(results: list[Event | ParseError], store: Store, received_at_default: datetime) -> IngestReport:
    events = [result for result in results if isinstance(result, Event)]
    errors = [result for result in results if isinstance(result, ParseError)]
    inserted, duplicate = store.add_events(events)
    return IngestReport(
        inserted=inserted, duplicate=duplicate, invalid=len(errors), errors=errors,
        default_received_at=received_at_default.isoformat(),
    )


def ingest_posted_events(raw_body: bytes, store: Store, storage: Storage, now: datetime) -> IngestReport | ParseError:
    """Archive first, so even a body we reject is never lost."""
    storage.put_raw_post(raw_body, now)
    parsed = _parse_batch(raw_body, _get_references(store), now)
    return parsed if isinstance(parsed, ParseError) else _add_parsed(parsed, store, now)


def rebuild(store: Store, storage: Storage) -> None:
    """Recreate Postgres from S3 alone: the inputs, then every archived POST."""
    store.reset()
    load_inputs(store, storage)
    references = _get_references(store)
    for received_at, body in storage.get_raw_posts():
        parsed = _parse_batch(body, references, received_at)
        if not isinstance(parsed, ParseError):
            _add_parsed(parsed, store, received_at)
