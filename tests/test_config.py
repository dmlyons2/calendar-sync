import pytest

from calendar_sync.config import Config, ConfigError


def test_load_minimal_env(monkeypatch):
    monkeypatch.setenv("ICS_URL", "https://example.com/feed.ics")
    monkeypatch.setenv("TARGET_CALENDAR_ID", "abc@group.calendar.google.com")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/sa.json")
    for key in ["SYNC_LOOKBACK_DAYS", "SYNC_LOOKAHEAD_DAYS", "DEFAULT_TZ", "LOG_LEVEL"]:
        monkeypatch.delenv(key, raising=False)

    cfg = Config.from_env()
    assert cfg.ics_url == "https://example.com/feed.ics"
    assert cfg.target_calendar_id == "abc@group.calendar.google.com"
    assert cfg.google_credentials_path == "/tmp/sa.json"
    assert cfg.lookback_days == 30
    assert cfg.lookahead_days == 365
    assert cfg.default_tz == "America/Los_Angeles"
    assert cfg.log_level == "INFO"


def test_missing_required_raises(monkeypatch):
    monkeypatch.delenv("ICS_URL", raising=False)
    monkeypatch.setenv("TARGET_CALENDAR_ID", "abc@group.calendar.google.com")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/sa.json")
    with pytest.raises(ConfigError, match="ICS_URL"):
        Config.from_env()


def test_rejects_primary_calendar(monkeypatch):
    monkeypatch.setenv("ICS_URL", "https://example.com/feed.ics")
    monkeypatch.setenv("TARGET_CALENDAR_ID", "primary")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/sa.json")
    with pytest.raises(ConfigError, match="primary"):
        Config.from_env()


def test_overrides_via_env(monkeypatch):
    monkeypatch.setenv("ICS_URL", "https://example.com/feed.ics")
    monkeypatch.setenv("TARGET_CALENDAR_ID", "abc@group.calendar.google.com")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/sa.json")
    monkeypatch.setenv("SYNC_LOOKBACK_DAYS", "7")
    monkeypatch.setenv("SYNC_LOOKAHEAD_DAYS", "180")
    monkeypatch.setenv("DEFAULT_TZ", "UTC")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    cfg = Config.from_env()
    assert cfg.lookback_days == 7
    assert cfg.lookahead_days == 180
    assert cfg.default_tz == "UTC"
    assert cfg.log_level == "DEBUG"
