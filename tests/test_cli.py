from unittest.mock import patch

from calendar_sync.__main__ import main
from calendar_sync.sync import SyncResult


def test_dry_run_flag_propagated(monkeypatch):
    monkeypatch.setenv("ICS_URL", "https://example.com/feed.ics")
    monkeypatch.setenv("TARGET_CALENDAR_ID", "abc@group.calendar.google.com")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/sa.json")

    with patch("calendar_sync.__main__.run") as run_mock:
        run_mock.return_value = SyncResult()
        exit_code = main(["--dry-run"])

    assert exit_code == 0
    run_mock.assert_called_once()
    assert run_mock.call_args.kwargs["dry_run"] is True


def test_errors_cause_nonzero_exit(monkeypatch):
    monkeypatch.setenv("ICS_URL", "https://example.com/feed.ics")
    monkeypatch.setenv("TARGET_CALENDAR_ID", "abc@group.calendar.google.com")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/sa.json")

    with patch("calendar_sync.__main__.run") as run_mock:
        run_mock.return_value = SyncResult(errors=2)
        exit_code = main([])

    assert exit_code == 1
