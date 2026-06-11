from datetime import UTC, datetime
from unittest.mock import MagicMock

from calendar_sync.config import Config
from calendar_sync.models import Create, Delete, SourceEvent, Update
from calendar_sync.sync import SyncResult, apply_actions, build_window


def _cfg() -> Config:
    return Config(
        ics_url="https://example.com/feed.ics",
        target_calendar_id="cal-1",
        google_credentials_path="/tmp/sa.json",
        lookback_days=30,
        lookahead_days=365,
        default_tz="America/Los_Angeles",
        log_level="INFO",
    )


def _src(uid="uid-1", sequence=1) -> SourceEvent:
    return SourceEvent(
        uid=uid,
        recurrence_id=None,
        summary="x",
        description=None,
        location=None,
        start=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
        end=datetime(2026, 6, 1, 16, 0, tzinfo=UTC),
        tzid="UTC",
        rrule=None,
        exdates=(),
        status="CONFIRMED",
        sequence=sequence,
        last_modified=None,
    )


def test_build_window_uses_config():
    now = datetime(2026, 6, 1, tzinfo=UTC)
    cfg = _cfg()
    window = build_window(cfg, now=now)
    assert (window.end - window.start).days == cfg.lookback_days + cfg.lookahead_days


def test_apply_actions_calls_client_methods():
    client = MagicMock()
    client.create_event.return_value = "g-new"
    actions = [
        Create(_src(uid="a")),
        Update("g-2", _src(uid="b", sequence=5)),
        Delete("g-3", reason="cancelled"),
        Delete("g-4", reason="vanished"),
    ]
    result = apply_actions(client, actions, dry_run=False)
    assert result == SyncResult(
        created=1, updated=1, deleted_cancelled=1, deleted_vanished=1, errors=0
    )
    client.create_event.assert_called_once()
    client.update_event.assert_called_once_with("g-2", actions[1].source)
    assert client.delete_event.call_count == 2


def test_apply_actions_dry_run_makes_no_calls():
    client = MagicMock()
    actions = [Create(_src()), Delete("g-3", reason="cancelled")]
    result = apply_actions(client, actions, dry_run=True)
    assert result == SyncResult(
        created=1, updated=0, deleted_cancelled=1, deleted_vanished=0, errors=0
    )
    client.create_event.assert_not_called()
    client.delete_event.assert_not_called()


def test_apply_actions_counts_errors_and_continues():
    client = MagicMock()
    client.create_event.side_effect = [RuntimeError("boom"), "g-ok"]
    actions = [Create(_src(uid="a")), Create(_src(uid="b"))]
    result = apply_actions(client, actions, dry_run=False)
    assert result.errors == 1
    assert result.created == 1
