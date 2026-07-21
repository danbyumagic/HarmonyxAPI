"""Tests for app.generation.realize (Milestone 1d/1e).

Milestone 1 acceptance (IMPLEMENTATION-PLAN): realizing ["I","IV","V","I"] in
C major yields a 4-voice score with zero parallel 5ths/8ves and correct
outer-voice cadential resolution -- both soprano-free and soprano-given.
"""

from __future__ import annotations

import pytest
from music21 import stream as m21stream

from app.generation.realize import (
    RealizationError,
    check_soprano,
    path_violations,
    realize,
    satb_voicings_from_score,
)
from app.generation.voicing import Voicing

KEY = "C major"


def _voicings_from_score(score: m21stream.Score) -> list[Voicing]:
    return satb_voicings_from_score(score)


def test_realize_returns_grand_staff_satb():
    score = realize(["I", "IV", "V", "I"], KEY)
    assert {p.id for p in score.parts} == {"Treble", "Bass"}
    voicings = satb_voicings_from_score(score)
    assert len(voicings) == 4
    # Stem directions: S/T up, A/B down on their respective staves.
    treble = next(p for p in score.parts if p.id == "Treble")
    bass = next(p for p in score.parts if p.id == "Bass")
    t_notes = list(treble.recurse().notes)
    b_notes = list(bass.recurse().notes)
    assert any(n.stemDirection == "up" for n in t_notes)
    assert any(n.stemDirection == "down" for n in t_notes)
    assert any(n.stemDirection == "up" for n in b_notes)
    assert any(n.stemDirection == "down" for n in b_notes)


def test_realize_i_iv_v_i_has_zero_hard_violations():
    progression = ["I", "IV", "V", "I"]
    score = realize(progression, KEY)
    voicings = _voicings_from_score(score)
    assert path_violations(voicings, progression, KEY) == []


def test_realize_cadence_resolves_leading_tone_up():
    # V -> I: whichever voice holds the leading tone in an outer voice must
    # resolve up by semitone (this is exactly what zero violations already
    # implies, but assert it directly too since it's the named acceptance
    # criterion).
    progression = ["I", "IV", "V", "I"]
    score = realize(progression, KEY)
    voicings = _voicings_from_score(score)
    v_chord, i_chord = voicings[2], voicings[3]
    # B (pc 11) is the leading tone of C major.
    for voice in ("s", "b"):
        p = getattr(v_chord, voice)
        if p % 12 == 11:
            assert getattr(i_chord, voice) - p == 1


def test_realize_longer_progression_zero_violations():
    progression = ["I", "IV", "I", "V", "I", "vi", "IV", "V", "I"]
    score = realize(progression, KEY)
    voicings = _voicings_from_score(score)
    assert path_violations(voicings, progression, KEY) == []


def test_realize_with_given_soprano_respects_it():
    soprano = [72, 71, 72]  # C5 - B4 - C5
    score = realize(["I", "V", "I"], KEY, soprano=soprano)
    voicings = _voicings_from_score(score)
    assert [v.s for v in voicings] == soprano
    assert path_violations(voicings, ["I", "V", "I"], KEY) == []


def test_realize_with_partial_soprano():
    soprano = [None, None, 72]
    score = realize(["I", "IV", "I"], KEY, soprano=soprano)
    voicings = _voicings_from_score(score)
    assert voicings[2].s == 72
    assert path_violations(voicings, ["I", "IV", "I"], KEY) == []


def test_realize_empty_progression_raises():
    with pytest.raises(RealizationError):
        realize([], KEY)


def test_realize_soprano_length_mismatch_raises():
    with pytest.raises(ValueError):
        realize(["I", "V"], KEY, soprano=[60])


def test_realize_incompatible_soprano_raises_realization_error():
    # C4 is not a chord tone of V (G-B-D); check_soprano would catch this
    # before calling realize in the API layer, but realize() itself must
    # also refuse cleanly rather than silently substituting a note.
    with pytest.raises(RealizationError):
        realize(["I", "V"], KEY, soprano=[60, 60])


# --- check_soprano -----------------------------------------------------


def test_check_soprano_flags_incompatible_note():
    mismatches = check_soprano(["I", "V"], KEY, [60, 60])
    assert len(mismatches) == 1
    assert mismatches[0]["index"] == 1
    assert mismatches[0]["roman"] == "V"
    assert mismatches[0]["soprano"] == 60
    assert 11 in mismatches[0]["chord_tones"]  # V does contain B; C(60) just isn't a member


def test_check_soprano_all_compatible_returns_empty():
    assert check_soprano(["I", "V"], KEY, [60, 67]) == []


def test_check_soprano_skips_none_entries():
    assert check_soprano(["I", "V"], KEY, [None, None]) == []


def test_check_soprano_length_mismatch_raises():
    with pytest.raises(ValueError):
        check_soprano(["I", "V"], KEY, [60])
