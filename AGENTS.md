# AGENTS.md: tech boundaries

Short rules for any agent or human writing code here. Project context lives in `CLAUDE.md`.

## How we write code (Must Use)


These are heurisics, not hard rules. hey describe what good code looks like here. When following
one would make a change worse, use judgment and say why in the change.


Choose reasonable defaults and make them visible: nothing a reader or user depends on should be
assumed silently. Solve problems at their cause, deliberately rather than ad hoc; avoid workarounds,
hacks and second-best paths.


### Shape


- **Modular.** Packages and modules have clear boundaries and dend on stable abstractions, not on
  each other's details.
- **One concern per module.** Keep definition, validation, runti behaviour and inspection apart.
- **Cohesive functions.** Usually 20–50 lines, rarely past about00. Split a function when it does two
  things, not to hit a number; don't scatter one idea across one-line helpers.
- **No god files.** When a file collects unrelated responsibilits, split it along those lines.


### Clarity


- **Readable first.** Names say what things are in the domain; t code should make sense without its
  comments.
- **Comments explain why,** not what.
- **Follow the surroundingode** before inventing a new pattern


### Behaviour


- **Expected outcomes are values** (results, decisions); exceptis are for programming errors.
- **Parse at the boundary.** Decode untrusted input once, then wk with typed domain values.
- **Effects at the edges.** Take time, IDs, randomness and I/O ainjected ports instead of reaching
  for globals, so code stays deterministic under test.
- **Export deliberately.** A small public surface through one eny point; internals stay internal.


### Risk


- **Complexity needs coverage.** Complex, untested code is the rkiest code. Prefer simplifying a
  function to excusing it, and don't let quality measures loosen silently.
- **Test invariants, not implementations.** One test per rule, pperty tests where a rule is general,
  type tests for public types.
- **Specify before you build.** For protocols and lifecycles, ste the rules precisely (a model or
  explicit invariants) before or alongside the code, and test the code against them.
- **Keep hot paths cheap.** Expensive checks belong in developme mode.


### Dependencies


- **Fewer is better.**
- **Librars don't pick platforms.** They take ports; applicatis and tests choose the drivers.



## Stack (fixed)
- Python 3.12 (Docker image `python:3.12-slim`).
- FastAPI + Uvicorn.
- Postgres 16. Driver `psycopg` v3. **No ORM.**
- S3 through `boto3`, pointed at Floci (`floci/floci:latest`, port 4566).
- pytest for tests.
- Docker Compose for everything. Services: `floci`, `postgres`, `seed`, `api`.
- No other dependency without asking the user first.

## Layer boundaries
- `rules.py`: constants only. No logic, no imports from the package.
- `engine.py`: **pure functions**. No DB, no S3, no HTTP, no `datetime.now()`.
  - Input: a list of events, the user, videos, the outage window, `as_of`.
  - Output: day rows and a streak result.
- `store.py`: the only module that runs SQL.
- `storage.py`: the only module that calls S3.
- `ingest.py`: parses, normalises and dedupes, then calls `store` and `storage`.
- `api.py`: thin. It parses input, calls `store` and `engine`, and returns JSON. No rules here.
- `support_view.py`: renders HTML from engine output. No rules here.

## Data rules
- Store **raw events** only. Never store a computed streak as truth.
- Insert idempotently with `ON CONFLICT (event_id) DO NOTHING`.
- Content dedupe on `(user_id, event_type, video_id, client_ts)` happens **in the engine**. It keeps the earliest `received_at`, so the result is order-independent.
- The engine only sees events with `received_at ≤ as_of`.
- Keep all timestamps tz-aware. Store `timestamptz`. Never use naive datetimes.
- Timezones: `zoneinfo` only. Compute a local day with `client_ts.astimezone(ZoneInfo(device_tz)).date()`.
- `received_at` is required on POST. Default it to server now only when it's missing.
- `as_of` is always explicit in the engine. The API defaults it to "now".

## API contract
- `POST /events`: JSON list of events. Returns counts `{inserted, duplicate, invalid}`.
- `GET /users/{id}/streak?as_of=`: `{current_streak, status, reason}`.
- `GET /users/{id}/days?from=&to=`: `[{date, code, watched_s, detail}]`.
- `GET /support/{id}`: HTML.
- Errors: 404 for an unknown user, 422 for bad input. No silent drops.

## Testing
- Engine tests use in-memory events. No DB.
- Must cover dedupe, order independence, late sync within and beyond the cap, tampering, outage bridge and travel.
- One API smoke test against Compose Postgres is enough.
- Name tests by behaviour, for example `test_late_sync_beyond_cap_is_rejected`.

## Code style
- Simple first. No layer, class or option without a present need.
- Names follow `naming-cheatsheet`: verbs for functions, `is_`/`has_` for booleans, units on constants (`_S`, `_H`).
- Small functions. Type hints on public functions.
- Comments say **why**, not what.

## Don'ts
- Don't hand-edit the generated CSV.
- Don't edit `brief/` or `data/`.
- Don't add caching, queues or background workers.
- Don't commit, push or deploy unless the user asks.
