from __future__ import annotations

from .models import SourceEvent, TargetEvent, Window, content_hash


def find_matches(
    source: list[SourceEvent],
    target: list[TargetEvent],
    fragment: str,
) -> list[tuple[str, str | None]]:
    """Resolve a case-insensitive fragment to a sorted list of (uid, recurrence_id) keys.

    Source pass: matches uid OR summary substring.
    Target fallback: only if source returns nothing; matches ics_uid substring.
    """
    needle = fragment.lower()
    keys: set[tuple[str, str | None]] = set()
    for s in source:
        if needle in s.uid.lower() or needle in s.summary.lower():
            keys.add((s.uid, s.recurrence_id))
    if keys:
        return sorted(keys, key=lambda k: (k[0], k[1] or ""))
    for t in target:
        if needle in t.ics_uid.lower():
            keys.add((t.ics_uid, t.ics_recurrence_id))
    return sorted(keys, key=lambda k: (k[0], k[1] or ""))


def verdict(
    source: SourceEvent | None,
    target: TargetEvent | None,
    window: Window,
) -> str:
    if source is not None and source.status == "CANCELLED":
        if target is not None:
            return "Delete (cancelled) — source.status=CANCELLED, target exists"
        return "none — source.status=CANCELLED and no target"

    if source is None and target is None:
        return "none — no event on either side"

    if source is not None and target is None:
        return "Create — source present, no target"

    if source is None and target is not None:
        if window.contains(target.start):
            return "Delete (vanished) — target inside window, source missing"
        return "none — target outside window, source missing"

    # both present, not cancelled
    src_hash = content_hash(source)
    raw_tgt_hash = target.content_hash
    if src_hash != raw_tgt_hash:
        tgt_display = raw_tgt_hash if raw_tgt_hash is not None else "(unset)"
        return f"Update — content_hash differs (source={src_hash} target={tgt_display})"
    return "none — content hashes match"
