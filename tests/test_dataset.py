"""Golden check: the real dataset against the hand predictions in spec §4."""

from datetime import date, datetime
from pathlib import Path

import pytest

from streaks.models import DayCode
from streaks.parsing import load_dataset
from streaks.report import compute_all_streaks

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime.fromisoformat("2026-11-15T10:00:00+05:30")

# u02 is 54, not 55: its 14 Nov LA lesson arrives at 10:32 IST, after "now" (see findings.md).
EXPECTED_STREAKS = {
    "u01": 12, "u02": 54, "u03": 26, "u04": 0, "u05": 20, "u06": 5, "u07": 72, "u08": 313,
    "u09": 2, "u10": 23, "u11": 3, "u12": 9, "u13": 58, "u14": 65, "u15": 30,
}


@pytest.fixture(scope="module")
def results():
    dataset = load_dataset(ROOT / "data", ROOT / "config" / "affected_uids.csv")
    return {result.user_id: result for result in compute_all_streaks(dataset, NOW)}


@pytest.mark.parametrize(("user_id", "expected"), sorted(EXPECTED_STREAKS.items()))
def test_dataset_streaks_match_spec_expectations(results, user_id, expected):
    assert results[user_id].current_streak == expected


def test_u06_tamper_days_are_rejected(results):
    codes = {row.date: row.code for row in results["u06"].days}

    assert codes[date(2026, 11, 8)] is DayCode.REJECTED_TAMPER
    assert codes[date(2026, 11, 9)] is DayCode.REJECTED_TAMPER
