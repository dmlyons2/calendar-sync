import pytest
import requests

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


def test_fetch_ics_does_not_retry_404(requests_mock):
    matcher = requests_mock.get("https://example.com/feed.ics", status_code=404, text="not found")
    with pytest.raises(IcsFetchError):
        fetch_ics("https://example.com/feed.ics", max_attempts=3, backoff_base=0)
    assert matcher.call_count == 1


def test_fetch_ics_does_not_retry_403(requests_mock):
    matcher = requests_mock.get("https://example.com/feed.ics", status_code=403, text="forbidden")
    with pytest.raises(IcsFetchError):
        fetch_ics("https://example.com/feed.ics", max_attempts=3, backoff_base=0)
    assert matcher.call_count == 1


def test_fetch_ics_still_retries_on_connection_error(requests_mock):
    matcher = requests_mock.get("https://example.com/feed.ics", exc=requests.ConnectionError)
    with pytest.raises(IcsFetchError):
        fetch_ics("https://example.com/feed.ics", max_attempts=3, backoff_base=0)
    assert matcher.call_count == 3


def test_fetch_ics_still_retries_on_timeout(requests_mock):
    matcher = requests_mock.get("https://example.com/feed.ics", exc=requests.Timeout)
    with pytest.raises(IcsFetchError):
        fetch_ics("https://example.com/feed.ics", max_attempts=3, backoff_base=0)
    assert matcher.call_count == 3
