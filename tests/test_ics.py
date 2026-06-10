from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from calendar_sync.ics import IcsParseError, parse_ics


def test_parse_ics_wraps_underlying_errors():
    with pytest.raises(IcsParseError):
        parse_ics("this is not a valid ics file", default_tz="UTC")


def test_parse_ics_wraps_per_component_errors():
    # Valid VCALENDAR but VEVENT missing required DTSTART.
    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//test//\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:broken-1\r\n"
        "SUMMARY:no dtstart\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    with pytest.raises(IcsParseError):
        parse_ics(ics, default_tz="UTC")


def test_parse_single_timed_event(fixture_text):
    events = parse_ics(fixture_text("single_event.ics"), default_tz="UTC")
    assert len(events) == 1
    e = events[0]
    assert e.uid == "single-1@example.com"
    assert e.recurrence_id is None
    assert e.summary == "Standup"
    assert e.description == "Daily standup"
    assert e.location == "Zoom"
    assert e.start == datetime(2026, 6, 15, 9, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    assert e.end == datetime(2026, 6, 15, 10, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    assert e.tzid == "America/Los_Angeles"
    assert e.rrule is None
    assert e.exdates == ()
    assert e.status == "CONFIRMED"
    assert e.sequence == 3


def test_parse_all_day_event(fixture_text):
    events = parse_ics(fixture_text("all_day_event.ics"), default_tz="UTC")
    assert len(events) == 1
    e = events[0]
    assert e.start == date(2026, 7, 4)
    assert e.end == date(2026, 7, 5)
    assert e.tzid is None


def test_floating_time_uses_default_tz(fixture_text):
    events = parse_ics(fixture_text("floating_time.ics"), default_tz="America/Los_Angeles")
    e = events[0]
    assert e.start == datetime(2026, 6, 15, 9, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    assert e.tzid == "America/Los_Angeles"


def test_recurring_with_cancelled_occurrence(fixture_text):
    events = parse_ics(
        fixture_text("recurring_with_cancellation.ics"), default_tz="UTC"
    )
    assert len(events) == 2

    master = next(e for e in events if e.recurrence_id is None)
    cancelled = next(e for e in events if e.recurrence_id is not None)

    assert master.rrule is not None
    assert "FREQ=WEEKLY" in master.rrule
    assert master.status == "CONFIRMED"

    assert cancelled.uid == master.uid
    assert cancelled.recurrence_id == "2026-06-15T16:00:00Z"
    assert cancelled.status == "CANCELLED"
