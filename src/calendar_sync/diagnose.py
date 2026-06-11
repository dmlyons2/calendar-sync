from __future__ import annotations

from .config import Config
from .google import GoogleClient, build_service
from .ics import fetch_ics, parse_ics
from .models import SourceEvent, TargetEvent, Window, content_hash
from .sync import build_window


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


def render_match_line(
    key: tuple[str, str | None],
    *,
    source: SourceEvent | None,
    target: TargetEvent | None,
) -> str:
    uid, recurrence_id = key
    summary = source.summary if source is not None else ""
    start = source.start if source is not None else (target.start if target else "")
    rid = f" recurrence_id={recurrence_id}" if recurrence_id else ""
    return f'{uid}{rid} "{summary}" @{start}'


def render_source(source: SourceEvent | None) -> str:
    if source is None:
        return "SOURCE\n  (not in current feed)"
    exdates = ", ".join(
        ex.strftime("%Y%m%dT%H%M%SZ") for ex in source.exdates
    ) or "—"
    tz_suffix = f" ({source.tzid})" if source.tzid else ""
    return (
        "SOURCE\n"
        f"  uid:            {source.uid}\n"
        f"  recurrence_id:  {source.recurrence_id or '—'}\n"
        f"  summary:        {source.summary}\n"
        f"  start:          {source.start}{tz_suffix}\n"
        f"  status:         {source.status}\n"
        f"  sequence:       {source.sequence}\n"
        f"  rrule:          {source.rrule or '—'}\n"
        f"  exdates:        {exdates}\n"
        f"  content_hash:   {content_hash(source)}"
    )


def render_target(target: TargetEvent | None, raw: dict | None) -> str:
    if target is None:
        return "TARGET\n  (no Google event)"
    recurrence = raw.get("recurrence") if raw else None
    recurrence_display = recurrence if recurrence is not None else "—"
    return (
        "TARGET\n"
        f"  google_event_id: {target.google_event_id}\n"
        f"  stored_sequence: {target.sequence}\n"
        f"  stored_hash:     {target.content_hash}\n"
        f"  recurrence:      {recurrence_display}"
    )


def diagnose(cfg: Config, fragment: str) -> tuple[int, str]:
    ics_text = fetch_ics(cfg.ics_url)
    sources = parse_ics(ics_text, default_tz=cfg.default_tz)
    service = build_service(cfg.google_credentials_path)
    client = GoogleClient(service=service, calendar_id=cfg.target_calendar_id)
    targets = list(client.list_synced_events())

    keys = find_matches(sources, targets, fragment)
    if not keys:
        return 1, f'no matching events for "{fragment}"'

    src_by_key = {(s.uid, s.recurrence_id): s for s in sources}
    tgt_by_key = {(t.ics_uid, t.ics_recurrence_id): t for t in targets}

    if len(keys) > 1:
        lines = [
            render_match_line(k, source=src_by_key.get(k), target=tgt_by_key.get(k))
            for k in keys
        ]
        lines.append("Refine the fragment.")
        return 2, "\n".join(lines)

    key = keys[0]
    source = src_by_key.get(key)
    target = tgt_by_key.get(key)
    raw = client.get_event(target.google_event_id) if target is not None else None
    window = build_window(cfg)

    blocks = [
        render_source(source),
        "",
        render_target(target, raw),
        "",
        f"VERDICT\n  Action: {verdict(source, target, window)}",
    ]
    return 0, "\n".join(blocks)
