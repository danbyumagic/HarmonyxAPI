"""Tests for the harmonic analyzer and the FastAPI endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient
from music21 import chord, corpus, meter, stream

from app.analyzer import (
    ChordAnalysis,
    analyze_score,
    detect_cadences,
    _clean_slices,
    _degree,
)
from app.main import app

client = TestClient(app)


def _c(roman, pitches, duration=1.0, measure=1, beat=1.0):
    return ChordAnalysis(
        measure=measure,
        beat=beat,
        pitches=pitches,
        roman=roman,
        quality="major",
        inversion=0,
        duration=duration,
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
