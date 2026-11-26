# Subagent: Builder check on streaks spec

Source log: `agent-ab04944e741a1319c.jsonl` (Claude Code session export, rendered to Markdown; long tool output trimmed, emails redacted).


---

## 🧑 User · 2026-11-26 06:34:47

You are a talented backend software engineer (Python/FastAPI/Postgres). You've been handed a design document and asked to put together a plan to build what it describes. You will not be able to talk to the person who wrote it.

Read /Users/gyankumar/Personal/jumpp_streak_test/docs/superpowers/specs/2026-11-26-streaks-v2-design.md. Supporting context, if needed: /Users/gyankumar/Personal/jumpp_streak_test/CLAUDE.md, AGENTS.md, brief/ASSIGNMENT.md, and data/*.csv. Read-only: do not modify any file.

Report only the questions you'd still need answered before you could plan this well: places where you'd have to guess and a wrong guess would matter. For each, give the question and why the answer changes the plan. Rank them by importance.

Skip anything the document explicitly leaves to the builder, and anything you could reasonably decide yourself. Skip nitpicks about wording.

If nothing important is left, say "nothing important left". Keep the report under 400 words.


---

## 🧑 User · 2026-11-26 06:34:47

<system-reminder>
Your final report is delivered through SubagentHandback: when your work is complete, call SubagentHandback({message: <your full report>}). The call ends your run, so make it your last step. Only a SubagentHandback call reaches your caller as your result; plain text you write at the end is not delivered. Do not also send the report with SendMessage: your caller would get it twice.
</system-reminder>

**Tool call: `Read`**

<details><summary>Input</summary>

````
{
  "file_path": "/Users/gyankumar/Personal/jumpp_streak_test/docs/superpowers/specs/2026-11-26-streaks-v2-design.md"
}
````
</details>

<details><summary>Tool result</summary>

````
1	# Streaks-v2: design spec
2	
3	- **Status:** draft, for user review.
4	- **Date:** 2026-11-26.
5	- **Context:** `CLAUDE.md` (project memory), `AGENTS.md` (tech limits), `brief/ASSIGNMENT.md` (the brief).
6	- **"Now":** 15 Nov 2026, 10:00 IST (`2026-11-15T04:30:00Z`).
7	
8	---
9	
10	## 1. Intent
11	
12	### Why
13	- The streak is Jumpp's biggest retention lever. It's also the biggest source of angry tickets.
14	- Today's streak breaks wrongly: offline syncs, travel, our own outage. And it can be faked: clock tampering, swiping.
15	- The grader checks **judgement**. Every number must trace back to a written rule.
16	
17	### Goals
18	- One pure engine turns raw events into day rows and a streak.
19	- Same events give the same answer, whatever the arrival order or duplicates.
20	- Every day has a reason code a support agent understands in 10 seconds.
21	- Changing one constant (for example `MAX_OFFLINE_DELAY_H`) changes the output predictably.
22	- CSV, API, DECISIONS and TICKETS agree, because they all come from one engine.
23	
24	### Non-goals
25	- Production scale, auth, styling, push sending, a freeze purchase flow.
26	
27	### Anti-goals (a failure even if it "works")
28	- Numbers in TICKETS that the engine doesn't produce.
29	- Rules hidden inside the API or SQL instead of `rules.py`.
30	- Matching Pooja's numbers by bending a rule.
31	- A "lost streak" message for a day that can still sync.
32	
33	---
34	
35	## 2. Approaches considered
36	
37	| Approach | Trade-off | Verdict |
38	|---|---|---|
39	| **A. Recompute from raw events on every read (pure engine)** | Simplest. Order-independent by construction. Too slow at 2M users | **Chosen** for the take-home |
40	| B. Incremental day table updated on ingest | Scales. But order-dependence and late events need re-open logic. ~2x the code | Described only (README, 2M notes) |
41	| C. Event-sourced projections with a streaming job | Production-grade. Far beyond 3h | Rejected |
42	
43	- Infra stack is the user's choice: Python, FastAPI, Postgres, pytest, Docker Compose, Floci S3.
44	
45	---
46	
47	## 3. Rules (the core)
48	
49	All constants live in `streaks/rules.py`.
50	
51	### 3.1 Constants
52	| Constant | Value | Why |
53	|---|---|---|
54	| `MIN_DAILY_WATCH_S` | 120 | Farhan's "2 minutes a day" |
55	| `COMPLETION_RATIO` | 0.9 | Finishing one short lesson is real learning (Neha) |
56	| `MAX_OFFLINE_DELAY_H` | 168 (7d) | The app queues up to 7 days (Sameer) |
57	| `MAX_CLOCK_AHEAD_S` | 300 | `client_ts` later than `received_at` means the clock was moved forward |
58	| `PENDING_WINDOW_H` | 48 | Matches the beta's pending state. Gives most offline users time to sync |
59	| `MIN_DAY_LENGTH_H` | 12 | A local day cut shorter than this by a timezone jump is a "short day" |
60	| `OUTAGE_START`, `OUTAGE_END` | 2026-11-09 15:15Z to 16:20Z | From the incident report |
61	| `OUTAGE_AFFECTED_UIDS` | from the `affected_uids` table | Seeded from the LB log sample |
62	
63	### 3.2 A watch
64	- A watch = one deduped
… [trimmed 9655 chars]
````
</details>

**Tool call: `Bash`**

<details><summary>Input</summary>

````
{
  "command": "cd /Users/gyankumar/Personal/jumpp_streak_test; ls -R | grep -v node_modules | head -60; cat CLAUDE.md AGENTS.md brief/ASSIGNMENT.md; for f in data/*.csv; do echo \"== $f\"; wc -l $f; head -5 $f; done",
  "description": "List project and read context docs and CSV heads"
}
````
</details>

<details><summary>Tool result</summary>

````
AGENTS.md
brief
CLAUDE.md
data
docs
SUBMISSION_QUESTIONS.md

./brief:
ASSIGNMENT.md
economics.md
incident_2026-11-09.md
stakeholder_thread.md
support_expected_streaks.md
support_tickets.md

./data:
beta_cohorts.csv
events.csv
users.csv
videos.csv

./docs:
superpowers

./docs/superpowers:
specs

./docs/superpowers/specs:
2026-11-26-streaks-v2-design.md
# CLAUDE.md: Jumpp streaks-v2 take-home

## Index
1. [What this is](#1-what-this-is)
2. [Deliverables](#2-deliverables)
3. [Repo map](#3-repo-map)
4. [Architecture](#4-architecture)
5. [Streak rules (decisions)](#5-streak-rules-decisions)
6. [Reason codes](#6-reason-codes)
7. [Stakeholder calls](#7-stakeholder-calls)
8. [Known data traps](#8-known-data-traps)
9. [Scope and cuts](#9-scope-and-cuts)
10. [Commands](#10-commands)
11. [Working rules](#11-working-rules)

---

## 1. What this is
- A take-home for Inkpen Labs: rebuild the Jumpp 🔥 daily streak ("streaks-v2").
- **Time box: 3 hours.** Judgement over polish. Honest and unfinished beats vague.
- "Now" is **15 Nov 2026, 10:00 IST**. Data covers 1 to 14 Nov 2026, 15 users.
- Graders POST extra events (with their own `received_at`) and check results against **our stated rules**.
- The full brief is in `brief/ASSIGNMENT.md`. Read it before changing scope.

## 2. Deliverables
| # | File / thing | Priority |
|---|---|---|
| 1 | `DECISIONS.md` (≤2 pages) | Highest. Never cut |
| 2 | Service: `POST /events`, `GET /users/{id}/streak`, `GET /users/{id}/days` | Medium. Cut breadth first |
| 3 | Support view: one HTML page per user | Low |
| 4 | `TICKETS.md`: 10 tickets + reply to Pooja | High. Never cut |
| 5 | `streaks_as_of_2026-11-15T1000IST.csv`, generated by code | Must agree with 1 and 4 |
| 6 | Screen recording (36h offline cap change) | The user does it. Never cut |
| 7 | `SUBMISSION_QUESTIONS.md` | **The user answers it, without AI.** Do not draft Q3 to Q19 |

- **Consistency rule:** CSV, API, DECISIONS and TICKETS must agree. One engine produces all numbers.

## 3. Repo map
```
.
├── CLAUDE.md / AGENTS.md      # project memory + tech boundaries
├── README.md                  # run in < 2 min (ours, not the brief)
├── DECISIONS.md  TICKETS.md   # written deliverables
├── SUBMISSION_QUESTIONS.md    # user-only
├── streaks_as_of_2026-11-15T1000IST.csv   # generated
├── brief/                     # assignment docs. Read-only
├── data/                      # input CSVs. Read-only. Seeded to S3
├── streaks/                   # Python package
│   ├── rules.py               # ALL rule constants (one place to change)
│   ├── engine.py              # pure: events → days → streak. No IO
│   ├── store.py               # Postgres read/write
│   ├── storage.py             # S3 (Floci) read/write
│   ├── ingest.py              # CSV/S3 → Postgres, dedupe
│   ├── api.py                 # FastAPI routes
│   └── support_view.py        # HTML table
├── sql/schema.sql             # tables + unique keys
├── scripts/                   # seed_s3, load, export_csv
├── 
… [trimmed 16922 chars]
````
</details>

**Tool call: `Bash`**

<details><summary>Input</summary>

````
{
  "command": "cd /Users/gyankumar/Personal/jumpp_streak_test; cat brief/incident_2026-11-09.md; cat data/users.csv; grep -E \"u07|u15|u09\" data/events.csv | grep -vE \"video_start\" | head -80; grep -E \"freeze|tz_change\" data/events.csv",
  "description": "Read incident report, users and key events"
}
````
</details>

<details><summary>Tool result</summary>

````
# Incident 2026-11-09 — event ingestion 503s

**Window:** 2026-11-09 20:45 → 21:50 IST (15:15 → 16:20 UTC)
**Impact:** `POST /v1/events` returned 503 for all requests. App **3.2.0 does not retry on 503** (fixed in 3.2.1, rolling out). Events sent in the window are **lost**; users could still watch cached videos.
**Estimated affected users:** ~18,400 (any user with a 503 in the LB log).

Load balancer log sample (user_id extracted from JWT):

```
2026-11-09T15:31:12Z POST /v1/events 503 uid=u31877 ua=Jumpp/3.2.0
2026-11-09T15:34:40Z POST /v1/events 503 uid=u08 ua=Jumpp/3.2.0
2026-11-09T15:34:41Z POST /v1/events 503 uid=u08 ua=Jumpp/3.2.0
2026-11-09T15:37:03Z POST /v1/events 503 uid=u08 ua=Jumpp/3.2.0
2026-11-09T15:52:19Z POST /v1/events 503 uid=u55120 ua=Jumpp/3.2.0
2026-11-09T16:02:51Z POST /v1/events 503 uid=u12 ua=Jumpp/3.2.0
```
Full list of affected uids is available as `affected_uids` table (you may assume it exists and contains exactly the uids that appear in the full log).
user_id,name,signup_at,home_tz,plan,freeze_balance,streak_as_of_2026_10_31
u01,Priya S,2026-10-20T09:00:00+05:30,Asia/Kolkata,free,0,0
u02,Rahul M,2026-08-02T09:00:00+05:30,Asia/Kolkata,premium,1,41
u03,Ananya K,2026-09-01T09:00:00+05:30,Asia/Kolkata,free,0,12
u04,Vikram R,2026-09-15T09:00:00+05:30,Asia/Kolkata,free,0,20
u05,Meera J,2026-10-01T09:00:00+05:30,Asia/Kolkata,free,0,6
u06,Karthik N,2026-09-20T09:00:00+05:30,Asia/Kolkata,free,0,33
u07,Sneha P,2026-07-10T09:00:00+05:30,Asia/Kolkata,premium,0,58
u08,Arjun D,2025-12-01T09:00:00+05:30,Asia/Kolkata,premium,1,300
u09,Divya T,2026-11-13T23:50:00+05:30,Asia/Kolkata,free,0,0
u10,Rohan B,2026-10-05T09:00:00+05:30,Asia/Kolkata,free,0,9
u11,Farah Q,2026-10-11T09:00:00+05:30,Asia/Kolkata,free,0,3
u12,Imran H,2026-10-02T09:00:00+05:30,Asia/Kolkata,free,0,15
u13,Nikhil V,2026-06-14T09:00:00+05:30,Asia/Kolkata,free,0,44
u14,Tanvi R,2026-05-02T09:00:00+05:30,Asia/Kolkata,free,0,51
u15,Ishaan G,2026-08-20T09:00:00-07:00,America/Los_Angeles,premium,1,17
e_f05eeefe8ece,u07,app_open,,,2026-11-01T07:12:00+05:30,Asia/Kolkata,2026-11-01T01:42:01Z,3.2.0,queue_depth=0
e_79474bfacdd0,u07,video_end,v024,81,2026-11-01T07:13:26+05:30,Asia/Kolkata,2026-11-01T01:43:26Z,3.2.0,
e_23c8afdb83f8,u07,app_open,,,2026-11-02T07:16:00+05:30,Asia/Kolkata,2026-11-02T01:46:01Z,3.2.0,queue_depth=0
e_88476c56827c,u07,video_end,v021,106,2026-11-02T07:17:52+05:30,Asia/Kolkata,2026-11-02T01:47:53Z,3.2.0,
e_c626e38f716f,u15,app_open,,,2026-11-01T20:07:00-08:00,America/Los_Angeles,2026-11-02T04:07:00Z,3.2.0,queue_depth=0
e_7c059799bdae,u15,video_end,v021,108,2026-11-01T20:08:54-08:00,America/Los_Angeles,2026-11-02T04:08:54Z,3.2.0,
e_044251dbd0d4,u07,app_open,,,2026-11-03T07:15:00+05:30,Asia/Kolkata,2026-11-03T01:45:01Z,3.2.0,queue_depth=0
e_797ebe8798cf,u07,video_end,v024,80,2026-11-03T07:16:27+05:30,Asia/Kolkata,2026-11-03T01:46:29Z,3.2.0,
e_83e8b7000e63,u15,app_open,,,2026-11-02T20:24:00-08:00,America/Los_Angeles,2026-11-03T04:24:01Z,3
… [trimmed 6436 chars]
````
</details>

**Tool call: `Bash`**

<details><summary>Input</summary>

````
{
  "command": "cd /Users/gyankumar/Personal/jumpp_streak_test; python3 - <<'E'\nimport csv,collections\nr=list(csv.DictReader(open('data/events.csv')))\nc=collections.Counter(x['event_id'] for x in r)\nfor x in r:\n  if c[x['event_id']]>1: print('ID',x)\nk=collections.defaultdict(list)\nfor x in r: k[(x['user_id'],x['event_type'],x['video_id'],x['client_ts'])].append(x)\nfor v in k.values():\n  if len({y['event_id'] for y in v})>1:\n    for y in v: print('K2',y)\nE\ngrep -E \"^[^,]*,u1[234],\" data/events.csv | grep -E \"2026-11-(09|11|12)\" ; grep queue_depth=[1-9] data/events.csv; grep u11 data/events.csv | grep 11-1[01]",
  "description": "Inspect duplicates and key user events"
}
````
</details>

<details><summary>Tool result</summary>

````
ID {'event_id': 'e_48603b32b4fb', 'user_id': 'u03', 'event_type': 'video_start', 'video_id': 'v019', 'watched_s': '', 'client_ts': '2026-11-10T14:05:05+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:00Z', 'app_version': '3.1.4', 'meta': ''}
ID {'event_id': 'e_48603b32b4fb', 'user_id': 'u03', 'event_type': 'video_start', 'video_id': 'v019', 'watched_s': '', 'client_ts': '2026-11-10T14:05:05+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:00Z', 'app_version': '3.1.4', 'meta': ''}
ID {'event_id': 'e_784c2f299804', 'user_id': 'u03', 'event_type': 'app_open', 'video_id': '', 'watched_s': '', 'client_ts': '2026-11-10T14:05:00+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:00Z', 'app_version': '3.1.4', 'meta': ''}
ID {'event_id': 'e_784c2f299804', 'user_id': 'u03', 'event_type': 'app_open', 'video_id': '', 'watched_s': '', 'client_ts': '2026-11-10T14:05:00+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:00Z', 'app_version': '3.1.4', 'meta': ''}
ID {'event_id': 'e_aff8754d1238', 'user_id': 'u03', 'event_type': 'video_end', 'video_id': 'v019', 'watched_s': '165', 'client_ts': '2026-11-10T14:07:53+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:00Z', 'app_version': '3.1.4', 'meta': ''}
ID {'event_id': 'e_aff8754d1238', 'user_id': 'u03', 'event_type': 'video_end', 'video_id': 'v019', 'watched_s': '165', 'client_ts': '2026-11-10T14:07:53+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:00Z', 'app_version': '3.1.4', 'meta': ''}
K2 {'event_id': 'e_48603b32b4fb', 'user_id': 'u03', 'event_type': 'video_start', 'video_id': 'v019', 'watched_s': '', 'client_ts': '2026-11-10T14:05:05+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:00Z', 'app_version': '3.1.4', 'meta': ''}
K2 {'event_id': 'e_48603b32b4fb', 'user_id': 'u03', 'event_type': 'video_start', 'video_id': 'v019', 'watched_s': '', 'client_ts': '2026-11-10T14:05:05+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:00Z', 'app_version': '3.1.4', 'meta': ''}
K2 {'event_id': 'e_c9af18f843b9', 'user_id': 'u03', 'event_type': 'video_start', 'video_id': 'v019', 'watched_s': '', 'client_ts': '2026-11-10T14:05:05+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:40Z', 'app_version': '3.1.4', 'meta': ''}
K2 {'event_id': 'e_aff8754d1238', 'user_id': 'u03', 'event_type': 'video_end', 'video_id': 'v019', 'watched_s': '165', 'client_ts': '2026-11-10T14:07:53+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:00Z', 'app_version': '3.1.4', 'meta': ''}
K2 {'event_id': 'e_aff8754d1238', 'user_id': 'u03', 'event_type': 'video_end', 'video_id': 'v019', 'watched_s': '165', 'client_ts': '2026-11-10T14:07:53+05:30', 'device_tz': 'Asia/Kolkata', 'received_at': '2026-11-11T04:10:00Z', 'app_version': '3.1.4', 'meta': ''}
K2 {'event_id': 'e_a9434aa096fc', 'user_id': 'u03', 'event_type': 'video_end', 'video_id': 'v019', 'watche
… [trimmed 3522 chars]
````
</details>

**Tool call: `SubagentHandback`**

<details><summary>Input</summary>

````
{
  "message": "Open questions, most important first:\n\n1. **What does `as_of` mean for events received after it?** Should the engine ignore events whose `received_at > as_of`, giving a view of what we knew at that time? Or does `as_of` only set \"today\" and the pending window? And should the API really default `as_of` to the real now (26 Nov or later)? If it does, a grader who leaves `as_of` out sees every user break with `NO_ACTIVITY` from 15 Nov on. The answer changes the engine's input filter, the u07 refund test, how grader replays behave, and possibly the default (fixed 15 Nov 10:00 IST instead of the real now).\n\n2. **Is the `queue_depth > 0` freeze rule built into the engine?** §3.8 says \"for DECISIONS, not code\", but it decides when a freeze is used, and the engine owns that. If the engine skips it, DECISIONS states a rule the engine doesn't produce, which the spec lists as an anti-goal. If it's built in, the engine needs a third \"held\" state beside `PENDING` and a definition of which `app_open` counts as the last one (as of `as_of`, or as of the end of that day?).\n\n3. **When can a freeze be spent?** \"Oldest miss first\" leaves three things open:\n   - Can a purchase cover a miss that happened before it was bought? u07 suggests yes.\n   - Is a freeze spent when the streak is already 0?\n   - When a late sync refunds a freeze, does it move to the next final miss?\n   Each answer changes freeze counts, so it changes the support view's \"Refund ₹49\" actions and grader scenarios for u02, u08 and u15 (balance 1 each).\n\n4. **Which status wins when several apply?** For example: today is learned but an earlier day is still pending; or the streak is 0 with no break, as for new users (u01 before 3 Nov). Is that `AT_RISK` or `BROKEN`? The status column of the graded CSV depends on this order.\n\n5. **Which timezone defines a day with no events?** Day end (for `PENDING`), \"today\", outage overlap and short-day detection all need a timezone for each date. Should it come from the latest `tz_change` or the latest event's `device_tz`? Grader travel events would land differently depending on the answer.\n\n6. **Which copy of a resend survives?** The 3.1.x resends have a different `received_at` from their originals (40s apart in the data). `ON CONFLICT DO NOTHING` keeps whichever copy arrived first. That can change late-sync and too-late results depending on arrival order, which breaks the order-independence goal. Should the stored copy be the one with the earliest `received_at` (an upsert, which goes against AGENTS.md)?\n\n7. **How does `POST /events` handle a batch with some bad items?** The spec gives both `{inserted, duplicate, invalid}` counts and \"422 for bad input\". Does one bad item (bad fields, unknown user) reject the whole batch with 422, or is it counted as invalid while the rest go in? Graders hit this endpoint directly."
}
````
</details>

<details><summary>Tool result</summary>

````
{"success":true,"message":"Report delivered to your caller."}
````
</details>
