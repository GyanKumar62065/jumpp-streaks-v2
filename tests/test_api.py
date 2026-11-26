from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from streaks.api import create_app
from streaks.ingest import load_inputs, seed_inputs

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AS_OF = datetime.fromisoformat("2026-11-15T10:00:00+05:30")


def _event(**overrides) -> dict:
    event = {"event_id": "e_post_1", "user_id": "u08", "event_type": "video_end", "video_id": "v004",
             "watched_s": 95, "client_ts": "2026-11-15T09:00:00+05:30", "device_tz": "Asia/Kolkata",
             "received_at": "2026-11-15T03:31:00Z", "app_version": "3.2.1", "meta": ""}
    event.update(overrides)
    return event


@pytest.fixture
def client(store, storage):
    seed_inputs(storage, ROOT / "data", ROOT / "config" / "affected_uids.csv")
    load_inputs(store, storage)
    app = create_app(store, storage, DEFAULT_AS_OF, clock=lambda: datetime(2026, 11, 15, 4, 30, tzinfo=timezone.utc))
    return TestClient(app)


def test_post_same_batch_twice_reports_duplicates(client):
    batch = [_event(), _event(event_id="e_post_2", event_type="app_open", video_id=None, watched_s=None)]

    first = client.post("/events", json=batch).json()
    second = client.post("/events", json=batch).json()

    assert (first["inserted"], first["duplicate"]) == (2, 0)
    assert (second["inserted"], second["duplicate"]) == (0, 2)


def test_post_with_bad_items_keeps_good_ones(client):
    batch = [_event(), _event(event_id="e_b1", client_ts="2026-11-15 09:00"),
             _event(event_id="e_b2", user_id="nope"), _event(event_id="e_b3", video_id="v999")]

    report = client.post("/events", json=batch).json()

    assert (report["inserted"], report["invalid"]) == (1, 3)
    assert [error["index"] for error in report["errors"]] == [1, 2, 3]


def test_post_non_list_body_is_422(client):
    assert client.post("/events", json={"event_id": "x"}).status_code == 422


def test_get_streak_for_u08(client):
    body = client.get("/users/u08/streak").json()

    assert body["current_streak"] == 313
    assert body["status"] == "AT_RISK"
    assert body["as_of"].startswith("2026-11-15T10:00:00")


def test_days_filter_returns_inclusive_range(client):
    rows = client.get("/users/u08/days", params={"from": "2026-11-08", "to": "2026-11-10"}).json()

    assert [row["date"] for row in rows] == ["2026-11-08", "2026-11-09", "2026-11-10"]
    assert rows[1]["code"] == "PROTECTED_OUTAGE"


def test_posting_today_lesson_makes_user_active(client):
    client.post("/events", json=[_event()])

    body = client.get("/users/u08/streak", params={"as_of": "2026-11-15T10:00:00+05:30"}).json()

    assert (body["status"], body["current_streak"]) == ("ACTIVE", 314)


def test_unknown_user_is_404(client):
    assert client.get("/users/nope/streak").status_code == 404
    assert client.get("/support/nope").status_code == 404


def test_naive_as_of_is_422(client):
    assert client.get("/users/u08/streak", params={"as_of": "2026-11-15T10:00:00"}).status_code == 422


def test_support_page_shows_refund_for_u07(client):
    response = client.get("/support/u07")

    assert response.headers["content-type"].startswith("text/html")
    assert "Refund ₹49" in response.text
    assert "LEARNED_LATE_SYNC" in response.text


def test_post_reports_the_received_at_it_used(client):
    report = client.post("/events", json=[_event(received_at=None)]).json()

    assert report["inserted"] == 1
    assert report["default_received_at"] == "2026-11-15T04:30:00+00:00"


# --- Support console --------------------------------------------------------------


def test_list_users_returns_everyone_with_status_and_action(client):
    users = client.get("/users").json()

    assert len(users) == 15
    u07 = next(user for user in users if user["user_id"] == "u07")
    assert (u07["name"], u07["current_streak"], u07["action_kind"]) == ("Sneha P", 72, "REFUND")


def test_support_index_links_every_user(client):
    page = client.get("/support").text

    assert all(f'href="/support/u{n:02d}"' in page for n in range(1, 16))


def test_support_index_filters_users_who_need_action(client):
    page = client.get("/support", params={"filter": "action"}).text

    assert 'href="/support/u07"' in page and 'href="/support/u06"' in page
    assert 'href="/support/u05"' not in page


def test_support_index_search_by_name(client):
    page = client.get("/support", params={"q": "sneha"}).text

    assert 'href="/support/u07"' in page
    assert 'href="/support/u08"' not in page


def test_support_user_page_links_neighbours_and_keeps_as_of(client):
    as_of = "2026-11-15T21:00:00+05:30"
    page = client.get("/support/u07", params={"as_of": as_of}).text

    assert 'href="/support/u06?as_of=2026-11-15T21%3A00%3A00%2B05%3A30"' in page
    assert 'href="/support/u08?as_of=2026-11-15T21%3A00%3A00%2B05%3A30"' in page


def test_root_redirects_to_support(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/support"


def test_post_events_documents_its_request_body(client):
    schema = client.get("/openapi.json").json()

    assert "requestBody" in schema["paths"]["/events"]["post"]


def test_support_index_counts_users_in_plain_english(client):
    assert "1 user shown." in client.get("/support", params={"q": "ishaan"}).text
    assert "15 users shown." in client.get("/support").text
