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
