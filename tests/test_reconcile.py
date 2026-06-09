from datetime import datetime, timezone

from calendar_sync.models import (
    Create,
    Delete,
    SourceEvent,
    TargetEvent,
    Update,
    Window,
)
from calendar_sync.reconcile import reconcile


def _src(
    uid: str,
    recurrence_id: str | None = None,
    *,
    sequence: int = 0,
    status: str = "CONFIRMED",
    start: datetime | None = None,
) -> SourceEvent:
    return SourceEvent(
        uid=uid,
        recurrence_id=recurrence_id,
        summary="Meeting",
        description=None,
        location=None,
        start=start or datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc),
        end=start or datetime(2026, 6, 1, 16, 0, tzinfo=timezone.utc),
        tzid="America/Los_Angeles",
        rrule=None,
        exdates=(),
        status=status,  # type: ignore[arg-type]
        sequence=sequence,
        last_modified=None,
    )


def _tgt(
    uid: str,
    recurrence_id: str | None = None,
    *,
    google_event_id: str = "g1",
    sequence: int | None = 0,
    start: datetime | None = None,
) -> TargetEvent:
    return TargetEvent(
        google_event_id=google_event_id,
        ics_uid=uid,
        ics_recurrence_id=recurrence_id,
        sequence=sequence,
        start=start or datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc),
    )


WINDOW = Window(
    start=datetime(2026, 1, 1, tzinfo=timezone.utc),
    end=datetime(2026, 12, 31, tzinfo=timezone.utc),
)


def test_create_new_single_event():
    actions = reconcile([_src("uid-1")], [], WINDOW)
    assert len(actions) == 1
    assert isinstance(actions[0], Create)
    assert actions[0].source.uid == "uid-1"


def test_no_change_when_sequence_matches():
    s = _src("uid-1", sequence=3)
    t = _tgt("uid-1", sequence=3)
    actions = reconcile([s], [t], WINDOW)
    assert actions == []


def test_update_when_sequence_bumped():
    s = _src("uid-1", sequence=4)
    t = _tgt("uid-1", sequence=3)
    actions = reconcile([s], [t], WINDOW)
    assert len(actions) == 1
    assert isinstance(actions[0], Update)
    assert actions[0].google_event_id == "g1"
    assert actions[0].source.sequence == 4


def test_no_update_when_target_sequence_higher():
    s = _src("uid-1", sequence=2)
    t = _tgt("uid-1", sequence=5)
    actions = reconcile([s], [t], WINDOW)
    assert actions == []


def test_cancel_single_event():
    s = _src("uid-1", status="CANCELLED", sequence=2)
    t = _tgt("uid-1", sequence=1)
    actions = reconcile([s], [t], WINDOW)
    assert len(actions) == 1
    assert isinstance(actions[0], Delete)
    assert actions[0].google_event_id == "g1"
    assert actions[0].reason == "cancelled"


def test_cancelled_source_not_in_target_is_noop():
    s = _src("uid-1", status="CANCELLED")
    actions = reconcile([s], [], WINDOW)
    assert actions == []


def test_recurring_master_synced_independently_of_overrides():
    master = _src("uid-1", recurrence_id=None, sequence=1)
    override = _src(
        "uid-1",
        recurrence_id="2026-06-15T15:00:00Z",
        sequence=1,
        start=datetime(2026, 6, 15, 16, 0, tzinfo=timezone.utc),
    )
    actions = reconcile([master, override], [], WINDOW)
    assert len(actions) == 2
    assert all(isinstance(a, Create) for a in actions)


def test_cancel_one_occurrence_leaves_master_alone():
    master_src = _src("uid-1", recurrence_id=None, sequence=2)
    cancelled_override = _src(
        "uid-1",
        recurrence_id="2026-06-15T15:00:00Z",
        status="CANCELLED",
        sequence=2,
    )
    master_tgt = _tgt(
        "uid-1", recurrence_id=None, google_event_id="g-master", sequence=2
    )
    override_tgt = _tgt(
        "uid-1",
        recurrence_id="2026-06-15T15:00:00Z",
        google_event_id="g-instance",
        sequence=1,
    )
    actions = reconcile(
        [master_src, cancelled_override], [master_tgt, override_tgt], WINDOW
    )
    assert len(actions) == 1
    assert isinstance(actions[0], Delete)
    assert actions[0].google_event_id == "g-instance"
    assert actions[0].reason == "cancelled"


def test_modify_one_occurrence_updates_only_override():
    master_src = _src("uid-1", recurrence_id=None, sequence=1)
    moved = _src(
        "uid-1",
        recurrence_id="2026-06-15T15:00:00Z",
        sequence=2,
        start=datetime(2026, 6, 15, 17, 0, tzinfo=timezone.utc),
    )
    master_tgt = _tgt("uid-1", recurrence_id=None, google_event_id="g-master", sequence=1)
    override_tgt = _tgt(
        "uid-1",
        recurrence_id="2026-06-15T15:00:00Z",
        google_event_id="g-instance",
        sequence=1,
    )
    actions = reconcile([master_src, moved], [master_tgt, override_tgt], WINDOW)
    assert len(actions) == 1
    assert isinstance(actions[0], Update)
    assert actions[0].google_event_id == "g-instance"


def test_vanished_inside_window_is_deleted():
    t = _tgt("uid-1", start=datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc))
    actions = reconcile([], [t], WINDOW)
    assert len(actions) == 1
    assert isinstance(actions[0], Delete)
    assert actions[0].reason == "vanished"


def test_vanished_outside_window_is_left_alone():
    t = _tgt("uid-1", start=datetime(2027, 6, 1, 15, 0, tzinfo=timezone.utc))
    actions = reconcile([], [t], WINDOW)
    assert actions == []


def test_cancelled_status_deletes_even_outside_window():
    s = _src(
        "uid-1",
        status="CANCELLED",
        start=datetime(2027, 6, 1, 15, 0, tzinfo=timezone.utc),
    )
    t = _tgt("uid-1", start=datetime(2027, 6, 1, 15, 0, tzinfo=timezone.utc))
    actions = reconcile([s], [t], WINDOW)
    assert len(actions) == 1
    assert isinstance(actions[0], Delete)
    assert actions[0].reason == "cancelled"
