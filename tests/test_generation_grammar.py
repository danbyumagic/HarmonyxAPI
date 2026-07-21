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


# --- Q3a: richer inversion / Cad64 traffic (no applied chords, no API) ---

_MAJOR_INVERSIONS = frozenset({"I6", "ii6", "IV6", "V6"})
_MINOR_INVERSIONS = frozenset({"i6", "iv6", "V6"})


def test_q3a_pac_length6_often_uses_inversion_or_cad64():
    """Modest share of seeds should show inversions and/or Cad64 (Q3a)."""
    n_seeds = 20
    hits = 0
    for seed in range(n_seeds):
        prog = generate_progression(KEY, length=6, cadence="PAC", seed=seed)
        has_inv = bool(set(prog) & _MAJOR_INVERSIONS)
        has_cad = "Cad64" in prog
        if has_inv or has_cad:
            hits += 1
        # Still student-safe: no secondary dominants in the figure set.
        assert not any("/" in fig for fig in prog), prog
        assert prog[-2] in ("V", "V7") and prog[-1] == "I"
    # Spec target ~30%; table is tuned higher — keep floor modest for stability.
    assert hits >= 6, f"expected >= 30% inversion/Cad64, got {hits}/{n_seeds}"


def test_q3a_pac_length8_can_emit_cad64():
    """With room before PAC, some seeds should approach via Cad64."""
    n_seeds = 20
    with_cad = 0
    for seed in range(n_seeds):
        prog = generate_progression(KEY, length=8, cadence="PAC", seed=seed)
        if "Cad64" in prog:
            with_cad += 1
            # Cad64 must resolve to V or V7 (table edge).
            for i, fig in enumerate(prog[:-1]):
                if fig == "Cad64":
                    assert prog[i + 1] in ("V", "V7"), prog
        for a, b in zip(prog, prog[1:]):
            assert not is_forbidden_transition(a, b), (a, b, prog)
    assert with_cad >= 1, f"expected at least one Cad64 in {n_seeds} seeds"


def test_q3a_minor_also_uses_inversions():
    n_seeds = 20
    hits = 0
    for seed in range(n_seeds):
        prog = generate_progression(MINOR, length=6, cadence="PAC", seed=seed)
        if set(prog) & _MINOR_INVERSIONS or "Cad64" in prog:
            hits += 1
        assert prog[-1] == "i"
        assert not any("/" in fig for fig in prog), prog
    assert hits >= 6, f"expected >= 30% inversion/Cad64 in minor, got {hits}/{n_seeds}"


def test_q3a_hc_still_ends_on_dominant():
    for seed in range(20):
        prog = generate_progression(KEY, length=6, cadence="HC", seed=seed)
        assert prog[-1] in ("V", "V7"), prog
        for a, b in zip(prog, prog[1:]):
            assert not is_forbidden_transition(a, b), (a, b, prog)
