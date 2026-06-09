from __future__ import annotations

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
