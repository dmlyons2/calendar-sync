import pytest

from calendar_sync.ics import IcsFetchError, fetch_ics


def test_fetch_ics_success(requests_mock):
    requests_mock.get("https://example.com/feed.ics", text="BEGIN:VCALENDAR\nEND:VCALENDAR")
    text = fetch_ics("https://example.com/feed.ics")
    assert "VCALENDAR" in text


def test_fetch_ics_retries_then_succeeds(requests_mock):
    requests_mock.get(
        "https://example.com/feed.ics",
        [
            {"status_code": 503, "text": "down"},
            {"status_code": 200, "text": "BEGIN:VCALENDAR\nEND:VCALENDAR"},
        ],
    )
    text = fetch_ics("https://example.com/feed.ics", max_attempts=2, backoff_base=0)
    assert "VCALENDAR" in text


def test_fetch_ics_raises_after_exhausting_retries(requests_mock):
    requests_mock.get("https://example.com/feed.ics", status_code=503, text="down")
    with pytest.raises(IcsFetchError):
        fetch_ics("https://example.com/feed.ics", max_attempts=2, backoff_base=0)
