"""Tests for the RN-agreement eval harness's alignment logic (A7)."""

from __future__ import annotations

from app.analyzer import ChordAnalysis
from eval.run_rn_eval import _chord_at


def _c(roman, measure, beat):
    return ChordAnalysis(
        measure=measure, beat=beat, pitches=["C4"], roman=roman,
        quality="major", inversion=0,
    )


def test_chord_at_returns_chord_sounding_at_exact_onset():
    chords = [_c("I", 1, 1.0), _c("V", 1, 3.0)]
    assert _chord_at(chords, 1, 3.0).roman == "V"


def test_chord_at_returns_last_chord_before_the_given_point():
    # Ground truth marks beat 2.5; the harmony from beat 1 is still sounding.
    chords = [_c("I", 1, 1.0), _c("V", 2, 1.0)]
    assert _chord_at(chords, 1, 2.5).roman == "I"


def test_chord_at_returns_none_before_the_first_chord():
    chords = [_c("I", 2, 1.0)]
    assert _chord_at(chords, 1, 1.0) is None
