# Streaks-v2: design spec

- **Status:** draft, for user review.
- **Date:** 2026-11-26.
- **Context:** `CLAUDE.md` (project memory), `AGENTS.md` (tech limits), `brief/ASSIGNMENT.md` (the brief).
- **"Now":** 15 Nov 2026, 10:00 IST (`2026-11-15T04:30:00Z`).

---

## 1. Intent

### Why
- The streak is Jumpp's biggest retention lever. It's also the biggest source of angry tickets.
- Today's streak breaks wrongly: offline syncs, travel, our own outage. And it can be faked: clock tampering, swiping.
- The grader checks **judgement**. Every number must trace back to a written rule.

### Goals
- One pure engine turns raw events into day rows and a streak.
- Same events give the same answer, whatever the arrival order or duplicates.
- Every day has a reason code a support agent understands in 10 seconds.
- Changing one constant (for example `MAX_OFFLINE_DELAY_H`) changes the output predictably.
- CSV, API, DECISIONS and TICKETS agree, because they all come from one engine.

### Non-goals
- Production scale, auth, styling, push sending, a freeze purchase flow.

### Anti-goals (a failure even if it "works")
- Numbers in TICKETS that the engine doesn't produce.
- Rules hidden inside the API or SQL instead of `rules.py`.
- Matching Pooja's numbers by bending a rule.
- A "lost streak" message for a day that can still sync.

---

## 2. Approaches considered

| Approach | Trade-off | Verdict |
|---|---|---|
| **A. Recompute from raw events on every read (pure engine)** | Simplest. Order-independent by construction. Too slow at 2M users | **Chosen** for the take-home |
| B. Incremental day table updated on ingest | Scales. But order-dependence and late events need re-open logic. ~2x the code | Described only (README, 2M notes) |
| C. Event-sourced projections with a streaming job | Production-grade. Far beyond 3h | Rejected |

- Infra stack is the user's choice: Python, FastAPI, Postgres, pytest, Docker Compose, Floci S3.

---

## 3. Rules (the core)

All constants live in `streaks/rules.py`.

### 3.1 Constants
| Constant | Value | Why |
|---|---|---|
| `MIN_DAILY_WATCH_S` | 120 | Farhan's "2 minutes a day" |
| `COMPLETION_RATIO` | 0.9 | Finishing one short lesson is real learning (Neha) |
| `MAX_OFFLINE_DELAY_H` | 168 (7d) | The app queues up to 7 days (Sameer) |
| `MAX_CLOCK_AHEAD_S` | 300 | `client_ts` later than `received_at` means the clock was moved forward |
| `PENDING_WINDOW_H` | 48 | Matches the beta's pending state. Gives most offline users time to sync |
| `MIN_DAY_LENGTH_H` | 12 | A local day cut shorter than this by a timezone jump is a "short day" |
| `OUTAGE_START`, `OUTAGE_END` | 2026-11-09 15:15Z to 16:20Z | From the incident report |
| `OUTAGE_AFFECTED_UIDS` | `config/affected_uids.csv` → `affected_uids` table | The uids in the LB log sample: u31877, u08, u55120, u12 |

### 3.2 A watch
- A watch = one deduped `video_end` with `watched_s > 0`.
- `watch_started_at = video_end.client_ts − watched_s`. No start/end pairing is needed.
- **Day = local date of `watch_started_at`** in that event's `device_tz`.
  - Why: u05 pressed play at 23:59:05 and finished at 00:00:27. The lesson was started on the 9th.
- `video_start` with no `video_end` gives a watch of 0s.

### 3.3 Trusting a watch (in order; the first failure wins)
1. `video.published_at > watch_started_at` → `REJECTED_TAMPER` ("lesson not published yet").
2. `client_ts > received_at + MAX_CLOCK_AHEAD_S` → `REJECTED_TAMPER` ("clock ahead of server").
3. `received_at − client_ts > MAX_OFFLINE_DELAY_H` → `REJECTED_TOO_LATE`.
4. Otherwise it's trusted. If `received_at − client_ts > 1h`, mark it late ("late sync").

### 3.0 What `as_of` means
- `as_of` = "what we knew at that moment".
- The engine uses only events with `received_at ≤ as_of`.
  - So `as_of=2026-11-08T09:00+05:30` shows u07's 7 Nov as missed, which is what the app showed when they bought the freeze.
- `as_of` also sets the user's "today" and the pending windows.
- **Default `as_of`** = env `STREAKS_DEFAULT_AS_OF`, set to `2026-11-15T10:00:00+05:30` in Compose.
  - Why: the brief fixes "now". The real clock (26 Nov+) would break every user.
  - Graders can pass `as_of`, or change the env. The README says so.

### 3.4 Duplicates
- Key 1: `event_id`. Postgres has one unique index on it, with `ON CONFLICT DO NOTHING`.
- Key 2: `(user_id, event_type, video_id, client_ts)`. This catches 3.1.x resends with new ids.
  - **Handled in the engine only.** Postgres keeps every raw copy.
  - The engine keeps the copy with the **earliest `received_at`** (tie: smallest `event_id`).
  - Why: resends are ~40s apart. "First to arrive in the DB" would make results depend on arrival order.

### 3.4b Which timezone a day lives in
- Build a timezone timeline per user:
  - Start with `home_tz` from signup.
  - Switch whenever an event's `device_tz` differs from the current one, at that event's `client_ts`. This includes `tz_change` and any other event, so it is the "last known `device_tz`".
- All instants are UTC. A DST day has its real length (23h or 25h), and windows are real elapsed time.
- `as_of` before the signup instant gives no days.
- A local date's span = the instants the user spent on that date along the timeline.
  - "Day end" = the last instant of that span. Pending windows use it.
  - "Day length" = the span's total duration. The short-day rule uses it.
- A watch still uses its own event's `device_tz` (§3.2). The timeline is only for days with no events, day ends and "today".
- The outage overlaps a day if `[OUTAGE_START, OUTAGE_END]` intersects that day's span.

### 3.5 Day classification
For each local day, from `max(local signup date, HISTORY_START_DATE = 2026-11-01)` to the user's local "today". Days before signup are not emitted.

| Order | Condition | Code | Effect |
|---|---|---|---|
| 2 | Trusted watch ≥ 120s total **or** one trusted watch ≥ 90% of its lesson | `LEARNED` / `LEARNED_LATE_SYNC` | +1 |
| 3 | Day is "today" (local) and not learned yet | `TODAY_OPEN` | none |
| 4 | User is in `affected_uids`, the outage overlaps this local day, and the day isn't learned | `PROTECTED_OUTAGE` | bridge |
| 5 | Local day shorter than `MIN_DAY_LENGTH_H` due to `tz_change` | `SKIPPED_TRAVEL` | bridge |
| 6 | `as_of < day_end + PENDING_WINDOW_H`, **or** the device still has unsynced events (below) | `PENDING` | none yet |
| 7 | Streak > 0, a freeze is available, and the day is **not** tampered | `PROTECTED_FREEZE` (uses 1) | bridge |
| 8 | Only rejected watches that day | `REJECTED_TAMPER` / `REJECTED_TOO_LATE` | break |
| 9 | Some trusted watch, but below the rule | `BELOW_THRESHOLD` | break |
| 10 | Nothing | `NO_ACTIVITY` | break |

- **Bridge** = the streak survives, and the count doesn't change. Everyone in the thread agreed on this.
- **Unsynced device (the u07 rule):**
  - Take the latest `app_open` with `received_at ≤ as_of`.
  - If it was received after the day ended and has `queue_depth > 0`, the day stays `PENDING`.
  - Capped at `day_end + MAX_OFFLINE_DELAY_H`. After that the day is final, whatever the queue says.
  - 3.1.x sends no `queue_depth`, so the rule doesn't apply there.
- **Freeze pool** = `users.freeze_balance` (read as the balance on 1 Nov), plus every `freeze_purchase` with `received_at ≤ as_of`.
  - A freeze can cover any final miss, including one before the purchase. That's the "buy to repair" flow (u07).
  - Spent oldest final miss first, and only when the streak is > 0. We never burn a freeze on a 0 streak.
  - A freeze freed by a late sync goes back to the pool and can cover a later miss.
  - The old system's `freeze_applied` events are **ignored**. v2 decides freeze use itself.
- **Tampered days are never bridged by a freeze.** Cheating isn't protected.
- **`LEARNED_LATE_SYNC` only when the on-time watches alone don't qualify.** One small late watch doesn't relabel an on-time day.
- **Late events re-open days.** A late watch turns a past `PROTECTED_FREEZE` into `LEARNED_LATE_SYNC`.
  - **Refundable** = purchases received after a day ended and before that day's late lesson arrived. That's the user buying because the day *looked* missed (u07). Capped at the freezes still unused.
  - Support action: refund ₹49 × refundable.
- The engine also returns `freezes_unused` and `freezes_used`. The support view needs them.

### 3.6 Streak and status
- Start from `streak_as_of_2026_10_31`.
- Walk the days in order: +1 on learned, unchanged on bridge or pending, reset to 0 on break.
- `TODAY_OPEN` never breaks.
- `status`, where the first match wins:
  1. `BROKEN`: `current_streak == 0`. Covers new users too. The reason says which.
  2. `PENDING`: any day is still `PENDING`. The streak shown is safe-so-far.
  3. `ACTIVE`: today is learned.
  4. `AT_RISK`: today isn't learned yet.
- `reason`: one line from the most recent day that changed things, e.g. "13 Nov synced late, counted".
- The user's local "today" = local date of `as_of` in the last known `device_tz`, else `home_tz`.

### 3.7 Unverifiable late syncs (u13, u14)
- Policy: **accept**, coded `LEARNED_LATE_SYNC`, and flagged for review.
- Rough cost at 2M MAU (90,000 cases a month, 60% would break a 7+ streak):
  - Rejecting honest users costs ~₹16 L/month.
  - Accepting fakes costs ~₹2 L/month.
  - DECISIONS.md shows the full maths.
- We'd change it if audited tampering went above ~70%, or if fakes moved the leaderboards.

### 3.8 Missed-day timeline (rules in code, table in DECISIONS)
- No "lost" message while a day is `PENDING`.
- Freeze is **offered or used only after 48h**, and never while the device reports unsynced events (§3.5, the u07 rule).
- The engine produces these states. DECISIONS.md writes the three-user table from them.
- Push and offer messages themselves are described only, not built.

---

## 4. Expected results (to be verified by the engine)

As of 15 Nov 10:00 IST. These are hand predictions. The engine output wins. Rows marked ✱ have a day close to the threshold.

| User | Expected | Why |
|---|---|---|
| u01 | 12 ✱ | Started 3 Nov. Days 8 and 9 rely on completion |
| u02 | 54 | LA local days 1–13 learned; at "now" it is 14 Nov 20:30 in LA and the lesson comes at 21:02 PST, so 14 Nov is still `TODAY_OPEN` |
| u03 | 26 ✱ | Offline 10 Nov synced within the cap |
| u04 | 0 | Swiping from 6 Nov, `BELOW_THRESHOLD` |
| u05 | 20 | 9 Nov counted by start time |
| u06 | 5 | 8 and 9 Nov `REJECTED_TAMPER` (v037 published 10 Nov) |
| u07 | 72 | 7 Nov late sync. The freeze wasn't needed → refund |
| u08 | 313 | 9 Nov `PROTECTED_OUTAGE` bridges, doesn't add |
| u09 | 2 | Signup day counts |
| u10 | 23 | 12 Nov: 101s of 104s = completion |
| u11 | 3 | 11 Nov: start with no end → break |
| u12 | 9 | 5 Nov `NO_ACTIVITY` |
| u13 | 58 | 12 Nov late sync accepted |
| u14 | 65 | 11 Nov late sync accepted |
| u15 | 30 | 10 Nov (10h40m day) `SKIPPED_TRAVEL` |

- Pooja's promises that differ: u02 (55 → 54, day still open in LA), u06 (47 → 5), u08 (314 → 313).

---

## 5. Data model (Postgres)

```
users(user_id PK, name, signup_at timestamptz, home_tz, plan,
      freeze_balance int, streak_as_of_2026_10_31 int)
videos(video_id PK, title, duration_s int, published_at timestamptz)
events(event_id PK, user_id, event_type, video_id NULL, watched_s NULL,
       client_ts timestamptz, device_tz, received_at timestamptz,
       app_version, meta jsonb)       -- content dedupe happens in the engine (§3.4)
affected_uids(user_id PK)
```
- `meta` is parsed from `k=v;k=v` into JSON on ingest.
- No computed tables.

## 6. Storage (Floci S3)
- Bucket `jumpp-streaks`.
- `inputs/*.csv` holds the 4 data files, uploaded by the `seed` service.
- `raw/posts/{yyyy-mm-dd}/{uuid}.json` holds every `POST /events` body, archived before the insert.
- `make rebuild` replays `inputs/` and then `raw/posts/` into an empty Postgres. That proves "we can't lose it".

## 7. API

| Endpoint | Returns |
|---|---|
| `POST /events` | Body: a JSON list. `received_at` is optional, defaulting to server now (the replay flag). Returns `{inserted, duplicate, invalid}` |
| `GET /users/{id}/streak?as_of=` | `{user_id, as_of, current_streak, status, reason}` |
| `GET /users/{id}/days?from=&to=` | `[{date, code, counted_watch_s, detail}]` |
| `GET /support/{id}?as_of=` | HTML table: Date · Code · What happened · What to do |

- **POST with partly bad batches:**
  - Valid items go in. Bad items (missing fields, unknown user, bad timestamp) are counted in `invalid`.
  - Bad items are listed as `errors: [{index, message}]`, and the response is 200.
  - 422 only when the body isn't a JSON list at all.
- GET: 404 for an unknown user. 422 for a bad `as_of`/`from`/`to`.
- `as_of` defaults per §3.0. The CSV script passes 15 Nov 10:00 IST explicitly.

## 8. Support view
- One table, newest day first.
- Columns: Date | Code | What happened (plain words) | What to do (one action, e.g. "Refund ₹49", "No action", "Explain the 2-min rule").
- A header line: current streak, status, plan, freeze balance.

## 9. Infra (Docker Compose)
- `floci`: `floci/floci:latest`, port 4566.
- `postgres`: `postgres:16`, with a healthcheck.
- `seed`: a one-shot job. Creates the bucket, uploads `data/*.csv`, applies `sql/schema.sql`, loads from S3.
- `api`: Uvicorn on port 8000. Depends on `seed` finishing.
- Goal: `docker compose up --build` gives a working API in under 2 minutes.

## 10. Tests (pytest)
Engine tests are pure, with in-memory events:
1. `test_duplicate_and_resent_events_count_once`
2. `test_result_is_independent_of_event_order` (shuffle)
3. `test_late_sync_within_cap_counts` / `test_late_sync_beyond_cap_is_rejected`
4. `test_watch_before_publish_is_rejected_as_tamper`
5. `test_outage_day_bridges_without_adding`
6. `test_watch_is_assigned_to_start_day_across_midnight`
7. `test_short_travel_day_is_skipped`
8. `test_late_sync_returns_used_freeze`

Plus one API smoke test: POST a duplicate, then GET the streak.

## 11. Docs to write (after code)
- `README.md`: run in 2 minutes, curl examples, plus 3 to 5 bullets on 2M users:
  1. A per-user day table updated incrementally on ingest. A day becomes final after the cap.
  2. Recompute only the affected user's open window (≤ 7 days) on a late event.
  3. Partition events by `user_id`. Ingest through a queue. Writes stay idempotent on the unique keys.
  4. Cache the streak per user and invalidate it on write.
  5. S3 raw log as the replay source for rule changes (backfill job).
- `DECISIONS.md`, `TICKETS.md`, the CSV. All are numbers from the engine.

## 12. Calls I made (please check)
1. A watch counts on the day it **started**, not finished.
2. **120s total OR one lesson ≥ 90%**, a middle ground between Farhan and Neha.
3. Pending for **48h**, separate from the 7-day sync cap. A late sync still re-opens a finalised day.
4. **Freezes are auto-used** from the balance after pending ends. The old `freeze_applied` events are ignored.
5. **u15's short travel day bridges.** The alternative is to use their free freeze. The streak is 30 either way.
6. `affected_uids` is seeded with the uids in the log sample only (u08, u12, plus 2 others).
7. Floci S3 holds the inputs plus the raw POST archive. Postgres can be rebuilt from it.
8. `as_of` = what we knew then (`received_at ≤ as_of`). The default is fixed to 15 Nov 10:00 IST through an env var, not the real clock.
9. Content dedupe in the engine, keeping the earliest `received_at`. Postgres dedupes on `event_id` only.
10. The `queue_depth > 0` hold is in the engine, capped at 7 days.
11. Freezes cover any earlier final miss. Never spent on a 0 streak. A freed freeze returns to the pool.
12. Status order: BROKEN > PENDING > ACTIVE > AT_RISK.
13. A partly bad POST batch returns 200 with per-item errors.

## 13. Left to the builder
- Module internals and function names (within `AGENTS.md`).
- SQL details, the Compose file layout, the curl examples.
- Exact wording of the `reason` and support "What to do" text.
