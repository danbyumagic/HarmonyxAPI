"""Tests for app.generation.voicing (Milestone 1b)."""

from __future__ import annotations

from app.generation import rules
from app.generation.voicing import Voicing, candidate_voicings


def test_candidate_voicings_nonempty_for_triad_and_seventh():
    assert len(candidate_voicings("I", "C major")) > 0
    assert len(candidate_voicings("V7", "C major")) > 0


def test_every_candidate_satisfies_static_rules():
    for figure in ["I", "V", "V7", "ii6", "viio6", "IV", "vi", "Cad64"]:
        for v in candidate_voicings(figure, "C major"):
            ctx = {"key": "C major", "prev_roman": None, "cur_roman": figure}
            assert rules.rule_violations(None, v, ctx) == [], (figure, v)


def test_root_position_candidates_include_a_root_doubled_voicing():
    # At least one root-position I candidate should double the root (C).
    cands = candidate_voicings("I", "C major")
    doubled_root = [
        v for v in cands
        if [v.s % 12, v.a % 12, v.t % 12, v.b % 12].count(0) >= 2
    ]
    assert doubled_root, "expected at least one root-doubled root-position voicing"


def test_given_soprano_is_respected():
    cands = candidate_voicings("V", "C major", soprano=71)  # B4, a chord tone of V
    assert cands
    assert all(v.s == 71 for v in cands)


def test_candidates_cover_all_chord_tones():
    # Every returned voicing for a seventh chord must contain all four tones.
    for v in candidate_voicings("V7", "C major"):
        pcs = {v.s % 12, v.a % 12, v.t % 12, v.b % 12}
        assert pcs == {2, 5, 7, 11}  # G B D F


def test_voicing_is_not_reordered():
    # A deliberately-crossed construction stays crossed (not auto-sorted).
    v = Voicing(60, 72, 55, 48)  # s < a -- a "crossing" shape
    assert v.s == 60 and v.a == 72
