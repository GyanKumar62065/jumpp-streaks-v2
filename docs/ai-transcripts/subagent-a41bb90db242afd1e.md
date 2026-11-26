# Subagent: Simplify review: altitude

Source log: `agent-a41bb90db242afd1e.jsonl` (Claude Code session export, rendered to Markdown; long tool output trimmed, emails redacted).


---

## 🧑 User · 2026-11-26 07:06:50

Read-only code-quality review (do NOT edit files). Repo: /Users/gyankumar/Personal/jumpp_streak_test. Scope: every file in streaks/*.py (all new; no git history). Context: AGENTS.md (layer boundaries: engine pure, rules only in rules.py, api thin, store only SQL, storage only S3), CLAUDE.md, spec docs/superpowers/specs/2026-11-26-streaks-v2-design.md.

Angle: ALTITUDE. Check each mechanism sits at the right depth: special cases layered on shared code, logic in the wrong layer (rules in report/api/support_view, validation outside parsing), symptom patches instead of root-cause fixes. Name the simpler, more general change. Ignore correctness bugs. Return up to 8 findings, each: file, line, one-line summary, concrete cost. Under 300 words.


---

## 🧑 User · 2026-11-26 07:06:50

<system-reminder>
Your final report is delivered through SubagentHandback: when your work is complete, call SubagentHandback({message: <your full report>}). The call ends your run, so make it your last step. Only a SubagentHandback call reaches your caller as your result; plain text you write at the end is not delivered. Do not also send the report with SendMessage: your caller would get it twice.
</system-reminder>

**Tool call: `Bash`**

<details><summary>Input</summary>

````
{
  "command": "cd /Users/gyankumar/Personal/jumpp_streak_test; cat AGENTS.md | head -80; wc -l streaks/*.py",
  "description": "Read AGENTS.md and list streaks files"
}
````
</details>

<details><summary>Tool result</summary>

````
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
  - Input: 
… [trimmed 557 chars]
````
</details>

**Tool call: `Bash`**

<details><summary>Input</summary>

````
{
  "command": "cd /Users/gyankumar/Personal/jumpp_streak_test; sed -n 80,200p AGENTS.md; for f in streaks/*.py; do echo \"=== $f\"; cat -n $f; done",
  "description": "Read rest of AGENTS.md and all streaks sources"
}
````
</details>

<details><summary>Tool result</summary>

````
<persisted-output>
Output too large (61.1KB). Full output saved to: /Users/gyankumar/.claude/projects/-Users-gyankumar-Personal-jumpp-streak-test/5d738e50-3ace-4175-8a26-49dc5338deba/tool-results/bpwjc5von.txt

Preview (first 2KB):
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
...
</persisted-output>
````
</details>

**Tool call: `Read`**

<details><summary>Input</summary>

````
{
  "file_path": "/Users/gyankumar/.claude/projects/-Users-gyankumar-Personal-jumpp-streak-test/5d738e50-3ace-4175-8a26-49dc5338deba/tool-results/bpwjc5von.txt",
  "allow_large": true
}
````
</details>

<details><summary>Tool result</summary>

````
1	  - Output: day rows and a streak result.
2	- `store.py`: the only module that runs SQL.
3	- `storage.py`: the only module that calls S3.
4	- `ingest.py`: parses, normalises and dedupes, then calls `store` and `storage`.
5	- `api.py`: thin. It parses input, calls `store` and `engine`, and returns JSON. No rules here.
6	- `support_view.py`: renders HTML from engine output. No rules here.
7	
8	## Data rules
9	- Store **raw events** only. Never store a computed streak as truth.
10	- Insert idempotently with `ON CONFLICT (event_id) DO NOTHING`.
11	- Content dedupe on `(user_id, event_type, video_id, client_ts)` happens **in the engine**. It keeps the earliest `received_at`, so the result is order-independent.
12	- The engine only sees events with `received_at ≤ as_of`.
13	- Keep all timestamps tz-aware. Store `timestamptz`. Never use naive datetimes.
14	- Timezones: `zoneinfo` only. Compute a local day with `client_ts.astimezone(ZoneInfo(device_tz)).date()`.
15	- `received_at` is required on POST. Default it to server now only when it's missing.
16	- `as_of` is always explicit in the engine. The API defaults it to "now".
17	
18	## API contract
19	- `POST /events`: JSON list of events. Returns counts `{inserted, duplicate, invalid}`.
20	- `GET /users/{id}/streak?as_of=`: `{current_streak, status, reason}`.
21	- `GET /users/{id}/days?from=&to=`: `[{date, code, watched_s, detail}]`.
22	- `GET /support/{id}`: HTML.
23	- Errors: 404 for an unknown user, 422 for bad input. No silent drops.
24	
25	## Testing
26	- Engine tests use in-memory events. No DB.
27	- Must cover dedupe, order independence, late sync within and beyond the cap, tampering, outage bridge and travel.
28	- One API smoke test against Compose Postgres is enough.
29	- Name tests by behaviour, for example `test_late_sync_beyond_cap_is_rejected`.
30	
31	## Code style
32	- Simple first. No layer, class or option without a present need.
33	- Names follow `naming-cheatsheet`: verbs for functions, `is_`/`has_` for booleans, units on constants (`_S`, `_H`).
34	- Small functions. Type hints on public functions.
35	- Comments say **why**, not what.
36	
37	## Don'ts
38	- Don't hand-edit the generated CSV.
39	- Don't edit `brief/` or `data/`.
40	- Don't add caching, queues or background workers.
41	- Don't commit, push or deploy unless the user asks.
42	=== streaks/__init__.py
43	=== streaks/api.py
44	     1	"""HTTP edge. Thin: parse input, call ingest/engine, return values. No rules here."""
45	     2	
46	     3	from collections.abc import Callable
47	     4	from dataclasses import asdict
48	     5	from datetime import UTC, date, datetime
49	     6	
50	     7	from fastapi import FastAPI, HTTPException, Query, Request
51	     8	from fastapi.responses import HTMLResponse, JSONResponse
52	     9	
53	    10	from streaks.engine import compute_streak
54	    11	from streaks.ingest import ingest_posted_events
55	    12	from streaks.models import ParseError, StreakResult, User
56	    13	from streaks.parsing 
… [trimmed 65421 chars]
````
</details>

**Tool call: `SubagentHandback`**

<details><summary>Input</summary>

````
{
  "message": "Altitude review of streaks/*.py (read-only, no edits). 8 findings:\n\n1. **engine.py:56-60.** `_get_queue_depth` decodes `meta[\"queue_depth\"]` inside the engine and quietly turns bad values into 0. Cost: this is parsing outside parsing.py, and a malformed value silently changes when a day goes final, which breaks \"no silent drops\". Fix: parse `queue_depth` once in parsing.py into a typed field.\n\n2. **engine.py:175-189.** `_add_spans_for_unmapped_watch_days` patches the symptom after `get_day_spans`: watches get their day from `device_tz`, but timeline.py builds days from tz_change events only. Cost: \"which local day\" has two sources of truth, and the made-up spans get a fixed 24h length, so the travel rule (line 110) can never apply to them. Fix: build spans in timeline.py from every event's `device_tz`.\n\n3. **report.py:10-22.** `ACTION_BY_CODE` hardcodes rule values (\"2-minute\", \"7-day sync limit\") as text. Cost: change `MIN_DAILY_WATCH_S` or `MAX_OFFLINE_DELAY_H` and the support advice goes stale without warning. Fix: build these strings from `rules`, the same way engine.py:85-89 does.\n\n4. **report.py:60-71.** The refund rule (`_has_unneeded_purchased_freeze`) lives in the report layer. Cost: it is a business rule with no engine test, and it never reaches the API or CSV. Fix: compute it in the engine as a `StreakResult` field.\n\n5. **engine.py:109.** The detail text hardcodes \"9 Nov outage\", while the window itself sits in `rules.OUTAGE_START`. Cost: the date is stated twice and they can drift. Fix: format the text from `outage.start`.\n\n6. **watches.py:71 / ingest.py:42-47.** Reference checks run only on the POST path. Seed `load_inputs` skips them, so the engine filters unknown videos again with `video_id in videos`, even though the docstring says ingest already rejected them. Cost: validation is split, and seed events with unknown video ids are dropped silently. Fix: run `_check_references` on both ingest paths and remove the engine guard.\n\n7. **api.py:33-39 / parsing.py:189-194.** Date parsing lives in api.py, and parsing.py keeps two `parse_timestamp` variants (one raises, one returns a value). Cost: the decoding rules are spread across the boundary. Fix: keep one value-returning parser in parsing.py.\n\n8. **ingest.py:28-30.** `INPUT_FILES[:3]` is a positional slice used only to special-case where `affected_uids` comes from. Cost: reordering the tuple breaks seeding silently. Fix: use an explicit mapping from file name to source path."
}
````
</details>

<details><summary>Tool result</summary>

````
{"success":true,"message":"Report delivered to your caller."}
````
</details>
