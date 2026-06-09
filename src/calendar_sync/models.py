from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from typing import Literal


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime

    def contains(self, value: datetime | date) -> bool:
        if isinstance(value, datetime):
            v = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        else:
            v = datetime.combine(value, time.min, tzinfo=timezone.utc)
        return self.start <= v <= self.end


@dataclass(frozen=True)
class SourceEvent:
    uid: str
    recurrence_id: str | None
    summary: str
    description: str | None
    location: str | None
    start: datetime | date
    end: datetime | date
    tzid: str | None
    rrule: str | None
    exdates: tuple[datetime, ...] = field(default_factory=tuple)
    status: Literal["CONFIRMED", "CANCELLED"] = "CONFIRMED"
    sequence: int = 0
    last_modified: datetime | None = None


@dataclass(frozen=True)
class TargetEvent:
    google_event_id: str
    ics_uid: str
    ics_recurrence_id: str | None
    sequence: int | None
    start: datetime | date
    content_hash: str | None = None


@dataclass(frozen=True)
class Create:
    source: SourceEvent


@dataclass(frozen=True)
class Update:
    google_event_id: str
    source: SourceEvent


@dataclass(frozen=True)
class Delete:
    google_event_id: str
    reason: Literal["cancelled", "vanished"]


Action = Create | Update | Delete


def content_hash(source: SourceEvent) -> str:
    """Stable hash over the fields that matter for sync. Used in place of
    iCal SEQUENCE because Outlook frequently mutates events (adds EXDATEs,
    renames, moves times) without bumping SEQUENCE."""
    exdates_utc = sorted(
        ex.astimezone(timezone.utc).isoformat() for ex in source.exdates
    )
    parts = [
        source.summary,
        source.description or "",
        source.location or "",
        source.start.isoformat(),
        source.end.isoformat(),
        source.rrule or "",
        "|".join(exdates_utc),
        source.status,
    ]
    raw = "\x1e".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
