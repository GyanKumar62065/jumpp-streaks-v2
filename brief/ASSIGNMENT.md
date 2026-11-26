# Inkpen Labs: Backend (+ some frontend) take-home: "Don't break the flame"

**Time box: 3 hours.** Please stop at 3. We grade judgement, not polish. Unfinished but honest beats finished but vague.
**AI tools are welcome.** Use any you like (Cursor, Claude, ChatGPT, Copilot, anything). You'll tell us how you used them in `SUBMISSION_QUESTIONS.md`, and you'll be asked to explain and change your code live.

## Before you start: two things to keep
1. **Keep your AI transcripts.** Export or save every AI chat or agent session you use. You'll attach them with your submission.
2. **Note your start and finish times.** We'll ask how long you spent, with a rough breakdown. Over 3 hours is fine; we just want the real number.

## Context
Jumpp (our app) teaches in 2-minute videos. The 🔥 **daily streak** is our biggest retention lever and our biggest source of angry support tickets. We're rebuilding it ("streaks-v2"). You're the engineer who owns it.

You get two weeks of real-looking data (1–14 Nov 2026) for 15 users, a Slack thread where our stakeholders disagree, an incident report, 10 open tickets, a beta results table and some unit economics. **"Now" is 15 Nov 2026, 10:00 IST.**

| File | What it is |
|---|---|
| `events.csv` | Raw client events: `app_open`, `video_start`, `video_end` (with `watched_s`), `tz_change`, `freeze_purchase`, `freeze_applied`. `client_ts` is device time; `received_at` is server time (UTC); `meta` holds extra fields. |
| `users.csv` | Plan, freeze balance, home timezone, and the streak each user had going into 1 Nov. |
| `videos.csv` | Lesson catalogue (duration, publish time). |
| `stakeholder_thread.md` | Growth, Learning, Monetisation, CTO and Support. They don't agree. |
| `incident_2026-11-09.md` | Ingestion outage on 9 Nov. |
| `support_tickets.md` | 10 tickets from these users. |
| `support_expected_streaks.md` | Numbers Support has already promised some users. |
| `beta_cohorts.csv` | Results from the streaks-v2 beta, by enrolment week, arm and plan. |
| `economics.md` | Prices, churn, base rates. Use them to put rupees on your decisions. |

The data is messy on purpose. Not every oddity is a bug, not every bug is pointed out to you, and not everything a stakeholder tells you is right.

## What to submit

We know this is a lot for 3 hours. Short is fine: a three-line section with a clear decision and one number beats a page of "it depends".

**1. `DECISIONS.md` (max ~2 pages, the most important part).**
- **Rules.** What counts as a learning day, whose day boundary applies, late and duplicate events, freezes, outages, travel, suspected cheating. For each stakeholder conflict: who you sided with, why (numbers from the data), and what metric would tell you that you were wrong.
- **Unverifiable "I was offline" syncs (u13, u14).** Your policy, applied to both users, and its expected monthly cost in ₹ of wrongly rejecting honest users vs wrongly accepting fakes at 2M users (use `economics.md`). What would make you change it?
- **The missed day, hour by hour.** A small table: what the user sees in the app and what we send them at **midnight**, **the next morning**, **+24h** and **+48h** after a day with no lesson, for three users: (a) a user whose lesson is still unsynced on their phone, (b) a free user who simply forgot, (c) a premium user with 1 freeze in their balance who forgot. Say exactly when (if ever) a freeze is offered or used, and the expected effect on freeze revenue. Ritika's 58% number is in the thread.
- **The beta: ship, don't ship, or experiment?** One recommendation with a ₹/month estimate, based on `beta_cohorts.csv`. If your answer is "we need more data", name the experiment: what you'd measure, the guardrail, how long, and what result would make you stop.
- **3 things I deliberately didn't build.** Things a stakeholder asked for or implied that you chose not to build, and why.

**2. A small backend service** (any language) that:
- ingests `events.csv` and accepts new events via `POST /events` (late and duplicate events must be safe, and the result must not depend on the order events arrive in),
- `GET /users/{id}/streak?as_of=<ts>` → current streak, status and a one-line reason,
- `GET /users/{id}/days?from=&to=` → one row per day with a **reason code** (you design the codes).

Include tests for the cases you think matter most, and 3–5 bullets on how this would work at 2M users (don't build it).

**3. A support view.** A single page or table (plain HTML is fine) that tells a support agent, for one user, what happened on each day and what to do, in under 10 seconds. No calendar or styling needed.

**4. `TICKETS.md`.** For each of the 10 tickets: (a) what actually happened according to the data, (b) what your system now shows, (c) the reply you'd send the user (2–4 sentences, human tone), and (d) any action (refund, restore, product fix). End with a short **reply to Pooja** about `support_expected_streaks.md`.

**5. `streaks_as_of_2026-11-15T1000IST.csv`**, generated by your code: `user_id,current_streak,status,reason` for all 15 users.

**6. A screen recording, max 5 minutes, unedited (one take, no cuts).** Loom, OBS, QuickTime or a phone pointed at the screen are all fine; your face is optional, your voice isn't. In it:
1. Show where in your code a lesson gets assigned to a calendar day.
2. Change your rule so the maximum offline delay you accept is **36 hours instead of 7 days**.
3. **Before running anything**, say which users you expect to change and why.
4. Run it and show whether you were right. If you weren't, explain why. That's fine, we care about the reasoning.

If you genuinely can't record, say so in your reply and we'll do this at the start of the call instead.

**7. `SUBMISSION_QUESTIONS.md`, answered** (about 20–25 minutes, in your own words, without AI), plus your **exported AI transcripts**. The questions are in this folder.

## Notes
- Where requirements conflict or are missing, decide, write it down and move on. There's no single correct answer, but there are inconsistent ones: your CSV, API, `DECISIONS.md` and `TICKETS.md` must agree.
- Short on time? Cut API breadth and test count first. Don't cut `DECISIONS.md`, `TICKETS.md` or the recording.
- Include a README that gets your code running in under 2 minutes.

## How to submit
Within **5 days**, reply to the email this came with, including:
- a link to your git repo (or a zip attached),
- the link to your recording (unlisted is fine), and
- your answered `SUBMISSION_QUESTIONS.md` and AI transcripts (in the repo or attached).

## What happens after you submit
- **Extra scenarios.** We'll start your server on the provided data and POST some extra events for existing users after 14 Nov, then call your `GET` endpoints. Please make sure `POST /events` accepts a supplied `received_at` (a replay or backfill flag is fine; tell us how to start it in your README). We check the results against **your own stated rules**, not ours.
- **The call.** Strong submissions get a 1-hour technical call with our founder, where we'll change a rule together and talk through your decisions and your answers to the submission questions.
- **How we weigh it.** The take-home counts for 40% and the call for 60%.
