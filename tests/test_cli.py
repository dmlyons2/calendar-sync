import logging

import pytest
from unittest.mock import patch

from calendar_sync.__main__ import main
from calendar_sync.config import ConfigError
from calendar_sync.ics import IcsFetchError, IcsParseError
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


def _set_env(monkeypatch):
    monkeypatch.setenv("ICS_URL", "https://example.com/feed.ics")
    monkeypatch.setenv("TARGET_CALENDAR_ID", "abc@group.calendar.google.com")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/sa.json")


def test_config_error_logs_and_exits_2(monkeypatch, caplog):
    monkeypatch.delenv("ICS_URL", raising=False)
    monkeypatch.setenv("TARGET_CALENDAR_ID", "abc@group.calendar.google.com")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/sa.json")

    with caplog.at_level(logging.ERROR, logger="calendar_sync"):
        exit_code = main([])

    assert exit_code == 2
    assert any("ICS_URL" in r.message for r in caplog.records)
    assert not any(r.exc_info for r in caplog.records)


def test_ics_fetch_error_logs_and_exits_2(monkeypatch, caplog):
    _set_env(monkeypatch)

    with patch("calendar_sync.__main__.run") as run_mock:
        run_mock.side_effect = IcsFetchError("server error 503")
        with caplog.at_level(logging.ERROR, logger="calendar_sync"):
            exit_code = main([])

    assert exit_code == 2
    assert any("server error 503" in r.message for r in caplog.records)


def test_ics_parse_error_logs_and_exits_2(monkeypatch, caplog):
    _set_env(monkeypatch)

    with patch("calendar_sync.__main__.run") as run_mock:
        run_mock.side_effect = IcsParseError("malformed VEVENT")
        with caplog.at_level(logging.ERROR, logger="calendar_sync"):
            exit_code = main([])

    assert exit_code == 2
    assert any("malformed VEVENT" in r.message for r in caplog.records)


def test_unexpected_exception_propagates(monkeypatch):
    _set_env(monkeypatch)

    with patch("calendar_sync.__main__.run") as run_mock:
        run_mock.side_effect = RuntimeError("something else entirely")
        with pytest.raises(RuntimeError, match="something else entirely"):
            main([])
