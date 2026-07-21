"""Harmonic analysis core built on music21.

The pipeline is deliberately small:

    parse -> key analysis -> chordify -> roman numerals -> cleanup

`chordify()` collapses a multi-voice texture into a stream of vertical
sonorities.  On real scores that produces a lot of junk: passing tones and
suspensions momentarily spell "chords" that no analyst would label.  The
cleanup pass (`_clean_slices`) is where the deterministic analysis becomes
usable -- it drops slices below a duration threshold and merges repeated
adjacent chords.

Scope (v1): four-part chorale texture in a single major/minor key, no
modulation.  See the README for the honest list of what this does and does
not handle.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Optional

from music21 import chord, converter, key as m21key, pitch, roman, stream


# A note counts as metrically weak (and thus eligible to be a non-chord tone)
# below this beatStrength. 0.5 keeps downbeats and strong sub-beats (e.g. beat
# 3 of 4/4) as real harmony while catching upbeats and offbeats.
NCT_BEAT_STRENGTH_THRESHOLD = 0.5


# A slice shorter than this (in quarter lengths) is treated as passing motion
# rather than a real harmony.  An eighth note is 0.5; the default keeps
# quarter-note-and-longer harmonies and discards most passing eighths.
DEFAULT_DURATION_THRESHOLD = 0.5


@dataclass
class ChordAnalysis:
    """A single analyzed harmony."""

    measure: int
    beat: float
    pitches: List[str]
    roman: str
    quality: str
    inversion: int
    duration: float = 0.0

    def to_dict(self) -> dict:
        return {
            "measure": self.measure,
            "beat": self.beat,
            "pitches": self.pitches,
            "roman": self.roman,
            "quality": self.quality,
            "inversion": self.inversion,
        }


@dataclass
class Cadence:
    measure: int
    type: str

    def to_dict(self) -> dict:
        return {"measure": self.measure, "type": self.type}


@dataclass
class AnalysisResult:
    key: str
    confidence: float
    chords: List[ChordAnalysis] = field(default_factory=list)
    cadences: List[Cadence] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "confidence": round(self.confidence, 3),
            "chords": [c.to_dict() for c in self.chords],
            "cadences": [c.to_dict() for c in self.cadences],
        }


class AnalysisError(Exception):
    """Raised when a score cannot be parsed or analyzed."""


def analyze_score(
    source,
    *,
    fmt: Optional[str] = None,
    duration_threshold: float = DEFAULT_DURATION_THRESHOLD,
) -> AnalysisResult:
    """Analyze a score and return chord-by-chord Roman numerals.

    ``source`` may be a path to a MusicXML/MIDI file or a raw string of
    score data.  ``fmt`` is an optional music21 format hint (e.g. ``"midi"``,
    ``"musicxml"``); music21 usually infers it from the file extension.
    """
    score = _parse(source, fmt)
    analyzed_key = score.analyze("key")

    neutralized = _neutralize_non_chord_tones(score)
    raw = _slice_chords(neutralized, analyzed_key)
    cleaned = _clean_slices(raw, duration_threshold)

    return AnalysisResult(
        key=_key_name(analyzed_key),
        confidence=_key_confidence(analyzed_key),
        chords=cleaned,
        cadences=detect_cadences(cleaned, analyzed_key),
    )


def _parse(source, fmt: Optional[str]) -> stream.Score:
    # Already-parsed streams (e.g. from music21's corpus in the eval harness)
    # pass straight through.
    if isinstance(source, stream.Stream):
        return source
    try:
        if fmt:
            parsed = converter.parse(source, format=fmt)
        else:
            parsed = converter.parse(source)
    except Exception as exc:  # music21 raises a variety of parse errors
        raise AnalysisError(f"Could not parse score: {exc}") from exc
    return parsed


def _is_passing_or_neighbor_tone(
    prev_ps: Optional[float],
    cur_ps: float,
    next_ps: Optional[float],
    beat_strength: float,
    strength_threshold: float = NCT_BEAT_STRENGTH_THRESHOLD,
) -> bool:
    """Classify a note as a passing or neighbor tone from melodic + metric shape.

    A passing tone steps continuously between two other pitches in the same
    direction (e.g. C-D-E); a neighbor tone steps away from and back to the
    same pitch (e.g. C-D-C). Both patterns only count as a non-chord tone on
    a metrically weak beat -- the same shape landing on a strong beat is a
    real (if momentarily dissonant-sounding) harmony, not ornamentation.
    """
    if prev_ps is None or next_ps is None:
        return False
    if beat_strength >= strength_threshold:
        return False

    step_in = cur_ps - prev_ps
    step_out = next_ps - cur_ps
    if not (0 < abs(step_in) <= 2 and 0 < abs(step_out) <= 2):
        return False

    if prev_ps == next_ps:
        return True  # neighbor tone
    return (step_in > 0) == (step_out > 0)  # passing tone: continues direction


def _neutralize_non_chord_tones(score: stream.Score) -> stream.Score:
    """Replace melodic passing/neighbor tones with the pitch they decorate.

    Operates per-part (chordify has already flattened voices together and
    lost this context) on a deep copy, so the original score is untouched.
    Each part's note stream is snapshotted before any mutation, so a note's
    classification is always based on its original neighbors, not ones
    already rewritten earlier in the pass.
    """
    cleaned = copy.deepcopy(score)

    parts = cleaned.getElementsByClass(stream.Part)
    if not parts:
        # Not a multi-part Score (e.g. a single flat Stream of block chords
        # in tests) -- there is no per-voice melodic line to neutralize.
        parts = [cleaned]

    for part in parts:
        notes = [n for n in part.flatten().notes if not n.isChord]
        original_ps = [n.pitch.ps for n in notes]

        for i, this_note in enumerate(notes):
            prev_ps = original_ps[i - 1] if i > 0 else None
            next_ps = original_ps[i + 1] if i < len(notes) - 1 else None
            if _is_passing_or_neighbor_tone(
                prev_ps, original_ps[i], next_ps, this_note.beatStrength
            ):
                this_note.pitch = pitch.Pitch(notes[i - 1].pitch.nameWithOctave)

    return cleaned


def _slice_chords(score: stream.Score, analyzed_key: m21key.Key) -> List[ChordAnalysis]:
    """Chordify the score and label each vertical sonority."""
    chordified = score.chordify()
    slices: List[ChordAnalysis] = []

    for element in chordified.recurse().getElementsByClass(chord.Chord):
        if not element.pitches:
            continue

        roman_figure = _roman_figure(element, analyzed_key)
        if roman_figure is None:
            continue

        slices.append(
            ChordAnalysis(
                measure=element.measureNumber or 0,
                beat=round(float(element.beat), 3),
                pitches=[p.nameWithOctave for p in element.pitches],
                roman=roman_figure,
                quality=_chord_quality(element),
                inversion=_safe_inversion(element),
                duration=float(element.quarterLength),
            )
        )

    return slices


def _clean_slices(
    slices: List[ChordAnalysis], duration_threshold: float
) -> List[ChordAnalysis]:
    """The craft step: drop passing-tone junk and merge repeats.

    Two passes:

    1. Drop slices shorter than ``duration_threshold`` -- these are almost
       always passing/neighbor motion that chordify spelled as a chord.
    2. Merge adjacent slices with the same Roman numeral and pitch-class set,
       accumulating their duration.  This collapses a harmony that is simply
       re-struck or held across beats into one entry.
    """
    kept = [s for s in slices if s.duration >= duration_threshold]
    if not kept:
        # Threshold ate everything (very short score / dense passing motion);
        # fall back to the raw slices so we never return an empty analysis.
        kept = slices

    merged: List[ChordAnalysis] = []
    for current in kept:
        if merged and _same_harmony(merged[-1], current):
            merged[-1].duration += current.duration
            continue
        merged.append(current)

    return merged


def _same_harmony(a: ChordAnalysis, b: ChordAnalysis) -> bool:
    return a.roman == b.roman and _pitch_classes(a) == _pitch_classes(b)


def _pitch_classes(c: ChordAnalysis) -> frozenset:
    # Compare by pitch name without octave so a voicing change (e.g. an inner
    # voice leaping an octave) does not count as a new harmony.
    return frozenset(p.rstrip("0123456789-") for p in c.pitches)


def detect_cadences(
    chords: List[ChordAnalysis], analyzed_key: m21key.Key
) -> List[Cadence]:
    """Detect cadences from adjacent Roman-numeral pairs.

    A lightweight, honest heuristic -- it inspects consecutive harmonies for
    the classic two-chord cadential motions rather than doing full phrase
    segmentation:

      * authentic   V(7) -> I/i
      * plagal      IV/iv -> I/i
      * half        anything -> V
      * deceptive   V(7) -> vi/VI
    """
    cadences: List[Cadence] = []

    for prev, curr in zip(chords, chords[1:]):
        prev_deg = _degree(prev.roman)
        curr_deg = _degree(curr.roman)

        cadence_type: Optional[str] = None
        if prev_deg == "V" and curr_deg == "I":
            cadence_type = "authentic"
        elif prev_deg == "IV" and curr_deg == "I":
            cadence_type = "plagal"
        elif prev_deg == "V" and curr_deg == "VI":
            cadence_type = "deceptive"
        elif curr_deg == "V":
            cadence_type = "half"

        if cadence_type:
            cadences.append(Cadence(measure=curr.measure, type=cadence_type))

    return cadences


def _degree(figure: str) -> str:
    """Reduce a Roman-numeral figure to its bare scale degree.

    Strips inversion figures, sevenths, and accidentals so that ``V7``,
    ``V6``, and ``V65`` all compare equal to ``V``.  Returns the degree in
    upper case so major/minor spellings of the same degree match.
    """
    core = []
    started = False
    for ch in figure:
        if ch in "iIvV":
            core.append(ch)
            started = True
        elif not started and ch in "b#-+♭♯":
            # Leading accidental (e.g. the 'b' in 'bVII') — skip it.
            continue
        else:
            break
    return "".join(core).upper()


def _roman_figure(element: chord.Chord, analyzed_key: m21key.Key) -> Optional[str]:
    try:
        rn = roman.romanNumeralFromChord(element, analyzed_key)
    except Exception:
        return None
    return rn.figure


def _chord_quality(element: chord.Chord) -> str:
    quality = element.quality  # 'major' | 'minor' | 'diminished' | 'augmented' | 'other'
    if quality == "other":
        # Fall back to a human-readable name for seventh chords and the like.
        try:
            return element.commonName
        except Exception:
            return "other"
    return quality


def _safe_inversion(element: chord.Chord) -> int:
    try:
        return int(element.inversion())
    except Exception:
        return 0


def _key_name(analyzed_key: m21key.Key) -> str:
    # music21 prints "f# minor"; present it as "F# minor".
    return f"{analyzed_key.tonic.name} {analyzed_key.mode}"


def _key_confidence(analyzed_key: m21key.Key) -> float:
    """music21's key-analysis certainty, clamped to [0, 1]."""
    try:
        certainty = analyzed_key.tonalCertainty()
    except Exception:
        certainty = getattr(analyzed_key, "correlationCoefficient", 0.0)
    if certainty is None:
        return 0.0
    return max(0.0, min(1.0, float(certainty)))
