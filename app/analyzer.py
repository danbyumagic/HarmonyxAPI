"""Harmonic analysis core built on music21.

The pipeline is deliberately small:

    parse -> key analysis -> chordify -> roman numerals -> cleanup

`chordify()` collapses a multi-voice texture into a stream of vertical
sonorities.  On real scores that produces a lot of junk: passing tones and
suspensions momentarily spell "chords" that no analyst would label.  The
cleanup pass (`_clean_slices`) is where the deterministic analysis becomes
usable -- it drops slices below a duration threshold and merges repeated
adjacent chords.

Key detection (A4) prefers notated key + final-chord tonic (Picardy-aware),
with a multi-algorithm ensemble fallback when the score has no written key
(e.g. MIDI).

Scope (v1): four-part chorale texture in a single major/minor key, no
modulation.  See the README for the honest list of what this does and does
not handle.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from music21 import chord, converter, expressions, key as m21key, pitch, roman, stream

# Profile algorithms music21 ships for key estimation. Used when the score
# has no written Key / when we need a fallback for unnotated input.
_KEY_ALGORITHMS = (
    "KrumhanslSchmuckler",
    "AardenEssen",
    "BellmanBudge",
    "TemperleyKostkaPayne",
    "SimpleWeights",
)

_PC_NAMES_SHARP = (
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
)
_PC_NAMES_FLAT = (
    "C", "D-", "D", "E-", "E", "F", "G-", "G", "A-", "A", "B-", "B",
)


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
    fermata: bool = False

    def to_dict(self) -> dict:
        return {
            "measure": self.measure,
            "beat": self.beat,
            "pitches": self.pitches,
            "roman": self.roman,
            "quality": self.quality,
            "inversion": self.inversion,
            "fermata": self.fermata,
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
    analyzed_key, key_confidence = _detect_key(score)

    neutralized = _neutralize_non_chord_tones(score)
    raw = _slice_chords(neutralized, analyzed_key)
    cleaned = _clean_slices(raw, duration_threshold)

    return AnalysisResult(
        key=_key_name(analyzed_key),
        confidence=key_confidence,
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
                fermata=_has_fermata(element),
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
            merged[-1].fermata = merged[-1].fermata or current.fermata
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
    """Detect cadences at phrase ends from adjacent Roman-numeral pairs.

    A lightweight, honest heuristic -- it inspects the final two harmonies of
    each phrase for the classic two-chord cadential motions, rather than
    scanning every adjacent pair (a mid-phrase V->I is passing harmony, not a
    cadence). Phrases are segmented on fermatas, the idiomatic phrase-end
    marker in chorale notation. If no chord carries a fermata (e.g. a MIDI
    source, which doesn't encode them), there is no phrase marker to segment
    on, so every adjacent pair is checked instead -- the old, permissive
    behavior:

      * authentic (PAC/IAC)   V(7) -> I/i
      * plagal                IV/iv -> I/i
      * half                  anything -> V
      * deceptive             V(7) -> vi/VI

    An authentic cadence is refined into a perfect authentic cadence (PAC)
    when both chords are in root position and the final chord's highest
    pitch (the soprano, in this four-part texture) is the tonic; otherwise
    it's an imperfect authentic cadence (IAC).
    """
    if any(c.fermata for c in chords):
        # Phrase markers are present -- only the final pair of each phrase
        # is a cadence candidate; a mid-phrase V->I is passing harmony.
        pairs = [
            (phrase[-2], phrase[-1])
            for phrase in _segment_phrases(chords)
            if len(phrase) >= 2
        ]
    else:
        # No fermata anywhere (e.g. a MIDI source) -- no phrase marker to
        # segment on, so fall back to checking every adjacent pair.
        pairs = list(zip(chords, chords[1:]))

    cadences: List[Cadence] = []
    for prev, curr in pairs:
        cadence_type = _classify_cadence(prev, curr, analyzed_key)
        if cadence_type:
            cadences.append(Cadence(measure=curr.measure, type=cadence_type))

    return cadences


def _segment_phrases(chords: List[ChordAnalysis]) -> List[List[ChordAnalysis]]:
    """Split a chord sequence into phrases ending at each fermata."""
    phrases: List[List[ChordAnalysis]] = []
    current: List[ChordAnalysis] = []
    for c in chords:
        current.append(c)
        if c.fermata:
            phrases.append(current)
            current = []
    if current:
        phrases.append(current)

    return phrases


def _classify_cadence(
    prev: ChordAnalysis, curr: ChordAnalysis, analyzed_key: Optional[m21key.Key]
) -> Optional[str]:
    prev_deg = _degree(prev.roman)
    curr_deg = _degree(curr.roman)

    if prev_deg == "V" and curr_deg == "I":
        return _classify_authentic(prev, curr, analyzed_key)
    if prev_deg == "IV" and curr_deg == "I":
        return "plagal"
    if prev_deg == "V" and curr_deg == "VI":
        return "deceptive"
    if curr_deg == "V":
        return "half"
    return None


def _classify_authentic(
    prev: ChordAnalysis, curr: ChordAnalysis, analyzed_key: Optional[m21key.Key]
) -> str:
    """Refine an authentic V->I cadence into PAC or IAC.

    PAC requires both chords in root position and the soprano landing on the
    tonic. Without a key (unit tests exercising the bare degree logic pass
    ``None``), there's no tonic to check against, so fall back to the
    pre-refinement label.
    """
    if analyzed_key is None:
        return "authentic"

    root_position = prev.inversion == 0 and curr.inversion == 0
    soprano_on_tonic = _soprano_pitch_class(curr) == analyzed_key.tonic.name
    return "PAC" if (root_position and soprano_on_tonic) else "IAC"


def _soprano_pitch_class(c: ChordAnalysis) -> str:
    # Highest-sounding pitch in a four-part texture is the soprano.
    top = max(c.pitches, key=lambda p: pitch.Pitch(p).ps)
    return pitch.Pitch(top).name


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


def _has_fermata(element: chord.Chord) -> bool:
    return any(isinstance(e, expressions.Fermata) for e in element.expressions)


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


def _detect_key(score: stream.Stream) -> Tuple[m21key.Key, float]:
    """Choose a global key for the score (A4).

    Always runs a multi-algorithm profile ensemble, then re-ranks with
    structural evidence (first/last chord roots, raised leading tones). A
    written ``Key``, when present, is a soft prior — enough to break ties and
    favour the notated mode (Picardy-safe) without overriding clear pitch
    evidence, and without re-tonicizing every phrase that ends on V.
    """
    first = _extreme_chord(score, which="first")
    final = _extreme_chord(score, which="last")
    return _ensemble_key(
        score,
        first=first,
        final=final,
        notated=_notated_key(score),
    )


def _notated_key(score: stream.Stream) -> Optional[m21key.Key]:
    """First explicit Key in the score, if any.

    music21 chorales typically carry ``key.Key`` objects (with mode). Plain
    ``KeySignature`` objects alone are mode-ambiguous (D major vs B minor);
    those are left to the ensemble unless a full Key is present.
    """
    keys = list(score.recurse().getElementsByClass(m21key.Key))
    if keys:
        return keys[0]
    return None


def _extreme_chord(
    score: stream.Stream, *, which: str
) -> Optional[chord.Chord]:
    """First or last vertical sonority via chordify."""
    chords = [
        c
        for c in score.chordify().recurse().getElementsByClass(chord.Chord)
        if c.pitches
    ]
    if not chords:
        return None
    return chords[0] if which == "first" else chords[-1]


def _chord_root_pc(c: chord.Chord) -> Optional[int]:
    try:
        return int(c.root().pitchClass)
    except Exception:
        try:
            return int(c.bass().pitchClass)
        except Exception:
            if c.pitches:
                return int(c.pitches[0].pitchClass)
            return None


def _triad_mode(c: chord.Chord) -> Optional[str]:
    quality = c.quality
    if quality in ("major", "minor"):
        return quality
    return None


def _key_from_pc(
    pc: int, mode: str, *, prefer_flats: bool = False
) -> m21key.Key:
    names = _PC_NAMES_FLAT if prefer_flats else _PC_NAMES_SHARP
    return m21key.Key(names[pc % 12], mode)


def _key_id(k: m21key.Key) -> Tuple[int, str]:
    return (int(k.tonic.pitchClass), k.mode)


# Soft prior for a written Key. Large enough to break near-ties and prefer
# the notated mode, small enough that strong profile+structure evidence can
# still win (important when the MusicXML Key disagrees with the sounding key).
_NOTATED_KEY_PRIOR = 2.0


def _ensemble_key(
    score: stream.Stream,
    *,
    first: Optional[chord.Chord],
    final: Optional[chord.Chord],
    notated: Optional[m21key.Key] = None,
) -> Tuple[m21key.Key, float]:
    """Vote across profile algorithms; break ties with structural evidence."""
    weights: Dict[Tuple[int, str], float] = defaultdict(float)
    candidates: Dict[Tuple[int, str], m21key.Key] = {}

    for alg in _KEY_ALGORITHMS:
        try:
            analyzed = score.analyze(alg)
        except Exception:
            continue
        _accumulate_key_candidate(analyzed, weights, candidates, primary=True)
        for alt in (getattr(analyzed, "alternateInterpretations", None) or [])[:3]:
            if isinstance(alt, m21key.Key):
                _accumulate_key_candidate(
                    alt, weights, candidates, primary=False
                )

    if notated is not None:
        kid = _key_id(notated)
        weights[kid] += _NOTATED_KEY_PRIOR
        candidates.setdefault(kid, notated)

    # Bare key signatures (mode-ambiguous) contribute mild major/minor priors.
    for ks in score.recurse().getElementsByClass(m21key.KeySignature):
        if isinstance(ks, m21key.Key):
            continue  # already handled via notated Key
        for mode in ("major", "minor"):
            try:
                k = ks.asKey(mode)
            except Exception:
                continue
            kid = _key_id(k)
            weights[kid] += 0.35
            candidates.setdefault(kid, k)

    if final is not None:
        fpc = _chord_root_pc(final)
        fmode = _triad_mode(final)
        if fpc is not None:
            for mode in ((fmode,) if fmode else ("major", "minor")):
                k = _key_from_pc(fpc, mode)
                kid = _key_id(k)
                weights[kid] += 0.5
                candidates.setdefault(kid, k)

    if not candidates:
        # Absolute last resort: music21 default.
        fallback = score.analyze("key")
        return fallback, _key_confidence(fallback)

    best_key: Optional[m21key.Key] = None
    best_score = float("-inf")
    for kid, k in candidates.items():
        total = weights[kid] + _structural_key_bonus(score, k, first, final)
        if total > best_score:
            best_score = total
            best_key = k

    assert best_key is not None
    # Map the winning structural score into a rough [0, 1] confidence.
    confidence = max(0.0, min(1.0, best_score / 12.0))
    # Prefer music21's own correlation when the winner came from a profile.
    profile_conf = _key_confidence(best_key)
    return best_key, max(confidence, profile_conf * 0.9)


def _accumulate_key_candidate(
    k: m21key.Key,
    weights: Dict[Tuple[int, str], float],
    candidates: Dict[Tuple[int, str], m21key.Key],
    *,
    primary: bool,
) -> None:
    kid = _key_id(k)
    corr = float(getattr(k, "correlationCoefficient", 0.0) or 0.0)
    if primary:
        weights[kid] += 1.0 + max(0.0, corr)
    else:
        weights[kid] += 0.35 + 0.35 * max(0.0, corr)
    prev = candidates.get(kid)
    if prev is None or corr >= float(
        getattr(prev, "correlationCoefficient", 0.0) or 0.0
    ):
        candidates[kid] = k


def _structural_key_bonus(
    score: stream.Stream,
    k: m21key.Key,
    first: Optional[chord.Chord],
    final: Optional[chord.Chord],
) -> float:
    """Extra weight from openings/closings and raised leading tones."""
    bonus = 0.0
    tonic_pc = int(k.tonic.pitchClass)

    if final is not None:
        fpc = _chord_root_pc(final)
        if fpc == tonic_pc:
            bonus += 4.0
            fmode = _triad_mode(final)
            if fmode == k.mode:
                bonus += 0.75
            elif k.mode == "minor" and fmode == "major":
                bonus += 0.6  # Picardy third on the minor tonic
            elif k.mode == "major" and fmode == "minor":
                bonus -= 0.75

    if first is not None:
        if _chord_root_pc(first) == tonic_pc:
            bonus += 1.75

    # Raised leading tone supports minor; lots of subtonic without LT weakens it.
    if k.mode == "minor":
        raised, subtonic = _leading_tone_counts(score, tonic_pc)
        if raised > subtonic:
            bonus += 2.0
        elif raised < subtonic:
            bonus -= 0.75
    else:
        # If the relative minor's raised LT is common and we close on that
        # minor tonic, prefer the relative minor instead.
        rel = k.relative
        raised, _ = _leading_tone_counts(score, int(rel.tonic.pitchClass))
        if (
            final is not None
            and _chord_root_pc(final) == int(rel.tonic.pitchClass)
            and raised >= 3
        ):
            bonus -= 1.5

    return bonus


def _leading_tone_counts(
    score: stream.Stream, tonic_pc: int
) -> Tuple[int, int]:
    """Counts of raised LT (tonic+11) vs natural subtonic (tonic+10)."""
    lt_pc = (tonic_pc + 11) % 12
    sub_pc = (tonic_pc + 10) % 12
    raised = 0
    subtonic = 0
    for n in score.recurse().notes:
        pitches = n.pitches if n.isChord else (n.pitch,)
        for p in pitches:
            if p.pitchClass == lt_pc:
                raised += 1
            elif p.pitchClass == sub_pc:
                subtonic += 1
    return raised, subtonic
