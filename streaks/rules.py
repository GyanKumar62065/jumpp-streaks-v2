"""Every streak rule value lives here. Change a rule here, then regenerate the CSV.

Why each value was chosen: docs/superpowers/specs/2026-11-26-streaks-v2-design.md §3.1.
"""

from datetime import UTC, date, datetime

# What counts as a learning day.
MIN_DAILY_WATCH_S = 120  # Farhan: "2 minutes a day"
COMPLETION_RATIO = 0.9  # one finished short lesson also counts (Neha)

# When a client clock is trusted.
MAX_OFFLINE_DELAY_H = 168  # the app queues events for up to 7 days
MAX_CLOCK_AHEAD_S = 300  # client_ts later than received_at by more = clock moved forward
LATE_SYNC_THRESHOLD_H = 1  # later than this is labelled a late sync

# When a missed day becomes final.
PENDING_WINDOW_H = 48  # no "you lost your streak" before this
MIN_DAY_LENGTH_H = 12  # a local day cut shorter by a timezone jump is a travel skip

# 9 Nov ingestion outage (brief/incident_2026-11-09.md).
OUTAGE_START = datetime(2026, 11, 9, 15, 15, tzinfo=UTC)
OUTAGE_END = datetime(2026, 11, 9, 16, 20, tzinfo=UTC)

# Day rows start here; earlier history is the users.csv carry-in.
HISTORY_START_DATE = date(2026, 11, 1)

FREEZE_PRICE_INR = 49
