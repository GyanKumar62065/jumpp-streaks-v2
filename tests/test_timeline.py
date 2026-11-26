from datetime import date, datetime, timedelta

from streaks.timeline import get_day_spans
from tests.conftest import make_event, make_user

LA = "America/Los_Angeles"


def test_spans_for_home_tz_user_are_full_days():
    spans = get_day_spans(make_user(), [], datetime.fromisoformat("2026-11-03T10:00+05:30"))

    assert [span.date for span in spans] == [date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3)]
    assert all(span.length == timedelta(hours=24) for span in spans)
    assert spans[0].start == datetime.fromisoformat("2026-10-31T18:30:00+00:00")


def test_eastward_date_line_jump_creates_short_day():
    user = make_user(home_tz=LA, signup_at="2026-08-20T09:00:00-07:00")
    jump = make_event("tz_change", "2026-11-11T07:40:00+13:00", device_tz="Pacific/Auckland")

    spans = {span.date: span for span in get_day_spans(user, [jump], datetime.fromisoformat("2026-11-12T12:00+13:00"))}

    assert spans[date(2026, 11, 10)].length == timedelta(hours=10, minutes=40)
    assert date(2026, 11, 11) in spans


def test_westward_jump_merges_repeated_date():
    user = make_user()
    jump = make_event("tz_change", "2026-11-07T22:10:00-08:00", device_tz=LA)

    spans = get_day_spans(user, [jump], datetime.fromisoformat("2026-11-09T12:00-08:00"))
    dates = [span.date for span in spans]

    assert dates == sorted(set(dates))
    nov_7 = next(span for span in spans if span.date == date(2026, 11, 7))
    assert nov_7.end == datetime.fromisoformat("2026-11-08T08:00:00+00:00")


def test_spans_start_at_signup_date():
    user = make_user(signup_at="2026-11-13T23:50:00+05:30")

    spans = get_day_spans(user, [], datetime.fromisoformat("2026-11-15T10:00+05:30"))

    assert spans[0].date == date(2026, 11, 13)


def test_dst_change_day_has_its_real_length():
    user = make_user(home_tz=LA, signup_at="2026-08-20T09:00:00-07:00")

    spans = get_day_spans(user, [], datetime.fromisoformat("2026-11-02T12:00-08:00"))

    assert spans[0].date == date(2026, 11, 1)
    assert spans[0].length == timedelta(hours=25)  # US DST ended at 02:00 on 1 Nov 2026
