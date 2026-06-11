from __future__ import annotations

import json
import time
from collections.abc import Iterable
from datetime import UTC, date, datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import TargetEvent, content_hash

SYNC_SOURCE_TAG = "outlook-ics"
SAFETY_FILTER = f"syncSource={SYNC_SOURCE_TAG}"

SCOPES = ["https://www.googleapis.com/auth/calendar"]

_RETRY_STATUSES = {429, 500, 502, 503, 504}
_RETRYABLE_403_REASONS = {"rateLimitExceeded", "userRateLimitExceeded"}


def build_service(credentials_path: str):
    creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _http_error_reason(e: HttpError) -> str | None:
    content = getattr(e, "content", None)
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    if not content:
        return None
    try:
        body = json.loads(content)
    except ValueError:
        return None
    errors = body.get("error", {}).get("errors") or []
    if errors and isinstance(errors[0], dict):
        return errors[0].get("reason")
    return None


def _is_retryable(e: HttpError) -> bool:
    status = getattr(e.resp, "status", None)
    if status in _RETRY_STATUSES:
        return True
    if status == 403:
        return _http_error_reason(e) in _RETRYABLE_403_REASONS
    return False


def _retry(callable_, *, max_attempts: int = 5, backoff_base: float = 1.0):
    for attempt in range(max_attempts):
        try:
            return callable_()
        except HttpError as e:
            if not _is_retryable(e) or attempt + 1 == max_attempts:
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
        content_hash=props.get("icsContentHash") or None,
    )


def _format_dt(value):
    if isinstance(value, datetime):
        return {"dateTime": value.isoformat()}
    return {"date": value.isoformat()}


def _to_google_body(source) -> dict:
    body: dict = {
        "summary": source.summary,
        "description": source.description or "",
        "location": source.location or "",
        "start": _format_dt(source.start),
        "end": _format_dt(source.end),
        "extendedProperties": {
            "private": {
                "syncSource": SYNC_SOURCE_TAG,
                "icsUid": source.uid,
                "icsRecurrenceId": source.recurrence_id or "",
                "icsSequence": str(source.sequence),
                "icsContentHash": content_hash(source),
            }
        },
    }
    if isinstance(source.start, datetime) and source.tzid:
        body["start"]["timeZone"] = source.tzid
        body["end"]["timeZone"] = source.tzid
    if source.rrule:
        recurrence = [f"RRULE:{source.rrule}"]
        for ex in source.exdates:
            recurrence.append(f"EXDATE:{ex.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}")
        body["recurrence"] = recurrence
    return body


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

    def create_event(self, source) -> str:
        body = _to_google_body(source)
        response = _retry(
            self._service.events().insert(calendarId=self._calendar_id, body=body).execute
        )
        return response["id"]

    def update_event(self, google_event_id: str, source) -> None:
        body = _to_google_body(source)
        _retry(
            self._service.events()
            .patch(calendarId=self._calendar_id, eventId=google_event_id, body=body)
            .execute
        )

    def delete_event(self, google_event_id: str) -> None:
        _retry(
            self._service.events()
            .delete(calendarId=self._calendar_id, eventId=google_event_id)
            .execute
        )

    def get_event(self, google_event_id: str) -> dict:
        return _retry(
            self._service.events()
            .get(calendarId=self._calendar_id, eventId=google_event_id)
            .execute
        )
