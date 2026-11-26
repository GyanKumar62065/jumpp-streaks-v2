# TICKETS

Streaks are as of **15 Nov 2026, 10:00 IST**, from `streaks_as_of_2026-11-15T1000IST.csv`. Day codes come from `GET /users/{id}/days` (and `/support/{id}`).

---

## T1 · u02 Rahul (premium): "Moved to SF, never missed, 48-day streak reset"
- **What happened:**
  - `tz_change` IST → LA on 7 Nov, 22:10 PST. He learned every day *in his local time*.
  - The old system counted days in IST, so his evening LA lessons looked like a missed 8 Nov. Streak 48 (41 + 7) was reset.
- **What v2 shows:** **54**, `AT_RISK`.
  - 1–13 Nov are `LEARNED` on LA days.
  - At 10:00 IST it's 14 Nov 20:30 in SF, so 14 Nov is `TODAY_OPEN`.
  - His 14 Nov lesson arrived at 10:32 IST, which makes it **55**.
- **Reply:** "Hi Rahul, sorry about this. Our old streak counted days on India time, so your evenings in San Francisco looked like missed days. The new streak follows your local time, and you haven't missed a single day: your streak is back, at 55 including last night's lesson."
- **Action:** restore (automatic in v2). Product fix: local-day boundary.

## T2 · u03 Ananya: "Got 'you lost your streak' but I watched on the flight"
- **What happened:**
  - On 10 Nov she watched v019 offline at 14:05. It synced on 11 Nov at 09:40 (19.5h late), after the morning "lost" push.
  - App 3.1.4 also resent the batch: 2 copies with the same id plus 1 with a new id, all deduped.
  - 12 Nov also synced late (37.7h).
- **What v2 shows:** **26**, `AT_RISK`. 10 and 12 Nov are `LEARNED_LATE_SYNC`.
- **Reply:** "Hi Ananya, you did nothing wrong. Your flight lesson reached us the next morning, just after our app wrongly told you the streak was lost. It counted, and your streak is 26. We're removing that early message, so a lesson still syncing won't trigger it again."
- **Action:** none for her (and suggest updating to 3.2.x). Product fix: `PENDING` for 48h, no "lost" push.

## T3 · u04 Vikram (beta): "I open the app EVERY night. Why does it say I'm not learning?"
- **What happened:**
  - Since 6 Nov he opens about 8 lessons a night and watches 2–6s of each, about 34s in total.
  - 1–5 Nov counted (75–162s a day).
- **What v2 shows:** **0**, `BROKEN`.
  - 6–12 Nov are `BELOW_THRESHOLD`; the reset is on 6 Nov.
  - 13–14 Nov are `PENDING`, but also below the rule.
- **Reply:** "Hi Vikram, thanks for testing streaks-v2, and sorry it felt insulting; that's not the intent. A day counts when you watch 2 minutes in total, or finish one lesson. Since 6 Nov your sessions have been about 30 seconds across several lessons, so they don't count yet. Finish any one lesson tonight and your new streak starts."
- **Action:** no restore. Product fix: an in-app progress hint ("45s of 2 min").

## T4 · u05 Meera: "I watched on 9th night before 12"
- **What happened:** v010 started at **23:59:05 on 9 Nov** and finished at 00:00:27 on 10 Nov. The old system used the end time, so the lesson landed on 10 Nov and 9 Nov looked missed.
- **What v2 shows:** **20**, `AT_RISK`. 9 Nov is `LEARNED`, counted by its start time.
- **Reply:** "Hi Meera, you're right: you started that lesson at 11:59 PM on the 9th. We now count a lesson on the day you start it, so the 9th counts, and your streak is 20."
- **Action:** restore (automatic). Product fix: assign a lesson to the day it started.

## T5 · u07 Sneha (premium): "Bought a ₹49 freeze, but I did watch yesterday"
- **What happened:**
  - She watched v013 offline on 7 Nov at 21:15. At 07:17 on 8 Nov her phone reported **`queue_depth=3`** (unsynced events).
  - We still sold her a freeze at 09:02 (order GPA.3391-2271-8812). The lesson synced at 12:00, 14.7h late.
- **What v2 shows:**
  - **72**, `AT_RISK`. 7 Nov is `LEARNED_LATE_SYNC`.
  - The freeze was **not used**, and the support page shows **Refund ₹49**.
- **Reply:** "Hi Sneha, you're right, and we're sorry. Your lesson from the metro reached us a few hours after we sold you the freeze. Your streak is 72 without it, and we've refunded the ₹49 to your original payment method."
- **Action:** **refund ₹49.** Product fix: no freeze offer while a day is pending or `queue_depth > 0`.

## T6 · u08 Arjun (premium): "300+ days gone. Watched at 9 PM, will cancel"
- **What happened:**
  - The LB log shows his POSTs returning 503 at 21:04–21:07 IST on 9 Nov. That was our outage, and 3.2.0 doesn't retry, so the lesson was lost.
  - There are no 9 Nov events from him at all.
- **What v2 shows:** **313**, `AT_RISK`. 9 Nov is `PROTECTED_OUTAGE`, which bridges the streak but doesn't add a day.
- **Reply:** "Hi Arjun, this one is on us. Our servers were down for an hour on the 9th and your 9 PM lesson never reached us. We've protected that day, so your streak is intact at 313. As an apology we've added a free Streak Freeze to your account."
- **Action:**
  - Restore (automatic).
  - **Grant 1 freeze** as goodwill: ₹49, against the 12% premium churn risk × ₹1,600 ≈ ₹192.
  - Product fix: retry on 503 in 3.2.1.

## T7 · u06 Karthik: "Was offline 8th and 9th, please fix after sync"
- **What happened:**
  - Both "offline" days claim **v037** at 20:08 on 8 Nov and 20:11 on 9 Nov. Both synced on 10 Nov.
  - **v037 was published on 10 Nov at 06:00.** It couldn't have been watched on the 8th or the 9th: the device clock was wrong.
- **What v2 shows:** **5**, `AT_RISK`. 8 and 9 Nov are `REJECTED_TAMPER`. 10–14 Nov count.
- **Reply:** "Hi Karthik, we checked carefully. The lessons recorded for the 8th and 9th were only released on the 10th, so your phone's date must have been off when they were saved, and we can't count those two days. Your new streak is at 5 and growing. If you think something else went wrong, reply and we'll look again."
- **Action:** no restore. Flag to T&S. Don't accuse in the reply.

## T8 · u10 Rohan: "Finished my lesson on the 12th. Why is it grey?"
- **What happened:** v003, 101s of a 104s lesson (97%). The old 2-minute-only rule greyed it out.
- **What v2 shows:** **23**, `AT_RISK`. 12 Nov is `LEARNED`, because he finished the lesson.
- **Reply:** "Hi Rohan, you did finish it. The lesson is only 1:44 long, and our old rule wanted 2 full minutes. Finishing a lesson now always counts, so the 12th is lit and your streak is 23."
- **Action:** restore (automatic). Product fix: the completion rule.

## T9 · u13 Nikhil: "Power cut, watched offline on the 12th"
- **What happened:**
  - v019 claimed at 20:56 on 12 Nov. It arrived on 13 Nov at 21:02 (24.1h late), in one batch, right after an `app_open` with `queue_depth=3` (3.2.0).
  - The claim can't be verified either way.
- **What v2 shows:** **58**, `AT_RISK`. 12 Nov is `LEARNED_LATE_SYNC` (accepted and flagged).
- **Reply:** "Hi Nikhil, your offline lesson from the 12th reached us when you reconnected and it counts. Your streak is safe at 58. Sorry about the power cut!"
- **Action:** none. It's logged in the flagged-late-sync review set (DECISIONS §2).

## T10 · u14 Tanvi: "On the train to Patna on the 11th"
- **What happened:** v001 claimed at 21:31 on 11 Nov. It arrived on 12 Nov at 21:24 (23.8h late), the same pattern as T9 (`queue_depth=3`, single batch).
- **What v2 shows:** **65**, `AT_RISK`. 11 Nov is `LEARNED_LATE_SYNC` (accepted and flagged).
- **Reply:** "Hi Tanvi, your train lesson synced the next evening and it counts. Your streak is 65, nothing lost. Safe travels!"
- **Action:** none. It's logged in the flagged review set.

---

## Reply to Pooja (re `support_expected_streaks.md`)

Hi Pooja, thanks for listing these. Two of your five numbers match; three don't, and I'd rather fix our replies than bend the rules (the CSV has to match what the app shows).

| Ticket | Promised | v2 | Why |
|---|---|---|---|
| T1 u02 | 55 | **54 → 55** | 54 at 10:00 IST, because 14 Nov wasn't over yet in SF. His lesson synced at 10:32, so **55 is fine to send now** |
| T2 u03 | 26 | **26** ✓ | — |
| T5 u07 | 72 | **72** ✓ | Also **refund her ₹49**: the freeze wasn't needed |
| T6 u08 | 314 | **313** | Protected days keep the streak alive but **don't add a day**, the same rule as a freeze (our Play Store listing) |
| T7 u06 | 47 | **5** | The "offline" lessons on the 8th and 9th were released on the 10th, so the device clock was wrong. Please send the T7 reply above, not 47 |

- **For T6:** "313, protected, plus a free freeze" keeps him whole.
- **For T7:** sorry, this one does mean walking back a promise.
- **Going forward:** before quoting a number, open `/support/{user_id}`. It shows each day's code, what happened and what to do, in about 10 seconds.
