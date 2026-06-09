from datetime import datetime
from zoneinfo import ZoneInfo

from calendar_sync.ics import parse_ics


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
