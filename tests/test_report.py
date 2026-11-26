from datetime import datetime
from pathlib import Path

from streaks.parsing import load_dataset
from streaks.report import compose_csv_rows, compose_user_action, compute_all_streaks

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime.fromisoformat("2026-11-15T10:00:00+05:30")


def _results():
    return compute_all_streaks(load_dataset(ROOT / "data", ROOT / "config" / "affected_uids.csv"), NOW)


def test_csv_rows_have_exact_columns():
    rows = compose_csv_rows(_results())

    assert len(rows) == 15
    assert all(list(row) == ["user_id", "current_streak", "status", "reason"] for row in rows)


def test_u07_support_header_offers_refund():
    u07 = next(result for result in _results() if result.user_id == "u07")

    assert "Refund ₹49" in compose_user_action(u07).text


def test_user_action_priority_puts_refund_and_tamper_first():
    from streaks.report import ActionKind, compose_user_action

    by_user = {result.user_id: compose_user_action(result) for result in _results()}

    assert by_user["u07"].kind is ActionKind.REFUND
    assert "₹49" in by_user["u07"].text
    assert by_user["u06"].kind is ActionKind.TAMPER
    assert by_user["u04"].kind is ActionKind.BROKEN
    assert "06 Nov" in by_user["u04"].text
    assert by_user["u05"] is None
