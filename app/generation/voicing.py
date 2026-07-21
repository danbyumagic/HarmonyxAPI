"""SATB voicing candidates for a single chord.

Enumerates ways to spell a Roman numeral across four voices, subject to the
*static* hard invariants from ``docs/PARTWRITING-RULES.md`` (§0-§2, and the
§7 doubling carve-outs). Transition-dependent rules (parallels, resolutions --
§3-§6) are evaluated later, per-pair, by ``rules.rule_violations`` once a
candidate sequence is chosen.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Optional

from . import chords as _chords

# Voice ranges as MIDI numbers (PARTWRITING-RULES §0).
S_RANGE = (60, 79)  # C4 .. G5
A_RANGE = (55, 74)  # G3 .. D5
T_RANGE = (48, 67)  # C3 .. G4
B_RANGE = (40, 60)  # E2 .. C4

MAX_UPPER_SPACING = 12  # semitones; S-A and A-T must each be <= an octave


@dataclass(frozen=True)
class Voicing:
    """Four MIDI pitch numbers, stored verbatim in S/A/T/B order.

    Deliberately NOT reordered/sorted on construction -- a voice-crossing
    candidate must be representable so the rule checker can flag it. Contract
    fixed by ``tests/test_partwriting.py``; do not change the field order or
    the constructor signature (``Voicing(s, a, t, b)``).
    """

    s: int
    a: int
    t: int
    b: int


def _in_range(value: int, bounds: tuple[int, int]) -> bool:
    lo, hi = bounds
    return lo <= value <= hi


def _pitches_in_range(pc: int, bounds: tuple[int, int]) -> list[int]:
    """All MIDI numbers with pitch class ``pc`` inside ``bounds`` (inclusive)."""
    lo, hi = bounds
    out = []
    # Start from the first octave-equivalent >= lo, then step by 12.
    start = lo + ((pc - lo) % 12)
    for v in range(start, hi + 1, 12):
        out.append(v)
    return out


def candidate_voicings(
    figure: str,
    key_like: _chords.KeyLike,
    *,
    soprano: Optional[int] = None,
    limit: Optional[int] = 200,
) -> list[Voicing]:
    """Enumerate static-rule-legal SATB voicings of ``figure`` in ``key_like``.

    Every voice is assigned a pitch class that is a member of the chord (a
    triad tone doubled if the chord has only 3 distinct pitch classes; all 4
    distinct tones covered if it's a seventh chord). The bass always carries
    the chord's inversion-determined bass note (``chord_members(...)["bass"]``)
    per PARTWRITING-RULES' notation. Every returned voicing already satisfies
    the *static* hard invariants: range (§0), spacing (§1), crossing (§2), and
    the doubled-leading-tone / doubled-seventh carve-outs (§7).

    If ``soprano`` (a MIDI int) is given, only voicings with that exact
    soprano are returned. The soprano must be a chord tone of ``figure``
    (pitch class in ``chord_pitch_classes``); otherwise this returns ``[]``,
    matching any other "no legal voicings" case. Callers that want per-beat
    diagnostics can still use ``realize.check_soprano`` first.

    ``limit`` caps the returned candidate count (voicing space grows quickly
    for seventh chords); pass ``None`` for no cap.
    """
    members = _chords.chord_members(figure, key_like)
    chord_pcs = [pc for pc in (members["root"], members["third"], members["fifth"], members["seventh"]) if pc is not None]
    bass_pc = members["bass"]
    lt_pc = _chords.leading_tone_pitch_class(key_like)
    seventh_pc = members["seventh"]

    if soprano is not None:
        # Reject non-chord-tone sopranos early; otherwise A/T/B can still cover
        # the chord and we'd return a "valid" voicing with a wrong S pitch.
        if (soprano % 12) not in _chords.chord_pitch_classes(figure, key_like):
            return []
        soprano_options = [soprano]
    else:
        soprano_options = [p for pc in chord_pcs for p in _pitches_in_range(pc, S_RANGE)]

    bass_options = _pitches_in_range(bass_pc, B_RANGE)

    out: list[Voicing] = []
    for b in bass_options:
        for s in soprano_options:
            if s < b:
                continue
            if not _in_range(s, S_RANGE) or not _in_range(b, B_RANGE):
                continue
            alto_options = [p for pc in chord_pcs for p in _pitches_in_range(pc, A_RANGE) if b <= p <= s]
            tenor_options = [p for pc in chord_pcs for p in _pitches_in_range(pc, T_RANGE) if b <= p <= s]
            for a, t in itertools.product(alto_options, tenor_options):
                if not (s >= a >= t >= b):
                    continue
                if s - a > MAX_UPPER_SPACING or a - t > MAX_UPPER_SPACING:
                    continue
                v = Voicing(s, a, t, b)
                if not _covers_all_chord_tones(v, chord_pcs):
                    continue
                if _count_pc(v, lt_pc) > 1:
                    continue
                if seventh_pc is not None and _count_pc(v, seventh_pc) > 1:
                    continue
                out.append(v)
                if limit is not None and len(out) >= limit:
                    return out
    return out


def _covers_all_chord_tones(v: Voicing, chord_pcs: list[int]) -> bool:
    present = {v.s % 12, v.a % 12, v.t % 12, v.b % 12}
    return set(chord_pcs).issubset(present)


def _count_pc(v: Voicing, pc: int) -> int:
    return sum(1 for x in (v.s, v.a, v.t, v.b) if x % 12 == pc)
