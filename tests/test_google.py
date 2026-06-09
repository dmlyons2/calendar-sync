from datetime import datetime, timezone
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from calendar_sync.google import GoogleClient
from calendar_sync.models import SourceEvent

SAFETY_TAG = "syncSource=outlook-ics"


def _mock_service_with_pages(pages: list[dict]):
    """Build a mocked Google discovery service whose events().list().execute() pages through `pages`."""
    service = MagicMock()
    list_chain = service.events.return_value.list
    list_next_chain = service.events.return_value.list_next

    list_chain.return_value.execute.return_value = pages[0]
    if len(pages) > 1:
        list_next_chain.side_effect = [MagicMock(execute=MagicMock(return_value=p)) for p in pages[1:]] + [None]
    else:
        list_next_chain.return_value = None
    return service, list_chain


def test_list_synced_events_includes_safety_filter():
    service, list_chain = _mock_service_with_pages(
        [{"items": []}]
    )
    client = GoogleClient(service=service, calendar_id="cal-1")
    list(client.list_synced_events())

    list_chain.assert_called_once()
    call_kwargs = list_chain.call_args.kwargs
    assert call_kwargs["calendarId"] == "cal-1"
    assert call_kwargs["privateExtendedProperty"] == SAFETY_TAG


def test_list_synced_events_returns_target_events():
    page = {
        "items": [
            {
                "id": "g-1",
                "start": {"dateTime": "2026-06-15T09:00:00-07:00"},
                "extendedProperties": {
                    "private": {
                        "syncSource": "outlook-ics",
                        "icsUid": "uid-1",
                        "icsRecurrenceId": "",
                        "icsSequence": "3",
                    }
                },
            }
        ]
    }
    service, _ = _mock_service_with_pages([page])
    client = GoogleClient(service=service, calendar_id="cal-1")
    events = list(client.list_synced_events())
    assert len(events) == 1
    e = events[0]
    assert e.google_event_id == "g-1"
    assert e.ics_uid == "uid-1"
    assert e.ics_recurrence_id is None
    assert e.sequence == 3


def _source(**overrides) -> SourceEvent:
    defaults = dict(
        uid="uid-1",
        recurrence_id=None,
        summary="Standup",
        description="Daily",
        location="Zoom",
        start=datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc),
        end=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        tzid="America/Los_Angeles",
        rrule=None,
        exdates=(),
        status="CONFIRMED",
        sequence=2,
        last_modified=None,
    )
    defaults.update(overrides)
    return SourceEvent(**defaults)


def test_create_event_stamps_safety_properties():
    service = MagicMock()
    insert = service.events.return_value.insert
    insert.return_value.execute.return_value = {"id": "g-new"}

    client = GoogleClient(service=service, calendar_id="cal-1")
    google_id = client.create_event(_source())

    assert google_id == "g-new"
    body = insert.call_args.kwargs["body"]
    assert body["summary"] == "Standup"
    props = body["extendedProperties"]["private"]
    assert props["syncSource"] == "outlook-ics"
    assert props["icsUid"] == "uid-1"
    assert props["icsRecurrenceId"] == ""
    assert props["icsSequence"] == "2"


def test_update_event_uses_patch_with_event_id():
    service = MagicMock()
    patch = service.events.return_value.patch
    patch.return_value.execute.return_value = {"id": "g-1"}

    client = GoogleClient(service=service, calendar_id="cal-1")
    client.update_event("g-1", _source(sequence=5))

    assert patch.call_args.kwargs["calendarId"] == "cal-1"
    assert patch.call_args.kwargs["eventId"] == "g-1"
    body = patch.call_args.kwargs["body"]
    assert body["extendedProperties"]["private"]["icsSequence"] == "5"


def test_delete_event():
    service = MagicMock()
    delete = service.events.return_value.delete
    delete.return_value.execute.return_value = None

    client = GoogleClient(service=service, calendar_id="cal-1")
    client.delete_event("g-1")

    delete.assert_called_once_with(calendarId="cal-1", eventId="g-1")


def test_delete_event_on_instance_id_works_via_same_api():
    """Documents that cancelling one occurrence uses the same delete_event path,
    because we previously stored the override as a tagged Google event whose ID
    is the instance ID."""
    service = MagicMock()
    delete = service.events.return_value.delete
    delete.return_value.execute.return_value = None

    client = GoogleClient(service=service, calendar_id="cal-1")
    client.delete_event("g-master_R20260615T160000Z")

    delete.assert_called_once_with(
        calendarId="cal-1", eventId="g-master_R20260615T160000Z"
    )


def test_to_google_body_serializes_exdate_in_utc():
    service = MagicMock()
    insert = service.events.return_value.insert
    insert.return_value.execute.return_value = {"id": "g-new"}

    src = _source(
        rrule="FREQ=WEEKLY;BYDAY=MO",
        exdates=(datetime(2026, 6, 15, 9, 0, tzinfo=ZoneInfo("America/Los_Angeles")),),
    )
    client = GoogleClient(service=service, calendar_id="cal-1")
    client.create_event(src)

    body = insert.call_args.kwargs["body"]
    # 9am Los Angeles in June (DST, UTC-7) == 16:00 UTC
    assert "EXDATE:20260615T160000Z" in body["recurrence"]
