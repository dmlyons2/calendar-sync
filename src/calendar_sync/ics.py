from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from icalendar import Calendar

from .models import SourceEvent


def _canonical_recurrence_id(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        v = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return value.isoformat()


def _resolve_dt(value: datetime | date, default_tz: str) -> datetime | date:
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=ZoneInfo(default_tz))
    return value


def _tzid_of(value: datetime | date) -> str | None:
    if isinstance(value, datetime) and value.tzinfo is not None:
        return str(value.tzinfo)
    return None


def _str_or_none(component, name: str) -> str | None:
    val = component.get(name)
    return str(val) if val is not None else None


def _int_or_zero(component, name: str) -> int:
    val = component.get(name)
    return int(val) if val is not None else 0


def _exdates(component) -> tuple[datetime, ...]:
    raw = component.get("exdate")
    if raw is None:
        return ()
    items = raw if isinstance(raw, list) else [raw]
    out: list[datetime] = []
    for item in items:
        for dt in item.dts:
            v = dt.dt
            if isinstance(v, datetime):
                out.append(v if v.tzinfo else v.replace(tzinfo=timezone.utc))
    return tuple(out)


def parse_ics(text: str, *, default_tz: str) -> list[SourceEvent]:
    cal = Calendar.from_ical(text)
    events: list[SourceEvent] = []
    for component in cal.walk("VEVENT"):
        dtstart = component.get("dtstart").dt
        dtend_prop = component.get("dtend")
        dtend = dtend_prop.dt if dtend_prop is not None else dtstart

        rid_prop = component.get("recurrence-id")
        recurrence_id = _canonical_recurrence_id(rid_prop.dt) if rid_prop is not None else None

        rrule_prop = component.get("rrule")
        rrule = rrule_prop.to_ical().decode() if rrule_prop is not None else None

        # Determine tzid before resolving dtstart (which may add timezone info)
        tzid = _tzid_of(dtstart)
        # If dtstart is a datetime without tzinfo (floating time), tzid should be default_tz
        if isinstance(dtstart, datetime) and dtstart.tzinfo is None:
            tzid = default_tz

        events.append(
            SourceEvent(
                uid=str(component["uid"]),
                recurrence_id=recurrence_id,
                summary=_str_or_none(component, "summary") or "",
                description=_str_or_none(component, "description"),
                location=_str_or_none(component, "location"),
                start=_resolve_dt(dtstart, default_tz),
                end=_resolve_dt(dtend, default_tz),
                tzid=tzid,
                rrule=rrule,
                exdates=_exdates(component),
                status=(_str_or_none(component, "status") or "CONFIRMED").upper(),  # type: ignore[arg-type]
                sequence=_int_or_zero(component, "sequence"),
                last_modified=(
                    component.get("last-modified").dt
                    if component.get("last-modified") is not None
                    else None
                ),
            )
        )
    return events
