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
