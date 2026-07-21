"""Tests for app.generation.validate (L2 — theory + engine gates)."""

from __future__ import annotations

import pytest

from app.generation.corpus import load_corpus
from app.generation.validate import (
    CODE_CADENCE,
    CODE_EMPTY,
    CODE_FORBIDDEN,
    CODE_LOCK,
    CODE_UNKNOWN,
    CODE_UNREAL_CHORD,
    CODE_UNREAL_PATH,
    GATE_ENGINE,
    GATE_THEORY,
    SEVERITY_BLOCK,
    validate_progression,
)

KEY = "C major"
MINOR = "A minor"


def _codes(result):
    return [i.code for i in result.issues]


def test_ok_textbook_pac():
    result = validate_progression(
        ["I", "IV", "V", "I"], KEY, cadence="PAC", check_engine=True
    )
    assert result.ok is True
    assert result.blocking_issues == ()
    assert result.progression == ("I", "IV", "V", "I")


def test_ok_with_secondary_dominant():
    """Secondary dominants are not house-forbidden; theory gate must allow them."""
    result = validate_progression(
        ["I", "vi", "ii6", "V/V", "V", "I"],
        KEY,
        cadence="PAC",
        check_engine=False,
    )
    assert result.ok is True
    assert CODE_FORBIDDEN not in _codes(result)


def test_empty_progression():
    result = validate_progression([], KEY)
    assert result.ok is False
    assert CODE_EMPTY in _codes(result)
    assert result.issues[0].gate == GATE_THEORY
    assert result.issues[0].severity == SEVERITY_BLOCK


def test_unknown_figure():
    result = validate_progression(
        ["I", "NotAChord", "V", "I"], KEY, cadence="PAC", check_engine=False
    )
    assert result.ok is False
    assert CODE_UNKNOWN in _codes(result)
    unknown = next(i for i in result.issues if i.code == CODE_UNKNOWN)
    assert unknown.index == 1
    assert unknown.found["figure"] == "NotAChord"
    assert "Beat 2" in unknown.message


def test_forbidden_transition_v_to_iv():
    result = validate_progression(
        ["I", "V", "IV", "I"], KEY, cadence=None, check_engine=False
    )
    assert result.ok is False
    assert CODE_FORBIDDEN in _codes(result)
    issue = next(i for i in result.issues if i.code == CODE_FORBIDDEN)
    assert issue.span == (1, 2)
    assert issue.found == {"from": "V", "to": "IV"}
    assert issue.gate == GATE_THEORY
    assert "V → IV" in issue.message or "V → IV" in issue.message.replace("→", "→")


def test_forbidden_viio6_not_to_tonic():
    result = validate_progression(
        ["I", "viio6", "V", "I"], KEY, check_engine=False
    )
    assert result.ok is False
    assert CODE_FORBIDDEN in _codes(result)


def test_cadence_pac_mismatch_final():
    result = validate_progression(
        ["I", "IV", "V", "vi"], KEY, cadence="PAC", check_engine=False
    )
    assert result.ok is False
    assert CODE_CADENCE in _codes(result)
    cad = [i for i in result.issues if i.code == CODE_CADENCE]
    assert any("tonic" in i.message.lower() or "I" in i.message for i in cad)


def test_cadence_pac_mismatch_penultimate():
    result = validate_progression(
        ["I", "IV", "ii", "I"], KEY, cadence="PAC", check_engine=False
    )
    assert result.ok is False
    assert CODE_CADENCE in _codes(result)


def test_cadence_hc_ok_and_mismatch():
    ok = validate_progression(["I", "IV", "V"], KEY, cadence="HC", check_engine=False)
    assert ok.ok is True
    bad = validate_progression(["I", "IV", "I"], KEY, cadence="HC", check_engine=False)
    assert bad.ok is False
    assert CODE_CADENCE in _codes(bad)


def test_cadence_none_skips_shape_check():
    # Ends on IV — fine when no cadence contract requested.
    result = validate_progression(["I", "V", "I", "IV"], KEY, cadence=None, check_engine=False)
    assert result.ok is True


def test_lock_conflict_mismatch():
    result = validate_progression(
        ["I", "IV", "V", "I"],
        KEY,
        locked={1: "ii6"},
        check_engine=False,
    )
    assert result.ok is False
    assert CODE_LOCK in _codes(result)
    lock = next(i for i in result.issues if i.code == CODE_LOCK)
    assert lock.found["expected"] == "ii6"
    assert lock.found["actual"] == "IV"


def test_lock_honored_ok():
    result = validate_progression(
        ["I", "ii6", "V", "I"],
        KEY,
        cadence="PAC",
        locked={1: "ii6"},
        check_engine=False,
    )
    assert result.ok is True


def test_lock_out_of_range():
    result = validate_progression(
        ["I", "V", "I"],
        KEY,
        locked={9: "V"},
        check_engine=False,
    )
    assert result.ok is False
    assert CODE_LOCK in _codes(result)


def test_minor_pac_ok():
    result = validate_progression(
        ["i", "iv", "V", "i"], MINOR, cadence="PAC", check_engine=False
    )
    assert result.ok is True


def test_as_dict_shape():
    result = validate_progression(
        ["I", "V", "IV", "I"], KEY, check_engine=False
    )
    d = result.as_dict()
    assert d["ok"] is False
    assert d["progression"] == ["I", "V", "IV", "I"]
    assert isinstance(d["issues"], list)
    issue = d["issues"][0]
    assert issue["code"] == CODE_FORBIDDEN
    assert issue["severity"] == SEVERITY_BLOCK
    assert issue["gate"] == GATE_THEORY
    assert "suggestions" in issue


def test_engine_ok_on_simple_phrase():
    result = validate_progression(
        ["I", "V", "I"], KEY, cadence="PAC", check_engine=True
    )
    assert result.ok is True
    assert not any(i.gate == GATE_ENGINE for i in result.issues)


def test_engine_skipped_when_unknown_figure():
    """Don't pile engine noise on unparseable figures."""
    result = validate_progression(
        ["I", "???", "I"], KEY, check_engine=True
    )
    assert result.ok is False
    assert CODE_UNKNOWN in _codes(result)
    assert CODE_UNREAL_CHORD not in _codes(result)
    assert CODE_UNREAL_PATH not in _codes(result)


def test_corpus_entries_pass_theory_gate():
    """L1 seed should be house-legal under the cadence each entry declares."""
    entries = load_corpus()
    failures = []
    for e in entries:
        cad = e.cadence if e.cadence in ("PAC", "HC") else None
        result = validate_progression(
            e.progression, e.key, cadence=cad, check_engine=False
        )
        if not result.ok:
            failures.append((e.id, _codes(result), [i.message for i in result.issues]))
    assert failures == []


def test_check_engine_false_is_cheap_theory_only():
    # Even a path that might stress the realizer is theory-only when disabled.
    result = validate_progression(
        ["I", "vi", "ii6", "V7", "I"], KEY, cadence="PAC", check_engine=False
    )
    assert result.ok is True
    assert all(i.gate != GATE_ENGINE for i in result.issues)
