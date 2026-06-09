from datetime import date, datetime, timezone

from calendar_sync.models import Window


def test_window_contains_datetime_inside():
    w = Window(
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 12, 31, tzinfo=timezone.utc),
    )
    assert w.contains(datetime(2026, 6, 1, tzinfo=timezone.utc)) is True


def test_window_contains_datetime_outside():
    w = Window(
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 12, 31, tzinfo=timezone.utc),
    )
    assert w.contains(datetime(2027, 1, 1, tzinfo=timezone.utc)) is False


def test_window_contains_date_inside():
    w = Window(
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 12, 31, tzinfo=timezone.utc),
    )
    assert w.contains(date(2026, 6, 1)) is True
