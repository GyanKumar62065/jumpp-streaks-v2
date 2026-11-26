import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from streaks.ingest import ingest_posted_events, load_inputs, rebuild, seed_inputs

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 11, 15, 4, 30, tzinfo=timezone.utc)


@pytest.fixture
def seeded(store, storage):
    seed_inputs(storage, ROOT / "data", ROOT / "config" / "affected_uids.csv")
    load_inputs(store, storage)
    return store, storage


def test_seed_loads_all_events(seeded):
    store, _ = seeded

    assert len(store.get_dataset().events) == 806  # 809 rows minus 3 repeated event_ids
    assert "u08" in store.get_outage().affected_uids


def test_rebuild_restores_posted_events(seeded):
    store, storage = seeded
    body = json.dumps([{"event_id": "e_new", "user_id": "u08", "event_type": "app_open",
                        "client_ts": "2026-11-15T09:00:00+05:30", "device_tz": "Asia/Kolkata",
                        "app_version": "3.2.1", "meta": "queue_depth=0"}]).encode()
    ingest_posted_events(body, store, storage, NOW)

    rebuild(store, storage)

    restored = [event for event in store.get_user_events("u08") if event.event_id == "e_new"]
    assert len(restored) == 1
    assert restored[0].received_at == NOW
