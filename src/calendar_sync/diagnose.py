from __future__ import annotations

from .models import SourceEvent, TargetEvent


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
