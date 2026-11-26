"""HTTP edge. Thin: parse input, call ingest/engine, return values. No rules here."""

from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, date, datetime

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from streaks.engine import compute_streak
from streaks.ingest import ingest_posted_events
from streaks.models import ParseError, StreakResult, User
from streaks.parsing import parse_date_value, parse_timestamp_value
from streaks.report import (
    ListFilter,
    compose_streak_summary,
    compose_support_rows,
    compose_user_action,
    compose_user_listings,
    filter_listings,
)
from streaks.storage import Storage
from streaks.store import Store
from streaks.support_view import render_support_index, render_support_page


_EVENTS_REQUEST_BODY = {
    "required": True,
    "content": {
        "application/json": {
            "schema": {"type": "array", "items": {"type": "object"}},
            "example": [
                {
                    "event_id": "e_demo_1", "user_id": "u09", "event_type": "video_end", "video_id": "v004",
                    "watched_s": 95, "client_ts": "2026-11-15T20:00:00+05:30", "device_tz": "Asia/Kolkata",
                    "received_at": "2026-11-15T14:31:00Z", "app_version": "3.2.1", "meta": "",
                }
            ],
        }
    },
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_as_of(raw: str | None, default_as_of: datetime) -> datetime:
    if raw is None:
        return default_as_of
    parsed = parse_timestamp_value(raw, "as_of")
    if isinstance(parsed, ParseError):
        raise HTTPException(status_code=422, detail=parsed.message)
    return parsed


def _parse_date(raw: str | None, field_name: str) -> date | None:
    if raw is None:
        return None
    parsed = parse_date_value(raw, field_name)
    if isinstance(parsed, ParseError):
        raise HTTPException(status_code=422, detail=parsed.message)
    return parsed


def create_app(
    store: Store, storage: Storage, default_as_of: datetime, clock: Callable[[], datetime] = _utc_now
) -> FastAPI:
    app = FastAPI(title="Jumpp streaks-v2")

    def get_user_or_404(user_id: str) -> User:
        user = store.get_user(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail=f"unknown user {user_id!r}")
        return user

    def compute_for(user: User, raw_as_of: str | None) -> StreakResult:
        as_of = _parse_as_of(raw_as_of, default_as_of)
        return compute_streak(user, store.get_user_events(user.user_id), store.get_videos(), store.get_outage(), as_of)

    @app.get("/", include_in_schema=False)
    def get_root():
        return RedirectResponse("/support")

    @app.post("/events", openapi_extra={"requestBody": _EVENTS_REQUEST_BODY})
    async def post_events(request: Request):
        result = ingest_posted_events(await request.body(), store, storage, clock())
        if isinstance(result, ParseError):
            return JSONResponse(status_code=422, content={"detail": result.message})
        return asdict(result)

    @app.get("/users")
    def get_users(as_of: str | None = None):
        listings = compose_user_listings(store.get_dataset(), _parse_as_of(as_of, default_as_of))
        return [
            {
                **compose_streak_summary(listing.result),
                "name": listing.user.name,
                "plan": listing.user.plan,
                "action_kind": listing.action.kind.value if listing.action else None,
                "action": listing.action.text if listing.action else None,
            }
            for listing in listings
        ]

    @app.get("/support", response_class=HTMLResponse)
    def get_support_index(as_of: str | None = None, filter: str = "all", q: str = ""):
        effective_as_of = _parse_as_of(as_of, default_as_of)
        try:
            list_filter = ListFilter(filter)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"filter: one of {[item.value for item in ListFilter]}") from None
        listings = filter_listings(compose_user_listings(store.get_dataset(), effective_as_of), list_filter, q)
        return render_support_index(listings, list_filter, q, as_of, effective_as_of.isoformat())

    @app.get("/users/{user_id}/streak")
    def get_streak(user_id: str, as_of: str | None = None):
        result = compute_for(get_user_or_404(user_id), as_of)
        return {**compose_streak_summary(result), "as_of": result.as_of.isoformat()}

    @app.get("/users/{user_id}/days")
    def get_days(
        user_id: str,
        from_date: str | None = Query(None, alias="from"),
        to_date: str | None = Query(None, alias="to"),
        as_of: str | None = None,
    ):
        result = compute_for(get_user_or_404(user_id), as_of)
        start, end = _parse_date(from_date, "from"), _parse_date(to_date, "to")
        return [
            asdict(day)
            for day in result.days
            if (start is None or day.date >= start) and (end is None or day.date <= end)
        ]

    @app.get("/support/{user_id}", response_class=HTMLResponse)
    def get_support_page(user_id: str, as_of: str | None = None):
        user = get_user_or_404(user_id)
        result = compute_for(user, as_of)
        user_ids = sorted(store.get_user_ids())
        position = user_ids.index(user_id)
        neighbours = (
            user_ids[position - 1] if position > 0 else None,
            user_ids[position + 1] if position + 1 < len(user_ids) else None,
        )
        return render_support_page(
            user, result, compose_support_rows(result), compose_user_action(result), neighbours, as_of
        )

    return app

