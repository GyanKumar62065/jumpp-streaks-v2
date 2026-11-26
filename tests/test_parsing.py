from datetime import datetime, timezone
from pathlib import Path

import pytest

from streaks.models import Event, ParseError
from streaks.parsing import load_dataset, parse_event, parse_meta

ROOT = Path(__file__).resolve().parent.parent


def _raw_event(**overrides) -> dict:
    raw = {
        "event_id": "e_1",
        "user_id": "u01",
        "event_type": "video_end",
        "video_id": "v001",
        "watched_s": "140",
        "client_ts": "2026-11-03T08:17:00+05:30",
        "device_tz": "Asia/Kolkata",
        "received_at": "2026-11-03T02:47:01Z",
        "app_version": "3.2.0",
        "meta": "",
    }
    raw.update(overrides)
    return raw


def test_parse_meta_splits_pairs():
    assert parse_meta("for_date=2026-11-07;source=server") == {
        "for_date": "2026-11-07",
        "source": "server",
    }
    assert parse_meta("") == {}


def test_parse_event_rejects_naive_timestamp():
    result = parse_event(_raw_event(client_ts="2026-11-15T10:00:00"), index=4)

    assert isinstance(result, ParseError)
    assert result.index == 4
    assert "client_ts" in result.message


def test_parse_event_uses_default_received_at_when_missing():
    now = datetime(2026, 11, 15, 4, 30, tzinfo=timezone.utc)

    result = parse_event(_raw_event(received_at=None), index=0, received_at_default=now)

    assert isinstance(result, Event)
    assert result.received_at == now
    assert result.watched_s == 140


def test_load_dataset_reads_all_inputs():
    dataset = load_dataset(ROOT / "data", ROOT / "config" / "affected_uids.csv")

    assert len(dataset.users) == 15
    assert len(dataset.videos) == 40
    assert len(dataset.events) == 809
    assert "u08" in dataset.outage.affected_uids
    assert dataset.users["u15"].streak_carry_in == 17


@pytest.mark.parametrize(
    "overrides",
    [
        {"device_tz": 5},
        {"event_type": ["video_end"]},
        {"meta": [1, 2]},
        {"user_id": {"id": 1}},
        {"watched_s": 10**12},
        {"watched_s": -5},
        {"client_ts": "9999-12-31T23:59:59+00:00"},
        {"client_ts": "0001-01-01T00:00:30+00:00"},
        {"received_at": 12345},
        {"event_id": "e_\x00bad"},
    ],
    ids=["tz_int", "type_list", "meta_list", "user_dict", "watched_huge", "watched_negative",
         "client_far_future", "client_year_1", "received_int", "nul_char"],
)
def test_parse_event_returns_error_for_malformed_values(overrides):
    result = parse_event(_raw_event(**overrides), index=7)

    assert isinstance(result, ParseError)
    assert result.index == 7
