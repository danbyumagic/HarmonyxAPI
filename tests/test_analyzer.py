"""Tests for the harmonic analyzer and the FastAPI endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient
from music21 import chord, corpus, key, meter, note, stream

from app.analyzer import (
    ChordAnalysis,
    analyze_score,
    detect_cadences,
    _clean_slices,
    _degree,
    _detect_key,
    _is_passing_or_neighbor_tone,
    _neutralize_non_chord_tones,
    _slice_chords,
)
from app.main import app

client = TestClient(app)


def _c(roman, pitches, duration=1.0, measure=1, beat=1.0, inversion=0, fermata=False):
    return ChordAnalysis(
        measure=measure,
        beat=beat,
        pitches=pitches,
        roman=roman,
        quality="major",
        inversion=inversion,
        duration=duration,
        fermata=fermata,
    )


# --- cleanup pass ----------------------------------------------------------

def test_clean_drops_short_slices():
    slices = [
        _c("I", ["C4", "E4", "G4"], duration=1.0),
        _c("ii", ["D4", "F4"], duration=0.25),  # passing — below threshold
        _c("V", ["G4", "B4", "D5"], duration=1.0),
    ]
    cleaned = _clean_slices(slices, duration_threshold=0.5)
    assert [c.roman for c in cleaned] == ["I", "V"]


def test_clean_merges_repeated_adjacent_chords():
    slices = [
        _c("I", ["C4", "E4", "G4"], duration=1.0),
        _c("I", ["C4", "E4", "G4"], duration=1.0),  # same harmony re-struck
        _c("V", ["G4", "B4", "D5"], duration=1.0),
    ]
    cleaned = _clean_slices(slices, duration_threshold=0.5)
    assert [c.roman for c in cleaned] == ["I", "V"]
    assert cleaned[0].duration == 2.0  # durations accumulated


def test_clean_falls_back_when_threshold_eats_everything():
    slices = [_c("I", ["C4"], duration=0.1), _c("V", ["G4"], duration=0.1)]
    cleaned = _clean_slices(slices, duration_threshold=1.0)
    assert len(cleaned) == 2  # never returns empty


def test_merge_ignores_octave_changes():
    slices = [
        _c("I", ["C4", "E4", "G4"], duration=1.0),
        _c("I", ["C3", "E4", "G4"], duration=1.0),  # voicing change, same pcs
    ]
    cleaned = _clean_slices(slices, duration_threshold=0.5)
    assert len(cleaned) == 1


# --- non-chord-tone classification (A1) ------------------------------------

def test_passing_tone_detected_on_weak_beat():
    # C4 -> D4 -> E4, stepwise same direction, weak beat.
    assert _is_passing_or_neighbor_tone(60, 62, 64, beat_strength=0.25) is True


def test_neighbor_tone_detected_on_weak_beat():
    # C4 -> D4 -> C4, steps away and back, weak beat.
    assert _is_passing_or_neighbor_tone(60, 62, 60, beat_strength=0.25) is True


def test_passing_shape_on_strong_beat_is_not_nct():
    assert _is_passing_or_neighbor_tone(60, 62, 64, beat_strength=1.0) is False


def test_leap_is_not_nct():
    # C4 -> G4 -> E4: not stepwise, so not a passing/neighbor tone.
    assert _is_passing_or_neighbor_tone(60, 67, 64, beat_strength=0.25) is False


def test_boundary_note_is_not_nct():
    # No previous note (start of phrase) -- can't classify.
    assert _is_passing_or_neighbor_tone(None, 62, 64, beat_strength=0.25) is False


def test_neutralize_replaces_passing_tone_with_previous_pitch():
    s = stream.Stream()
    s.append(meter.TimeSignature("4/4"))
    for name in ("C4", "D4", "E4", "C4"):
        s.append(note.Note(name, quarterLength=1.0))
    part = stream.Part()
    part.append(s.flatten())
    score = stream.Score()
    score.append(part)

    cleaned = _neutralize_non_chord_tones(score)
    pitches = [n.pitch.nameWithOctave for n in cleaned.parts[0].flatten().notes]
    assert pitches == ["C4", "C4", "E4", "C4"]


def test_neutralize_reduces_spurious_slices_on_chorale():
    score = corpus.parse("bach/bwv140.7")
    analyzed_key = score.analyze("key")
    raw_before = _slice_chords(score, analyzed_key)
    cleaned_score = _neutralize_non_chord_tones(score)
    raw_after = _slice_chords(cleaned_score, analyzed_key)
    assert len(raw_after) <= len(raw_before)


# --- cadence detection -----------------------------------------------------

def test_degree_strips_figures():
    assert _degree("V7") == "V"
    assert _degree("V65") == "V"
    assert _degree("ii6") == "II"
    assert _degree("bVII") == "VII"


def test_detect_authentic_cadence():
    chords = [_c("V", ["G4"], measure=8), _c("I", ["C4"], measure=8)]
    cadences = detect_cadences(chords, None)
    assert any(c.type == "authentic" for c in cadences)


def test_detect_plagal_and_half():
    plagal = detect_cadences([_c("IV", ["F4"]), _c("I", ["C4"])], None)
    assert any(c.type == "plagal" for c in plagal)
    half = detect_cadences([_c("I", ["C4"]), _c("V", ["G4"])], None)
    assert any(c.type == "half" for c in half)


# --- phrase-end restriction + PAC/IAC refinement (A2) -----------------------

def test_only_phrase_final_pair_flagged_when_fermata_present():
    # I -> V -> I(fermata) -> IV -> I. The mid-phrase I->V ("half") must NOT
    # be reported once a fermata marks a real phrase end -- only the
    # phrase-final pairs count.
    chords = [
        _c("I", ["C4", "E4", "G4"], measure=1),
        _c("V", ["G4", "B4", "D5"], measure=2),
        _c("I", ["C5", "E5", "G5"], measure=3, fermata=True),
        _c("IV", ["F4", "A4", "C5"], measure=4),
        _c("I", ["C4", "E4", "G4"], measure=5),
    ]
    cadences = detect_cadences(chords, None)
    types_by_measure = {c.measure: c.type for c in cadences}
    assert types_by_measure == {3: "authentic", 5: "plagal"}


def test_every_pair_checked_when_no_fermata_present():
    # No fermata anywhere -- fall back to checking every adjacent pair
    # (legacy behavior), since there's no phrase marker to segment on.
    chords = [
        _c("I", ["C4"], measure=1),
        _c("V", ["G4"], measure=2),
        _c("I", ["C4"], measure=3),
    ]
    cadences = detect_cadences(chords, None)
    types = [c.type for c in cadences]
    assert types == ["half", "authentic"]


def test_authentic_cadence_root_position_soprano_on_tonic_is_pac():
    prev = _c("V", ["G3", "B3", "D4"], measure=1, inversion=0)
    curr = _c("I", ["C3", "E3", "C5"], measure=2, inversion=0, fermata=True)
    cadences = detect_cadences([prev, curr], key.Key("C"))
    assert cadences[0].type == "PAC"


def test_authentic_cadence_inverted_tonic_chord_is_iac():
    prev = _c("V", ["G3", "B3", "D4"], measure=1, inversion=0)
    curr = _c("I", ["E3", "G3", "C5"], measure=2, inversion=1, fermata=True)
    cadences = detect_cadences([prev, curr], key.Key("C"))
    assert cadences[0].type == "IAC"


def test_authentic_cadence_soprano_off_tonic_is_iac():
    prev = _c("V", ["G3", "B3", "D4"], measure=1, inversion=0)
    curr = _c("I", ["C3", "E3", "G5"], measure=2, inversion=0, fermata=True)
    cadences = detect_cadences([prev, curr], key.Key("C"))
    assert cadences[0].type == "IAC"


def test_cadences_align_with_fermata_measures_on_real_chorale():
    score = corpus.parse("bach/bwv66.6")
    result = analyze_score(score)
    fermata_measures = {1, 2, 3, 5, 7, 9}
    for cadence in result.cadences:
        assert cadence.measure in fermata_measures


# --- key detection (A4) ----------------------------------------------------

def test_key_picardy_third_keeps_notated_minor_mode():
    """Final major triad on the minor tonic must not flip the mode to major."""
    score = corpus.parse("bach/bwv7.7")  # B minor, ends on B major (Picardy)
    analyzed, confidence = _detect_key(score)
    assert f"{analyzed.tonic.name} {analyzed.mode}" == "B minor"
    assert 0.0 <= confidence <= 1.0


def test_key_does_not_retonicize_final_dominant_as_tonic():
    """Phrases often end on V — final root alone must not become the key."""
    score = corpus.parse("bach/bwv311")  # B minor chorale; often closes on F#
    analyzed, _ = _detect_key(score)
    assert f"{analyzed.tonic.name} {analyzed.mode}" == "B minor"


def test_key_relative_major_minor_prefers_minor_when_notated():
    """Ensemble + structure should not flip a clear G minor chorale to B♭ major."""
    score = corpus.parse("bach/bwv273")
    analyzed, _ = _detect_key(score)
    assert f"{analyzed.tonic.name} {analyzed.mode}" == "G minor"


def test_key_ensemble_fallback_on_unnotated_major_triads():
    """No written Key — ensemble should still land on a major key for I–IV–V–I."""
    s = stream.Stream()
    s.append(meter.TimeSignature("4/4"))
    for pitches in (
        ["C4", "E4", "G4"],
        ["F4", "A4", "C5"],
        ["G4", "B4", "D5"],
        ["C4", "E4", "G4"],
    ):
        s.append(chord.Chord(pitches, quarterLength=1.0))
    analyzed, confidence = _detect_key(s)
    assert analyzed.mode == "major"
    assert analyzed.tonic.pitchClass == 0  # C
    assert 0.0 <= confidence <= 1.0


# --- full pipeline on a real chorale --------------------------------------

def test_analyze_chorale_end_to_end():
    score = corpus.parse("bach/bwv66.6")
    result = analyze_score(score)
    assert result.key == "F# minor"
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.chords) > 0
    first = result.chords[0]
    assert first.roman  # every kept chord has a Roman numeral
    assert first.pitches


def test_analyze_synthetic_progression():
    # I - IV - V - I in C major, as block chords.
    s = stream.Stream()
    s.append(meter.TimeSignature("4/4"))
    for pitches in (["C4", "E4", "G4"], ["F4", "A4", "C5"],
                    ["G4", "B4", "D5"], ["C4", "E4", "G4"]):
        s.append(chord.Chord(pitches, quarterLength=1.0))
    result = analyze_score(s)
    assert "major" in result.key
    romans = [c.roman for c in result.chords]
    assert "I" in romans


# --- API endpoint ----------------------------------------------------------

def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_analyze_endpoint_with_midi():
    # Render a real chorale to MIDI on disk, then post it to the endpoint.
    import os
    import tempfile

    score = corpus.parse("bach/bwv66.6")
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        path = tmp.name
    try:
        score.write("midi", fp=path)
        with open(path, "rb") as fh:
            resp = client.post(
                "/analyze",
                files={"file": ("chorale.mid", fh.read(), "audio/midi")},
            )
    finally:
        os.unlink(path)
    assert resp.status_code == 200
    data = resp.json()
    assert "key" in data and "chords" in data and "cadences" in data
    assert len(data["chords"]) > 0


def test_analyze_rejects_unsupported_type():
    resp = client.post(
        "/analyze",
        files={"file": ("notes.txt", b"not a score", "text/plain")},
    )
    assert resp.status_code == 415


def test_analyze_rejects_empty_file():
    resp = client.post(
        "/analyze",
        files={"file": ("empty.mid", b"", "audio/midi")},
    )
    assert resp.status_code == 400
