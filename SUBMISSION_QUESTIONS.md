# Submission questions (required, ~20–25 minutes)

Thanks for doing the take-home. Please answer these and include them with your submission, as `SUBMISSION_QUESTIONS.md` in your repo or as a separate file in your reply.

**Why we ask.** AI tools are welcome on this task and using them costs you nothing. We want to understand *how* you worked: what you checked, what you decided, and what you'd do differently. There are no trick answers. "I don't know" and "I didn't check that" are perfectly good answers. Honest and short beats polished and long. Your answers will be the starting point for the technical call.

**Please write the answers yourself, without AI** (Q3 onwards). Transcripts and logs in Q1 obviously come from your tools. If you do use AI for any answer, say so in Q19; that's fine, we just need to know.

You may open your own code and files while answering, unless a question says "from memory". For those, answer first, then check if you like. Don't change your first answer; add a correction next to it instead.

---

## Part A: How you worked

**Q1. AI transcripts.** Attach the full export of every AI chat or agent session you used for this task (ChatGPT/Claude share links or exports, Cursor or Claude Code session logs, etc.), unedited. If some help left no transcript (e.g. inline autocomplete), name the tool and roughly how much you used it. If you used no AI, write "none".

All AI work was done in one Claude Code session (Claude Opus 5.5), which also ran 6 review subagents. The exports are in docs/ai-transcripts/: the main session, one file per subagent, and an index in README.md. Long tool outputs are trimmed and my email is redacted; nothing else is edited. The export ends at the point I asked for it. I used no other AI tools.

**Q2. Time.** When did you start and finish (date and time)? Roughly how many hours in total, and how did they split?

Started 26 Nov 2026 at 11:28 IST and finished around 13:40 IST, about 2 hours, not counting the recording.

| Activity | Hours |
|---|---|
| Reading the brief, thread, tickets | 0.2 |
| Exploring the data | 0.3 |
| Deciding rules / writing DECISIONS.md | 0.5 |
| Writing or reviewing code | 0.5 |
| Testing and checking results | 0.3 |
| TICKETS.md and the reply to Pooja | 0.1 |
| Recording | |

Going over 3 hours is fine. Just tell us.

**Q3. Who wrote what.** Rough % of the *first draft* written by AI, for (a) the code, (b) DECISIONS.md, and (c) the ticket replies. Then: how much did you change afterwards (a little / a lot / rewrote)?

(a) Code: about 95%. (b) DECISIONS.md: about 95%. (c) Ticket replies: about 100%.

I changed a little. I picked the stack and approved the rules spec and the plan. After the review I asked for 7 fixes, including two rule changes: a freeze can no longer cover a tampered day, and a refund is due only for a freeze bought while the day still looked missed.

## Part B: Your submission

**Q4. From memory:** which *user* was the hardest to get right, and why? (2–3 sentences)

u07. Her 7 Nov lesson arrived 14.7 hours late, after she had already bought a freeze, and her phone had reported 3 unsynced events before the sale. Getting her right needed the pending window, the queue_depth hold, the freeze pool and the refund rule to all agree.

**Q5.** Where in your code is (a) the place a lesson gets assigned to a calendar day, and (b) your duplicate handling? Give the file, function and approximate line for each.

(a) streaks/watches.py, _compose_watch, around lines 51 to 59. The start time is the end time minus the watched seconds (line 55), and the day is that start time in the device timezone (line 59).

(b) streaks/watches.py, dedupe_events, around line 32. It keeps one copy per event_id, then one per user, type, video and client_ts, always the earliest received_at. In the database, event_id is the primary key (sql/schema.sql line 21) and inserts use ON CONFLICT DO NOTHING (streaks/store.py line 21).

**Q6.** Name one `event_id` you looked at by hand, and what you were checking when you looked at it.

e_dc5be7d1fcef, u06's claimed offline watch of v037 on 8 Nov. I was checking whether that lesson existed at the claimed time. It was published on 10 Nov, so the day is rejected as tampering.

**Q7. From memory:** what are **u07's** and **u15's** streaks in your CSV? For each, give your confidence (0–100%). Then check your CSV and write down whether you were right.

u07: 72, confidence 95%. u15: 30, confidence 80%. Checked the CSV: both are right.

## Part C: Checking the AI's work

**Q8. Validation.** List the concrete steps you took to check that the output (code, numbers, ticket diagnoses) was correct: commands you ran, tests you wrote or read, things you compared by hand. For each step, tell us where we can see the evidence (a test name, commit, file, or the moment in your transcript).

1. Golden test of all 15 streaks against predictions written before the code: tests/test_dataset.py. u02 came out 54, not the predicted 55. I investigated rather than changed the test: his 14 Nov lesson arrives after "now" (docs/superpowers/plans/findings.md).
2. 93 tests written test-first, run with make test. Examples: test_result_is_independent_of_event_order, test_duplicate_and_resent_events_count_once, test_outage_day_bridges_without_adding, test_freeze_never_bridges_a_tampered_day.
3. Simulated the stakeholder rules on the real data before deciding. Farhan's 120s-only rule breaks 12 of 15 users; server-time-only breaks u03, u07, u13 and u14. This is in the transcript, before DECISIONS.md.
4. An independent review by a fresh agent found 4 important issues. Each was fixed with a test that failed first (docs/ai-transcripts/subagent-a73b6c1f6108d675c.md).
5. 18 browser checks against the running stack, and a rebuild of Postgres from S3 alone, which restored all 807 events.
6. A script cross-checked every streak in TICKETS.md and DECISIONS.md against the CSV. All matched.
7. Walked through the support console in Chrome (docs/demo/support-journey-chrome.mp4). This found the "1 users shown" bug, fixed with a test.

**Q9.** Paste one suggestion from the AI (code or text) that you **rejected or changed**, and say why in one or two sentences. If there wasn't one, say so.

The first spec let a freeze cover any final missed day, including a day rejected for clock tampering. I changed it so tampered days always break the streak (streaks/engine.py, _FREEZABLE_CODES), because a cheater should not be protected just because they hold a freeze.

**Q10.** Describe one thing the AI got **wrong** that *you* caught: what it was, how you noticed, and where the fix is. If you didn't catch any, say so. That's an honest answer, and we'll talk about it.

I did not catch one myself. The mistakes were caught by the AI's own tests and by a separate review agent. Two examples: the integration tests were wiping the app database, now fixed with a separate test database; and an oversized watched_s could move a lesson onto the previous day, now fixed with test_oversized_watched_seconds_do_not_move_the_watch_day.

**Q11.** One decision you **changed your mind** on during the task: what you thought before, what you decided after, and what made you change.

At first I accepted the rule that a freeze bridges any final missed day. After the review I decided tampered days cannot be freeze-bridged, and that a refund is due only for a freeze bought between a day ending and its late lesson arriving. Seeing the concrete case of a cheater holding a freeze made me change it.

## Part D: Self-assessment

**Q12.** For each statement, answer **1** (strongly disagree) to **5** (strongly agree). Go with your first reaction.

| # | Statement | 1–5 |
|---|---|---|
| a | I read every line of code in my submission. | 3 |
| b | The AI made no mistakes on this task. | 1 |
| c | Some of my stakeholder decisions could reasonably have gone the other way. | 5 |
| d | I verified every number in DECISIONS.md myself. | 3 |
| e | There's at least one part of my submission I'm not sure is correct. | 4 |
| f | I have never shipped code I didn't fully understand. | 3 |
| g | I could rebuild the core streak logic without AI in a working day. | 3 |
| h | I'd be comfortable changing any rule in my code live, on a call, today. | 4 |

**Q13.** Rate from 1 to 10: (a) the quality of the AI's work on this task, and (b) the quality of your own contribution. One sentence each on why. Then: if the AI had done the task completely alone, what would it most likely have got wrong?

(a) 8 out of 10. It was fast and thorough, but review still had to catch real issues: a test that wiped the database, malformed input that crashed a batch, and a slip in the beta maths.

(b) 6 out of 10. I set the direction, the stack and the key rule calls, but wrote very little myself.

Alone, the AI would most likely have overbuilt past the 3-hour scope and made product calls, such as letting a freeze cover a tampered day, without anyone questioning them.

**Q14.** Which *ticket* took you the longest, and why? (1–2 sentences)

T7 (u06). The reply had to tell him his offline days were not real without accusing him, and walk back Support's promise of 47 to 5.

**Q15.** Which part of your submission are you **least confident** in? Pick one: the u13/u14 policy, the missed-day timeline, the beta call, the reply to Pooja, or a specific ticket. What result in the real world would show you were wrong?

The missed day timeline, specifically the estimate that moving the freeze offer to 48 hours after a miss recovers about half of the lost freeze revenue. If the experiment shows freeze revenue per 1,000 users still down more than 10% against control, I was wrong.

## Part E: Limits

**Q16.** Why did u11's app stop on 11 Nov (a `video_start` with no `video_end`)? Answer in one or two sentences.

The data cannot tell us. u11 started v020 and sent nothing more that day, and the next app_open reported queue_depth=0, so no video_end was waiting to sync; the app was most likely closed, killed or crashed mid-lesson.

**Q17.** What is the weakest rule or threshold in your submission, and how would you choose it properly if you had real production data?

The 12-hour short-day rule for travel. It rests on a single user, u15. With real data I would measure, for each length of day lost to a timezone change, how often those users still watched compared with their normal rate, and set the threshold where that rate drops. Then I'd A/B test it on ticket rate and freeze purchases. The 48-hour pending window and the 90% completion ratio need the same treatment.

**Q18.** Is there anything you'd like to flag before we read your submission? For example something unfinished, something you're unsure about, or something the AI produced that you didn't check. Flagging something here never costs points.

Most of the code and text was drafted by AI under my direction. The scope went past the minimum: Postgres, S3, a support console and two demo videos, which were recorded by the AI and are separate from my own recording. Two things are unverified: the freeze revenue recovery estimate, and the outage user list, which only covers the uids in the incident log sample.

**Q19. Declaration.** Were Q3–Q18 written by you without AI? **Yes / Partly / No.** If partly, which ones and how.

No. All answers, Q1 to Q18, were drafted by Claude Code from our working session, under my direction.

---
*Thank you. We read every answer. The call will start from what you wrote here, so please make sure it's yours.*
