"""Tests for app.generation.chords (Milestone 1a)."""

from __future__ import annotations

from app.generation.chords import (
    chord_members,
    chord_pitch_classes,
    is_chord_tone,
    leading_tone_pitch_class,
    midi_to_name,
    normalize_rn,
    rn_agreement,
    tonic_pitch_class,
)


def test_chord_pitch_classes_major_triads():
    assert chord_pitch_classes("I", "C major") == [0, 4, 7]  # C E G
    assert chord_pitch_classes("V", "C major") == [2, 7, 11]  # G B D


def test_chord_pitch_classes_seventh():
    assert chord_pitch_classes("V7", "C major") == [2, 5, 7, 11]  # G B D F


def test_chord_pitch_classes_minor_key_raised_leading_tone():
    # A minor V should spell E-G#-B (raised 7th), not E-G-B.
    pcs = chord_pitch_classes("V", "A minor")
    assert 8 in pcs  # G# = pitch class 8


def test_chord_members_root_position():
    m = chord_members("I", "C major")
    assert m["root"] == 0 and m["third"] == 4 and m["fifth"] == 7
    assert m["seventh"] is None
    assert m["bass"] == 0  # root position -> bass == root


def test_chord_members_inversion_changes_bass_not_root():
    m = chord_members("V6", "C major")
    assert m["root"] == 7  # G
    assert m["bass"] == 11  # third (B) is in the bass


def test_chord_members_seventh_chord():
    m = chord_members("V7", "C major")
    assert m["seventh"] == 5  # F


def test_chord_members_cad64_bass_is_dominant():
    m = chord_members("Cad64", "C major")
    assert m["bass"] == 7  # scale-degree 5 (G) in the bass


def test_is_chord_tone_accepts_and_rejects():
    assert is_chord_tone("G4", "V", "C major") is True
    assert is_chord_tone("C4", "V", "C major") is False  # C is not in V (G-B-D)
    assert is_chord_tone(67, "I", "C major") is True  # MIDI int for G4


def test_tonic_and_leading_tone_pitch_class():
    assert tonic_pitch_class("C major") == 0
    assert leading_tone_pitch_class("C major") == 11  # B
    assert tonic_pitch_class("A minor") == 9
    assert leading_tone_pitch_class("A minor") == 8  # G#


def test_normalize_rn_accidental_insensitive_degree():
    assert normalize_rn("bVII")[0] == normalize_rn("VII")[0] == 7


def test_normalize_rn_inversion_and_seventh():
    degree, quality, inversion, seventh = normalize_rn("V65")
    assert degree == 5
    assert inversion == 1
    assert seventh is True


def test_rn_agreement_primary_ignores_inversion_and_seventh():
    # V vs V7: same degree+quality -> agree on the primary metric...
    assert rn_agreement("V", "V7") is True
    # ...but not on the strict metric (seventh differs).
    assert rn_agreement("V", "V7", strict=True) is False


def test_rn_agreement_different_quality_disagrees():
    assert rn_agreement("V", "v") is False  # major vs minor dominant


def test_midi_to_name_returns_pitch_name_with_octave():
    assert midi_to_name(72) == "C5"
    assert midi_to_name(61) == "C#4"
