# DECISIONS: streaks-v2

"Now" = **15 Nov 2026, 10:00 IST**. Every number below comes from the engine (`make csv`, `/users/{id}/days`) or from `data/beta_cohorts.csv` and `brief/economics.md`. All rule values are in `streaks/rules.py`.

---

## 1. Rules

| Topic | Decision (What) | Why | How (code) |
|---|---|---|---|
| **Learning day** | ≥ **120s** watched that day, **or** one lesson watched to ≥ **90%** | "120s only" would break **12 of 15** users (u08: 313 → 2). Swiping still fails: u04 watches ~34s/day | `engine._is_learning_day` |
| **Whose day** | The user's **local** midnight, from the `device_tz` the phone reports | u02 flew to SF. On IST days their LA lessons looked like a missed 8 Nov | `timeline.get_day_spans` |
| **Which moment** | The day the lesson **started** (`end − watched_s`, capped at the lesson length) | u05 pressed play at 23:59:05 and finished at 00:00:27 | `watches._compose_watch` |
| **Clock trust** | Use `client_ts` unless: the lesson wasn't published yet, the clock is > 5 min ahead of the server, or the event arrived > **7 days** late | Server time alone breaks 4 honest offline users (u03, u07, u13, u14) | `watches._judge_watch` |
| **Late events** | Accepted up to 7 days. A late lesson re-opens its day (`LEARNED_LATE_SYNC`) | The app queues events for up to 7 days (Sameer) | `MAX_OFFLINE_DELAY_H` |
| **Duplicates** | Dedupe on `event_id`, then on (user, type, video, `client_ts`), keeping the **earliest** `received_at` | 3.1.x resends carry new ids (u03). Keeping the earliest copy means arrival order can't change a result | `watches.dedupe_events` |
| **Order** | Recompute from the full event set. `as_of` = only what we had received by then | The same events give the same answer, whatever order they arrived in | `engine.compute_streak` |
| **Pending** | A missed day is `PENDING` for **48h**, or up to 7 days while the phone reports `queue_depth > 0` | No "lost streak" message for a day that can still sync. u07 had `queue_depth=3` when we sold them a freeze | `engine._get_pending_deadline` |
| **Freezes** | Used automatically on a **final** miss, only if the streak is > 0, **never on a tampered day**. A late sync returns the freeze | Ritika: a freeze is a paid product. It must not cover cheating | `engine._apply_streak_and_freezes` |
| **Outage** | Affected uid with no lesson on 9 Nov → `PROTECTED_OUTAGE`. It **bridges the streak but doesn't add a day** | Our fault, so we protect it. "Bridge, don't add" is the Play Store rule for freezes too | `rules.OUTAGE_*`, `config/affected_uids.csv` |
| **Travel** | Correct local days. A day cut to **< 12h** by a timezone jump is `SKIPPED_TRAVEL` (bridge) | u15's LA 10 Nov lasted 10h40m before the jump to NZ | `MIN_DAY_LENGTH_H` |
| **Cheating** | Lesson "watched" before it was published → `REJECTED_TAMPER`. This breaks the streak, and no freeze can cover it | u06 "watched" v037 on 8 and 9 Nov; v037 came out on 10 Nov | `WatchVerdict.TAMPER_*` |

### Stakeholder conflicts
| Conflict | I sided with | Why (data) | I'm wrong if… |
|---|---|---|---|
| Farhan (2 min) vs Neha (short lessons) | **Both**: 120s **or** one lesson finished | 120s alone breaks 12/15 users. The completion rule still fails u04's swiping | Lesson completion rises while D30 learning (lessons per active day) falls |
| Sameer (server time) vs Neha (offline) | **Neha, within limits** | Server time alone breaks u03, u07, u13 and u14. The published-after check catches u06 | Tamper share in T&S audits goes above ~62% (§2 break-even) |
| Ritika (sell freezes) vs Neha (forgive) | **Ritika** on "forgot" and travel, **Neha** on outages | Only our own faults are forgiven. Travel is fixed by correct local days, not by forgiveness | Freeze purchases per 1k don't recover once the offer comes at +48h (§3) |
| Pooja (match my numbers) | **The rules** | 3 of 5 promises differ (see TICKETS) | — |

---

## 2. Unverifiable "I was offline" syncs (u13, u14)

**Policy: accept, then flag.** Both are coded `LEARNED_LATE_SYNC`.
- **u13:** the 12 Nov lesson arrived 24.1h late, in one batch, right after an `app_open` with `queue_depth=3` (app 3.2.0). Streak **58**.
- **u14:** the 11 Nov lesson arrived 23.8h late, same pattern. Streak **65**.
- **Why:** the late batch arrived with the queue signal Sameer described, and the lessons were published long before. Nothing contradicts their story.

**Cost at 2M MAU** (90,000 cases a month; 60% would break a 7+ streak; 10% are premium):

| | Fake share 11.5% (audited) | Fake share 25% (Farhan) |
|---|---|---|
| **Reject:** cost of honest users we call liars. ₹39.7 each = churn (0.9×16%×₹45 + 0.1×12%×₹1,600) + ticket (35%×₹40) | **₹19.0 L/month** | **₹16.1 L/month** |
| **Accept:** cost of fakes we let through. ₹14.8 each = lost freeze (20%×₹49) + integrity (₹5) | **₹1.5 L/month** | **₹3.3 L/month** |

- Accepting is **5 to 12 times cheaper**. The break-even fake share is **~62%**.
- **I'd change the policy if:**
  - audits show tampering above ~40% (a safety margin under 62%); or
  - one user claims more than 2 offline days in 30 (then cap it at 1 a month); or
  - fake days start reaching leaderboards or certificates.

---

## 3. The missed day, hour by hour

(a) = lesson still unsynced on the phone · (b) = free user who forgot · (c) = premium user, 1 freeze, forgot

| When | (a) unsynced lesson | (b) free, forgot | (c) premium, 1 freeze |
|---|---|---|---|
| **Midnight** | App: 🔥 "Syncing your lesson…" (`PENDING`). Push: **none** | App: 🔥 dashed "Did you watch offline? Open the app online to sync" (`PENDING`). Push: none | Same as (b) |
| **Next morning** | It syncs when the app goes online. The day turns `LEARNED_LATE_SYNC`. In-app ✅ "Your offline lesson counted". **No freeze offer while `queue_depth > 0`** | Push: "Today's lesson is ready, keep your 🔥" (no "lost" message). No freeze offer | Same as (b) |
| **+24h** | If it's still queued: in-app "Connect to sync" | Still `PENDING`. No offer | Still `PENDING`. No offer |
| **+48h** | Still pending while `queue_depth > 0`, for up to 7 days, then final | Day becomes **final** (`NO_ACTIVITY`) and the streak ends. One push: "Your 23-day streak ended. **Repair it for ₹49** (24h)". This is the **only freeze offer** | Day becomes final. The **freeze is used automatically** (`PROTECTED_FREEZE`) and the streak is kept. Push: "We used your freeze. Buy a spare for ₹49?" |

- **Freeze timing:** offered or used **only at +48h**. Never while the day is pending, never while the queue is non-empty, never for tampering. The engine honours a purchase made inside the 24h repair window.
- **Freeze revenue:**
  - Ritika's **−58%** is a mix artefact. Weeks 1–4 v2 had ~90 premium users per week, against ~900 in control, and premium buys 8× more freezes.
  - Like-for-like (weeks 5–10, both plans) it's **−35%**, about **−₹15.8 L/month** if nothing changes.
  - Moving the offer to +48h brings back the purchase moment. My estimate is that it recovers about half of that loss. That's unproven, so it's what §4 tests.

---

## 4. The beta: experiment, not ship

| Cohorts | ΔD7 (v2 − control) | Freezes per 1k |
|---|---|---|
| Week 1, all users (Neha) | +4.7pt | −58% |
| Week 1, by plan | free +8.1, premium +8.4 | −36%, −38% |
| **Weeks 5–10, clean mix** | **+2.4pt** (free +2.4, premium +2.5) | **−35%** (both plans) |

- **Why the headline numbers mislead:**
  - Weeks 1–4 have the billing-SDK enrolment bug, which kept premium users out of v2.
  - Week 1 is also a novelty peak.
- **Ship as-is:** +2.4pt × ₹2.6 L = **+₹6.2 L/month** retention, −₹15.8 L freezes = **−₹9.5 L/month**. Don't ship as-is.
- **Experiment:** v2 pending state **plus** the +48h repair offer (§3), against control. 50/50, new enrolees, both plans.
  - **Measure:** D7, and freeze revenue per 1k.
  - **Guardrails:** freeze revenue per 1k ≥ −10% of control, and support tickets per 1k not up.
  - **Length:** 4 enrolment weeks plus 14 days of follow-up (~6 weeks).
  - **Ship if** ΔD7 ≥ +2pt **and** freeze revenue ≥ −10%. That's +₹5.2 L − ₹4.5 L = **net ≥ +₹0.7 L/month**.
  - **Stop** early if freezes drop ≥ 30% after 2 weeks, or ΔD7 < +1pt.

---

## 5. Three things I deliberately didn't build
1. **Forgiving "I forgot" and travel (Neha's "when in doubt, be generous").** Free forgiveness removes the freeze purchase moment, which is 11% of revenue. Travel is handled correctly by local days; only a day under 12h is bridged.
2. **A manual override to match Support's promised numbers (Pooja).** An override table makes the CSV disagree with the rules. That's the inconsistency the brief warns against. TICKETS explains each difference instead.
3. **Hard proof for offline claims (Farhan's "no fakes"):** device attestation, a tamper ML score. We can't verify u13/u14-type syncs today, and §2 shows accepting them is cheaper. The only tamper check built is the provable one (published after the claimed watch time).

## 6. At 2M users (not built, see README)
- Per-user day rows, updated on ingest. A day becomes final after the 7-day cap.
- A late event recomputes only that user's open window.
- Ingest partitioned by `user_id`, idempotent on `event_id`.
- The streak cached per user and invalidated on write.
- The S3 raw log as the replay source for rule changes.

## Known limits
- **`affected_uids`:** seeded only from the incident's log *sample* (u08, u12, plus 2 others). Production uses the full table.
- **Freeze balance:** `users.freeze_balance` is read as the balance on 1 Nov.
- **Repair window:** the 24h repair window is product behaviour. The engine honours any purchase on the oldest final miss.
