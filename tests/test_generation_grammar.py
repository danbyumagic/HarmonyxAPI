"""Tests for app.generation.grammar (M3 Chunk A — no HTTP)."""

from __future__ import annotations

import pytest

from app.generation.grammar import (
    GrammarError,
    FORBIDDEN_TRANSITIONS,
    generate_progression,
    is_forbidden_transition,
    tonic_figure,
)

KEY = "C major"
MINOR = "A minor"


def test_generate_progression_length_and_type():
    prog = generate_progression(KEY, length=8, seed=0)
    assert len(prog) == 8
    assert all(isinstance(f, str) and f for f in prog)


def test_fixed_seed_is_deterministic():
    a = generate_progression(KEY, length=8, seed=42)
    b = generate_progression(KEY, length=8, seed=42)
    c = generate_progression(KEY, length=8, seed=43)
    assert a == b
    assert a != c  # different seed should almost always differ for length 8


def test_pac_ends_with_dominant_to_tonic():
    for seed in range(20):
        prog = generate_progression(KEY, length=6, cadence="PAC", seed=seed)
        assert prog[-2] in ("V", "V7"), prog
        assert prog[-1] == "I", prog


def test_hc_ends_on_dominant():
    for seed in range(20):
        prog = generate_progression(KEY, length=5, cadence="HC", seed=seed)
        assert prog[-1] in ("V", "V7"), prog


def test_never_emits_forbidden_retrogression():
    for seed in range(30):
        prog = generate_progression(KEY, length=10, seed=seed)
        for a, b in zip(prog, prog[1:]):
            assert not is_forbidden_transition(a, b), (a, b, prog)
            assert (a, b) not in FORBIDDEN_TRANSITIONS


def test_locked_slots_honored():
    locked = {1: "IV", 3: "vi"}
    prog = generate_progression(KEY, length=6, locked=locked, seed=7)
    assert prog[1] == "IV"
    assert prog[3] == "vi"
    assert prog[-2] in ("V", "V7")
    assert prog[-1] == "I"


def test_locked_cadence_penultimate_honored_when_legal():
    prog = generate_progression(
        KEY, length=4, locked={2: "V7"}, cadence="PAC", seed=1
    )
    assert prog[2] == "V7"
    assert prog[3] == "I"


def test_locked_conflict_with_pac_raises():
    with pytest.raises(GrammarError):
        # Final locked to IV cannot be a PAC.
        generate_progression(KEY, length=4, locked={3: "IV"}, cadence="PAC", seed=0)


def test_minor_uses_minor_tonic_and_pac():
    prog = generate_progression(MINOR, length=6, cadence="PAC", seed=11)
    assert tonic_figure(MINOR) == "i"
    assert prog[-1] == "i"
    assert prog[-2] in ("V", "V7")


def test_pac_requires_length_at_least_2():
    with pytest.raises(GrammarError):
        generate_progression(KEY, length=1, cadence="PAC", seed=0)


def test_locked_index_out_of_range_raises():
    with pytest.raises(GrammarError):
        generate_progression(KEY, length=4, locked={9: "V"}, seed=0)
