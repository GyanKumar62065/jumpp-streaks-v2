# #streaks-v2 (Slack export, lightly trimmed)

**Neha (Growth PM)** · Mon 10:02
Streaks are our #1 lever for D7 retention. Users who hit a 7-day streak retain 2.4x. Rule of thumb: if a user *did learn something* that day, the streak must survive. Never break a streak because of travel or anything that's our fault. When in doubt, be generous.

**Farhan (Head of Learning)** · Mon 10:15
Generous is fine, fake is not. A streak has to mean learning. I've seen people open 6 videos and swipe away in 3 seconds just to keep the flame. Our promise is "2 minutes a day" — so a day should count only with **at least 2 minutes of real watching**.

**Neha** · Mon 10:17
2 minutes total? Lots of our lessons are shorter than 2 min.

**Farhan** · Mon 10:19
Then they watch two. That's the point.

**Ritika (Monetisation)** · Mon 10:40
Reminder: Streak Freeze is ₹49 (premium gets 1 free/month in `freeze_balance`). It's ~11% of revenue this quarter. If we auto-forgive every missed day, nobody buys a freeze. Please don't give away for free what people are happily paying for.

**Neha** · Mon 10:42
Outage days are not "giving away", Ritika. That's on us.

**Ritika** · Mon 10:44
Agree on outages. Travel and "I forgot" — no.
Also, to be clear on how it works today (and what our Play Store listing says): a freeze keeps your streak alive, it doesn't add a day. Same for anything we forgive.

**Neha** · Mon 10:45
👍 Protected days bridge the streak; they don't count as a day.

**Sameer (CTO)** · Mon 11:05
Data notes:
- Client clocks lie. Some users set their phone clock back to fake streaks. **Trust server `received_at`, not `client_ts`.**
- Offline mode: the app queues events and sends them when back online, up to **7 days** late. App 3.1.x sometimes resends a batch on retry (and an older bug regenerated event_ids on retry — fixed in 3.2.0).
- Since 3.2.0, every `app_open` carries `queue_depth=N` in `meta`: the number of events still unsynced on the device at that moment. 3.1.x doesn't send it.
- 9 Nov outage: see `incident_2026-11-09.md`.
- At 2M users we can't recompute everyone's full history on every request. For this exercise keep it simple, but tell me how it would scale.
- FYI beta enrolment had a billing-SDK conflict in September (fixed in enrolment week 5). Shouldn't matter much.

**Neha** · Mon 11:08
Wait, if we use received_at, offline users lose their streaks. That's exactly the case I said must not happen.

**Sameer** · Mon 11:09
Then figure out which timestamps to trust when. 🙂

**Pooja (Support lead)** · Mon 11:30
"My streak broke" is 31% of all tickets. My agents can't see *why* anything happened. Whatever you build, I need a screen that tells an agent in 10 seconds what happened on each day and what we should do.

**Neha** · Mon 11:31
Also — users currently get a "😢 You lost your 23-day streak" push the morning after a miss. If that's wrong and the streak comes back later, that's the worst experience we have.

**Ritika** · Tue 09:10
Numbers from the streaks-v2 beta (it shows a "pending" state for 48h instead of "you missed", and sends no "lost your streak" push). Freeze purchases per 1,000 enrolled users are down **58%** vs control over the first four enrolment weeks. That's a big chunk of 11% of revenue walking out. Whatever we ship, I need to know exactly *when* a user gets offered a freeze.

**Neha** · Tue 09:14
And the week-1 beta cohort's D7 retention is up **4.7 points**. Ship it 🚀

**Farhan** · Tue 09:20
Not so fast. The full table is in `beta_cohorts.csv`, please actually look at it.
Separately: Trust & Safety flagged two more "I was offline" cases this week (u13, u14, tickets T9/T10). T&S looked at both and can't tell whether either is genuine. At 2M users we'll see thousands of these a day. I don't want us accepting fakes, and I don't want us calling honest people liars. Finance put the numbers in `economics.md`. Engineering: pick a policy and own it.

**Pooja** · Tue 09:40
Support needs final numbers to close tickets. I've listed what we already promised users in `support_expected_streaks.md`. Please make your CSV match so my team isn't contradicted.
