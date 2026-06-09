from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .config import Config
from .google import GoogleClient, build_service
from .ics import fetch_ics, parse_ics
from .lock import LockHeldError, single_run_lock
from .models import Action, Create, Delete, Update, Window
from .reconcile import reconcile

LOG = logging.getLogger(__name__)
LOCK_PATH = "/tmp/calendar-sync.lock"


@dataclass(frozen=True)
class SyncResult:
    created: int = 0
    updated: int = 0
    deleted_cancelled: int = 0
    deleted_vanished: int = 0
    errors: int = 0


def build_window(cfg: Config, *, now: datetime | None = None) -> Window:
    now = now or datetime.now(tz=timezone.utc)
    return Window(
        start=now - timedelta(days=cfg.lookback_days),
        end=now + timedelta(days=cfg.lookahead_days),
    )


def apply_actions(client: GoogleClient, actions: list[Action], *, dry_run: bool) -> SyncResult:
    created = updated = del_c = del_v = errors = 0
    for action in actions:
        try:
            if isinstance(action, Create):
                LOG.debug(
                    "create uid=%s recurrence_id=%s summary=%r",
                    action.source.uid,
                    action.source.recurrence_id,
                    action.source.summary,
                )
                if not dry_run:
                    client.create_event(action.source)
                created += 1
            elif isinstance(action, Update):
                LOG.debug(
                    "update id=%s uid=%s recurrence_id=%s summary=%r",
                    action.google_event_id,
                    action.source.uid,
                    action.source.recurrence_id,
                    action.source.summary,
                )
                if not dry_run:
                    client.update_event(action.google_event_id, action.source)
                updated += 1
            elif isinstance(action, Delete):
                LOG.debug("delete id=%s reason=%s", action.google_event_id, action.reason)
                if not dry_run:
                    client.delete_event(action.google_event_id)
                if action.reason == "cancelled":
                    del_c += 1
                else:
                    del_v += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            LOG.error("action failed: %r: %s", action, e)
    return SyncResult(
        created=created,
        updated=updated,
        deleted_cancelled=del_c,
        deleted_vanished=del_v,
        errors=errors,
    )


def run(cfg: Config, *, dry_run: bool) -> SyncResult:
    try:
        with single_run_lock(LOCK_PATH):
            LOG.info(
                "starting sync (dry_run=%s, target=…%s)",
                dry_run,
                cfg.target_calendar_id[-8:],
            )
            text = fetch_ics(cfg.ics_url)
            source_events = parse_ics(text, default_tz=cfg.default_tz)

            service = build_service(cfg.google_credentials_path)
            client = GoogleClient(service=service, calendar_id=cfg.target_calendar_id)
            target_events = list(client.list_synced_events())

            window = build_window(cfg)
            actions = reconcile(source_events, target_events, window)
            return apply_actions(client, actions, dry_run=dry_run)
    except LockHeldError:
        LOG.info("previous run still active; exiting")
        return SyncResult()
