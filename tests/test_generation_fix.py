"""Tests for app.generation.fix (L3 — deterministic suggestions)."""

from __future__ import annotations

from app.generation.fix import suggest_fixes
from app.generation.validate import (
    CODE_FORBIDDEN,
    validate_progression,
)

KEY = "C major"
MINOR = "A minor"


def _assert_suggestions_valid(
    original,
    suggestions,
    *,
    key=KEY,
    cadence=None,
    locked=None,
    check_engine=False,
):
    assert suggestions, f"expected suggestions for {original}"
    assert len(suggestions) <= 3
    seen = set()
    for s in suggestions:
        assert s.label
        assert s.progression
        assert tuple(s.progression) not in seen
        seen.add(tuple(s.progression))
        result = validate_progression(
            s.progression,
            key,
            cadence=cadence,
            locked=locked,
            check_engine=check_engine,
            suggest=False,
        )
        assert result.ok, (s.label, s.progression, [i.message for i in result.issues])
        # Edits should describe the diff from original when same length.
        if len(s.progression) == len(original):
            for edit in s.edits:
                idx = edit["index"]
                assert original[idx] == edit["from"]
                assert s.progression[idx] == edit["to"]


def test_forbidden_v_to_iv_gets_valid_suggestions():
    prog = ["I", "V", "IV", "I"]
    suggestions = suggest_fixes(prog, KEY, cadence=None, check_engine=False)
    _assert_suggestions_valid(prog, suggestions, cadence=None)
    # Spec-style fixes should appear among options.
    progs = [list(s.progression) for s in suggestions]
    assert any(p[2] in ("I", "vi", "V", "V7") for p in progs)


def test_forbidden_with_pac_preserves_cadence():
    prog = ["I", "V", "IV", "I"]
    suggestions = suggest_fixes(prog, KEY, cadence="PAC", check_engine=False)
    _assert_suggestions_valid(prog, suggestions, cadence="PAC")
    for s in suggestions:
        assert s.progression[-1] == "I"
        assert s.progression[-2] in ("V", "V7")


def test_cadence_mismatch_aligned():
    prog = ["I", "IV", "V", "vi"]
    suggestions = suggest_fixes(prog, KEY, cadence="PAC", check_engine=False)
    _assert_suggestions_valid(prog, suggestions, cadence="PAC")
    # Minimal fix: last chord → I
    assert any(list(s.progression) == ["I", "IV", "V", "I"] for s in suggestions)


def test_unknown_figure_replaced():
    prog = ["I", "NotAChord", "V", "I"]
    suggestions = suggest_fixes(prog, KEY, cadence="PAC", check_engine=False)
    _assert_suggestions_valid(prog, suggestions, cadence="PAC")
    for s in suggestions:
        assert "NotAChord" not in s.progression


def test_honors_locked_slots():
    prog = ["I", "V", "IV", "I"]
    locked = {0: "I", 3: "I"}
    suggestions = suggest_fixes(
        prog, KEY, cadence="PAC", locked=locked, check_engine=False
    )
    _assert_suggestions_valid(prog, suggestions, cadence="PAC", locked=locked)
    for s in suggestions:
        assert s.progression[0] == "I"
        assert s.progression[3] == "I"


def test_empty_progression_suggestions():
    suggestions = suggest_fixes([], KEY, cadence="PAC", check_engine=False)
    assert suggestions
    for s in suggestions:
        result = validate_progression(
            s.progression, KEY, cadence="PAC", check_engine=False, suggest=False
        )
        assert result.ok


def test_already_valid_returns_no_suggestions():
    prog = ["I", "IV", "V", "I"]
    assert suggest_fixes(prog, KEY, cadence="PAC", check_engine=False) == []


def test_validate_with_suggest_attaches_to_result_and_issue():
    result = validate_progression(
        ["I", "V", "IV", "I"],
        KEY,
        cadence="PAC",
        check_engine=False,
        suggest=True,
    )
    assert result.ok is False
    assert result.suggestions
    _assert_suggestions_valid(
        ["I", "V", "IV", "I"],
        list(result.suggestions),
        cadence="PAC",
    )
    # First blocking issue carries the same suggestions.
    blocking = [i for i in result.issues if i.severity == "block"]
    assert blocking
    assert blocking[0].suggestions == result.suggestions
    # as_dict includes suggestions
    d = result.as_dict()
    assert d["suggestions"]
    assert d["issues"][0]["suggestions"]


def test_validate_suggest_false_leaves_empty():
    result = validate_progression(
        ["I", "V", "IV", "I"],
        KEY,
        check_engine=False,
        suggest=False,
    )
    assert result.suggestions == ()
    forbidden = next(i for i in result.issues if i.code == CODE_FORBIDDEN)
    assert forbidden.suggestions == ()


def test_minor_forbidden_and_cadence():
    prog = ["i", "V", "iv", "i"]
    suggestions = suggest_fixes(prog, MINOR, cadence="PAC", check_engine=False)
    _assert_suggestions_valid(prog, suggestions, key=MINOR, cadence="PAC")
    for s in suggestions:
        assert s.progression[-1] == "i"


def test_hc_cadence_fix():
    prog = ["I", "IV", "I"]
    suggestions = suggest_fixes(prog, KEY, cadence="HC", check_engine=False)
    _assert_suggestions_valid(prog, suggestions, cadence="HC")
    for s in suggestions:
        assert s.progression[-1] in ("V", "V7")


def test_max_suggestions_cap():
    prog = ["I", "V", "IV", "I"]
    suggestions = suggest_fixes(
        prog, KEY, cadence=None, check_engine=False, max_suggestions=1
    )
    assert len(suggestions) == 1


def test_deceptive_or_resolve_labels_preferred():
    """Among fixes for V→IV, prefer musically labeled single edits when possible."""
    prog = ["I", "V", "IV", "I"]
    suggestions = suggest_fixes(prog, KEY, cadence=None, check_engine=False)
    labels = [s.label for s in suggestions]
    # At least one musically meaningful label (not only bland phrase).
    assert any(
        lab in ("Resolve to tonic", "Deceptive", "Use dominant")
        or "→" in lab
        for lab in labels
    )
