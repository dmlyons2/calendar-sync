from __future__ import annotations

import time
from datetime import date, datetime
from typing import Iterable

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import TargetEvent

SYNC_SOURCE_TAG = "outlook-ics"
SAFETY_FILTER = f"syncSource={SYNC_SOURCE_TAG}"

SCOPES = ["https://www.googleapis.com/auth/calendar"]

_RETRY_STATUSES = {403, 429, 500, 502, 503, 504}


def build_service(credentials_path: str):
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _retry(callable_, *, max_attempts: int = 5, backoff_base: float = 1.0):
    for attempt in range(max_attempts):
        try:
            return callable_()
        except HttpError as e:
            status = getattr(e.resp, "status", None)
            if status not in _RETRY_STATUSES or attempt + 1 == max_attempts:
                raise
            time.sleep(backoff_base * (2**attempt))
    raise RuntimeError("unreachable")


def _parse_event_start(item: dict) -> datetime | date:
    start = item["start"]
    if "date" in start:
        return date.fromisoformat(start["date"])
    return datetime.fromisoformat(start["dateTime"])


def _to_target_event(item: dict) -> TargetEvent:
    props = item.get("extendedProperties", {}).get("private", {})
    rid = props.get("icsRecurrenceId") or None
    seq_raw = props.get("icsSequence")
    sequence = int(seq_raw) if seq_raw is not None and seq_raw != "" else None
    return TargetEvent(
        google_event_id=item["id"],
        ics_uid=props["icsUid"],
        ics_recurrence_id=rid,
        sequence=sequence,
        start=_parse_event_start(item),
    )


class GoogleClient:
    def __init__(self, *, service, calendar_id: str):
        self._service = service
        self._calendar_id = calendar_id

    def list_synced_events(self) -> Iterable[TargetEvent]:
        events_api = self._service.events()
        request = events_api.list(
            calendarId=self._calendar_id,
            privateExtendedProperty=SAFETY_FILTER,
            showDeleted=False,
            singleEvents=False,
            maxResults=2500,
        )
        while request is not None:
            response = _retry(request.execute)
            for item in response.get("items", []):
                yield _to_target_event(item)
            request = events_api.list_next(request, response)
