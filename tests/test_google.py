from unittest.mock import MagicMock

from calendar_sync.google import GoogleClient

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
