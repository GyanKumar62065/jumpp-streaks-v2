# Findings while building

- **u02 = 54, not 55 (spec §4 corrected).** Its 14 Nov lesson in LA was at 21:02 PST, which is
  2026-11-15T05:02Z, after "now" (04:30Z). At "now" it is 14 Nov 20:30 in LA, so the day is
  `TODAY_OPEN`. The engine only sees events with `received_at ≤ as_of`. Pooja's 55 counts a day
  that hadn't ended yet.
