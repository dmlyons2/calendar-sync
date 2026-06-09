from __future__ import annotations

from .models import Action, Create, Delete, SourceEvent, TargetEvent, Update, Window


def reconcile(
    source: list[SourceEvent],
    target: list[TargetEvent],
    window: Window,
) -> list[Action]:
    src_by_key: dict[tuple[str, str | None], SourceEvent] = {
        (e.uid, e.recurrence_id): e for e in source
    }
    tgt_by_key: dict[tuple[str, str | None], TargetEvent] = {
        (e.ics_uid, e.ics_recurrence_id): e for e in target
    }

    actions: list[Action] = []

    # 1. CANCELLED in source → delete
    for key, s in src_by_key.items():
        if s.status == "CANCELLED" and key in tgt_by_key:
            actions.append(Delete(tgt_by_key[key].google_event_id, reason="cancelled"))

    # 2. New or changed → create/update
    for key, s in src_by_key.items():
        if s.status == "CANCELLED":
            continue
        if key not in tgt_by_key:
            actions.append(Create(s))
        elif s.sequence > (tgt_by_key[key].sequence or -1):
            actions.append(Update(tgt_by_key[key].google_event_id, s))

    # 3. Vanished from feed within window → delete
    for key, t in tgt_by_key.items():
        if key in src_by_key:
            continue
        if window.contains(t.start):
            actions.append(Delete(t.google_event_id, reason="vanished"))

    return actions
