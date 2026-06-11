from datetime import datetime, timezone

from calendar_sync.diagnose import find_matches
from calendar_sync.models import SourceEvent, TargetEvent


def _src(uid="uid-1", recurrence_id=None, summary="Standup", status="CONFIRMED"):
    return SourceEvent(
        uid=uid,
        recurrence_id=recurrence_id,
        summary=summary,
        description=None,
        location=None,
        start=datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc),
        end=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        tzid="America/Los_Angeles",
        rrule=None,
        exdates=(),
        status=status,
        sequence=0,
    )


def _tgt(google_event_id="g-1", ics_uid="uid-1", ics_recurrence_id=None, content_hash="h"):
    return TargetEvent(
        google_event_id=google_event_id,
        ics_uid=ics_uid,
        ics_recurrence_id=ics_recurrence_id,
        sequence=0,
        start=datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc),
        content_hash=content_hash,
    )


def test_find_matches_by_uid_substring_case_insensitive():
    src = [_src(uid="ABC-FOO-123"), _src(uid="XYZ-456")]
    keys = find_matches(src, [], "foo")
    assert keys == [("ABC-FOO-123", None)]


def test_find_matches_by_summary_substring_case_insensitive():
    src = [_src(uid="u1", summary="Weekly Standup"), _src(uid="u2", summary="1:1")]
    keys = find_matches(src, [], "standup")
    assert keys == [("u1", None)]


def test_find_matches_returns_multiple_when_ambiguous():
    src = [
        _src(uid="u1", summary="Standup"),
        _src(uid="u2", recurrence_id="2026-06-15T16:00:00Z", summary="Standup"),
    ]
    keys = find_matches(src, [], "standup")
    assert keys == [("u1", None), ("u2", "2026-06-15T16:00:00Z")]


def test_find_matches_falls_back_to_target_when_source_empty():
    tgt = [_tgt(ics_uid="orphan-uid", ics_recurrence_id=None)]
    keys = find_matches([], tgt, "orphan")
    assert keys == [("orphan-uid", None)]


def test_find_matches_skips_target_fallback_when_source_matched():
    src = [_src(uid="match-source")]
    tgt = [_tgt(ics_uid="match-target")]
    keys = find_matches(src, tgt, "match")
    assert keys == [("match-source", None)]


def test_find_matches_returns_empty_when_no_hits():
    keys = find_matches([_src(uid="u1", summary="A")], [_tgt(ics_uid="u2")], "zzz")
    assert keys == []


def test_find_matches_results_are_sorted():
    src = [
        _src(uid="u2", summary="foo"),
        _src(uid="u1", recurrence_id="r2", summary="foo"),
        _src(uid="u1", recurrence_id="r1", summary="foo"),
    ]
    keys = find_matches(src, [], "foo")
    assert keys == [("u1", "r1"), ("u1", "r2"), ("u2", None)]


def test_find_matches_falls_back_to_target_when_source_has_no_match():
    src = [_src(uid="something-else", summary="Irrelevant")]
    tgt = [_tgt(ics_uid="orphan-uid")]
    keys = find_matches(src, tgt, "orphan")
    assert keys == [("orphan-uid", None)]


# --- verdict tests ---

from datetime import timedelta
from calendar_sync.diagnose import verdict
from calendar_sync.models import Window, content_hash


def _window_around(dt):
    return Window(start=dt - timedelta(days=1), end=dt + timedelta(days=1))


def _window_far_from(dt):
    return Window(
        start=dt - timedelta(days=400),
        end=dt - timedelta(days=300),
    )


def test_verdict_create_when_only_source():
    s = _src()
    w = _window_around(s.start)
    assert verdict(s, None, w) == "Create — source present, no target"


def test_verdict_update_when_hashes_differ():
    s = _src()
    t = _tgt(content_hash="different")
    w = _window_around(s.start)
    v = verdict(s, t, w)
    assert v.startswith("Update — content_hash differs")
    assert content_hash(s) in v
    assert "different" in v


def test_verdict_none_when_hashes_match():
    s = _src()
    t = _tgt(content_hash=content_hash(s))
    w = _window_around(s.start)
    assert verdict(s, t, w) == "none — content hashes match"


def test_verdict_delete_cancelled_when_source_cancelled_and_target_exists():
    s = _src(status="CANCELLED")
    t = _tgt(content_hash=content_hash(s))
    w = _window_around(s.start)
    assert verdict(s, t, w) == "Delete (cancelled) — source.status=CANCELLED, target exists"


def test_verdict_none_when_source_cancelled_and_no_target():
    s = _src(status="CANCELLED")
    w = _window_around(s.start)
    assert verdict(s, None, w) == "none — source.status=CANCELLED and no target"


def test_verdict_delete_vanished_when_target_inside_window_and_source_missing():
    t = _tgt()
    w = _window_around(t.start)
    assert verdict(None, t, w) == "Delete (vanished) — target inside window, source missing"


def test_verdict_none_when_target_outside_window_and_source_missing():
    t = _tgt()
    w = _window_far_from(t.start)
    assert verdict(None, t, w) == "none — target outside window, source missing"


def test_verdict_update_renders_none_target_hash_as_unset():
    s = _src()
    t = _tgt(content_hash=None)
    w = _window_around(s.start)
    v = verdict(s, t, w)
    assert "Update" in v
    assert "target=(unset)" in v
    assert "target=None" not in v


# --- render tests ---

from calendar_sync.diagnose import render_match_line, render_source, render_target


def test_render_match_line_with_source():
    s = _src(uid="u1", summary="Standup")
    line = render_match_line(("u1", None), source=s, target=None)
    assert "u1" in line
    assert '"Standup"' in line
    assert "recurrence_id=" not in line  # None is omitted


def test_render_match_line_with_recurrence_id():
    s = _src(uid="u1", recurrence_id="2026-06-15T16:00:00Z", summary="Standup")
    line = render_match_line(("u1", "2026-06-15T16:00:00Z"), source=s, target=None)
    assert "recurrence_id=2026-06-15T16:00:00Z" in line


def test_render_match_line_target_only_has_blank_summary():
    t = _tgt(ics_uid="orphan")
    line = render_match_line(("orphan", None), source=None, target=t)
    assert "orphan" in line
    assert '""' in line  # blank summary


def test_render_source_present():
    s = _src(uid="u1", summary="Standup")
    text = render_source(s)
    assert text.startswith("SOURCE\n")
    assert "u1" in text
    assert "Standup" in text
    assert "content_hash:" in text


def test_render_source_absent():
    text = render_source(None)
    assert text == "SOURCE\n  (not in current feed)"


def test_render_target_present_with_raw():
    t = _tgt(google_event_id="g-1")
    raw = {"id": "g-1", "recurrence": ["RRULE:FREQ=WEEKLY"]}
    text = render_target(t, raw)
    assert text.startswith("TARGET\n")
    assert "g-1" in text
    assert "RRULE:FREQ=WEEKLY" in text


def test_render_target_absent():
    text = render_target(None, None)
    assert text == "TARGET\n  (no Google event)"


def test_render_target_renders_missing_recurrence_as_dash():
    t = _tgt(google_event_id="g-1")
    raw = {"id": "g-1"}
    text = render_target(t, raw)
    assert "recurrence:      —" in text
    assert "None" not in text
