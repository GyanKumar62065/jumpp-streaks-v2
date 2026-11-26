# Jumpp streaks-v2

The take-home brief is in `brief/ASSIGNMENT.md`. The rules are explained in `DECISIONS.md`, with full detail in `docs/superpowers/specs/2026-11-26-streaks-v2-design.md`.

## Run it (under 2 minutes)

Needs Docker only.

```bash
make up        # = docker compose up --build -d
               # floci (S3) + postgres + seed (S3 → Postgres) + api on :8000
make test      # all tests (unit + integration) inside Docker
make csv       # regenerate streaks_as_of_2026-11-15T1000IST.csv
make rebuild   # empty Postgres, replay everything from S3
make down
```

Without `make`, run the `docker compose …` lines from the `Makefile`.

## Support console and demo

- **<http://localhost:8000/support>** lists all users. Each row shows a strip of the last days, a filter (Everyone, Needs action, Broken streaks, Pending days) and a search box.
- **`/support/{id}`** is one user's page: the streak, a "Do this" banner, the day strip, the days that matter, and every day. It has previous/next links and an `as_of` picker.
- `GET /users` returns the same list as JSON.
- The full API is at <http://localhost:8000/docs>. `POST /events` can be tried from there.
- **Real-user journey in Chrome:** `docs/demo/support-journey-chrome.mp4` (33s). There's also a `.gif` version.
  - Clicked through by Claude in Chrome, screenshot by screenshot.
  - Needs action → u07 refund → time picker at the freeze sale → u06 tampering → u08 outage → search for u15 travel.
- **Demo video:** `docs/demo/streaks-v2-demo.mp4` (1m44s, silent, captioned).
  - Recorded by Claude Code with browser automation against the running stack.
  - It is **not** the candidate recording the brief asks for.

## Notes for graders (replaying events)

- `POST /events` takes a JSON list of events with the same fields as `events.csv`.
  - **Your `received_at` is used as given.** If an event has none, the server clock fills it in.
  - The response's `default_received_at` shows the time used.
  - Such events are invisible to a GET whose `as_of` is earlier, including the fixed default of 15 Nov. Send `received_at`, or pass a later `as_of`.
  - `meta` may be `"k=v;k=v"` or a JSON object.
- A partly bad batch still returns 200: `{inserted, duplicate, invalid, errors:[{index, message}]}`. Only a body that isn't a JSON list gets a 422.
- Posting the same batch twice is safe. Arrival order never changes a result.
- **"Now" is fixed** with `STREAKS_DEFAULT_AS_OF=2026-11-15T10:00:00+05:30` in `docker-compose.yml`.
  - Any GET can override it with `?as_of=<ISO with offset>`.
  - `as_of` means "what we knew then": events with `received_at` after it are ignored.
- Every POST body is archived to S3 (Floci) before it's inserted. `make rebuild` restores Postgres from S3 alone.

```bash
curl -s -X POST localhost:8000/events -H 'content-type: application/json' -d '[{
  "event_id":"e_demo_1","user_id":"u08","event_type":"video_end","video_id":"v004","watched_s":95,
  "client_ts":"2026-11-15T09:00:00+05:30","device_tz":"Asia/Kolkata",
  "received_at":"2026-11-15T03:31:00Z","app_version":"3.2.1","meta":""}]'
curl -s 'localhost:8000/users/u08/streak?as_of=2026-11-15T10:00:00%2B05:30'
curl -s 'localhost:8000/users/u08/days?from=2026-11-08&to=2026-11-10'
open  'http://localhost:8000/support/u07'          # support view (plain HTML)
```

## Where things are

| What | Where |
|---|---|
| Every rule value (120s, 90%, 7-day cap, 48h pending…) | `streaks/rules.py` |
| **A lesson gets assigned to a calendar day** | `streaks/watches.py` → `_compose_watch` (`day=` uses the watch's start time in `device_tz`) |
| **Duplicate handling** | `streaks/watches.py` → `dedupe_events` (engine); `sql/schema.sql` PK on `event_id` (DB) |
| Trusting a client clock (tamper, too late, late) | `streaks/watches.py` → `_judge_watch` |
| Day codes, freezes, streak, status | `streaks/engine.py` → `compute_streak` |
| Local days and timezone travel | `streaks/timeline.py` → `get_day_spans` |
| CSV rows, support actions, list filters | `streaks/report.py` |
| Support console HTML (list, user page, day strip) | `streaks/support_view.py` |
| SQL / S3 / HTTP adapters | `streaks/store.py`, `streaks/storage.py`, `streaks/api.py` |

To change a rule, edit `streaks/rules.py`, then run `make csv` and `make test`.

## How this would work at 2M users (not built)

1. **A per-user day table, updated on ingest.** Each event updates only its own local day's row. A day becomes final once the 7-day sync cap passes, and stays open until then.
2. **A late event recomputes only that user's open window** (at most 7 days plus the walk forward), never the full history. The streak is `last final streak + open days`.
3. **Ingest partitioned by `user_id`** behind a queue (Kafka/Kinesis). Writes are idempotent on `event_id`, with the content key deduped per partition, so retries and replays are safe.
4. **The streak is cached per user and invalidated on write.** GETs read the cache, which removes the recompute-on-read cost this version has.
5. **S3 raw log as the replay source.** A rule change (like the 36h cap) is a backfill job over S3, run in parallel per user partition. Results are compared before the switch.
