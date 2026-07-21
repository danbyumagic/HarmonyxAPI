"""Golden fixtures for the part-writing HARD INVARIANTS (PARTWRITING-RULES §0–§7).

These tests are the executable spec for the SATB engine's rule checker. They are
**pre-written on purpose** so the implementation is graded against a fixed target
— do not edit them to match an implementation; implement the engine to satisfy
them. See `docs/PARTWRITING-RULES.md` for the authoritative definitions.

Until the engine modules exist, `importorskip` makes this whole module skip, so
CI stays green. The moment `app/generation/voicing.py` and
`app/generation/rules.py` exist, these fixtures activate.

CONTRACT the engine must satisfy (see PARTWRITING-RULES §"How this maps to code"):
- `app.generation.voicing.Voicing(s, a, t, b)` — a dataclass of four MIDI ints,
  stored verbatim in S/A/T/B order (NOT reordered — a crossing must be
  representable).
- `app.generation.rules.rule_violations(prev, cur, ctx) -> list[RuleViolation]`
  - `prev`: the previous `Voicing`, or `None` for the first chord (then only
    static rules on `cur` apply — no transition rules).
  - `cur`: the current `Voicing`.
  - `ctx`: a dict `{"key": str, "prev_roman": str|None, "cur_roman": str}`.
  - Each `RuleViolation` has a `.rule` attribute holding one of the canonical
    slugs below.
- Canonical rule slugs (this set is the contract):
  "range", "spacing", "crossing", "overlap",
  "parallel_fifths", "parallel_octaves", "direct",
  "leading_tone", "seventh",
  "doubled_leading_tone", "doubled_seventh".

Semantics the fixtures assume:
- Static rules (checked on `cur` even when `prev is None`): range, spacing,
  crossing, doubled_leading_tone, doubled_seventh.
- Transition rules (need `prev`): overlap, parallel_fifths, parallel_octaves,
  direct, leading_tone, seventh.
- `leading_tone`: at a dominant→tonic motion (prev_roman a V-type containing the
  key's leading tone), the LT in an OUTER voice (S or B) must resolve up by
  semitone to the tonic; else flag.
- `seventh`: the chordal 7th of `prev` must resolve DOWN by step in `cur`.
- `direct`: outer voices (S & B) in similar motion into a P5/P8 with the soprano
  arriving by LEAP (> 2 semitones); stepwise soprano arrival is allowed.
"""

from __future__ import annotations

import pytest
from music21 import pitch as m21pitch

voicing_mod = pytest.importorskip("app.generation.voicing")
rules_mod = pytest.importorskip("app.generation.rules")
Voicing = voicing_mod.Voicing
rule_violations = rules_mod.rule_violations

KEY = "C major"


def _m(name: str) -> int:
    return m21pitch.Pitch(name).midi


def vc(s: str, a: str, t: str, b: str) -> "Voicing":
    """Build a Voicing from note names, in S/A/T/B order, WITHOUT reordering."""
    return Voicing(_m(s), _m(a), _m(t), _m(b))


def ctx(cur_roman: str, prev_roman: str | None = None, key: str = KEY) -> dict:
    return {"key": key, "prev_roman": prev_roman, "cur_roman": cur_roman}


def slugs(prev, cur, context) -> set[str]:
    return {v.rule for v in rule_violations(prev, cur, context)}


# --- §0 voice ranges -------------------------------------------------------

def test_range_soprano_too_high():
    v = vc("C6", "G4", "E4", "C3")            # C major, soprano C6 > G5
    assert "range" in slugs(None, v, ctx("I"))


def test_range_bass_too_low():
    v = vc("G4", "E4", "C4", "C2")            # bass C2 < E2
    assert "range" in slugs(None, v, ctx("I"))


def test_range_all_in_range_ok():
    v = vc("C5", "G4", "E4", "C3")            # all four in range
    assert "range" not in slugs(None, v, ctx("I"))


# --- §1 spacing ------------------------------------------------------------

def test_spacing_upper_voices_gt_octave():
    v = vc("G5", "E4", "C4", "C3")            # S-A = 15 semitones > octave
    assert "spacing" in slugs(None, v, ctx("I"))


def test_spacing_tenor_bass_gt_octave_allowed():
    v = vc("C5", "G4", "E4", "E2")            # T-B huge but allowed; upper spacing fine
    assert "spacing" not in slugs(None, v, ctx("I"))


# --- §2 crossing & overlap -------------------------------------------------

def test_voice_crossing_within_voicing():
    v = Voicing(_m("E4"), _m("G4"), _m("C4"), _m("C3"))  # alto above soprano
    assert "crossing" in slugs(None, v, ctx("I"))


def test_voice_overlap_across_transition():
    prev = vc("C5", "G4", "E4", "C3")         # tenor E4 = 64
    cur = vc("D5", "D4", "B3", "G3")          # alto D4 = 62 < prev tenor 64
    assert "overlap" in slugs(prev, cur, ctx("V", prev_roman="I"))


# --- §3 parallel perfect fifths / octaves ----------------------------------

def test_parallel_fifths():
    prev = vc("G4", "E4", "C4", "C3")         # outer G4/C3 = P5
    cur = vc("A4", "F4", "D4", "D3")          # outer A4/D3 = P5, both up
    assert "parallel_fifths" in slugs(prev, cur, ctx("ii", prev_roman="I"))


def test_parallel_octaves():
    prev = vc("C5", "G4", "E4", "C4")         # outer C5/C4 = P8
    cur = vc("D5", "A4", "F4", "D4")          # outer D5/D4 = P8, both up
    assert "parallel_octaves" in slugs(prev, cur, ctx("ii", prev_roman="I"))


def test_repeated_chord_no_parallels():
    v = vc("G4", "E4", "C4", "C3")            # identical prev/cur → no motion
    s = slugs(v, v, ctx("I", prev_roman="I"))
    assert "parallel_fifths" not in s and "parallel_octaves" not in s


# --- §4 direct (hidden) fifths / octaves in outer voices -------------------

def test_direct_fifth_soprano_leap():
    prev = vc("C5", "E4", "C4", "C3")
    cur = vc("G5", "E4", "C4", "C4")          # outer → P5, soprano leaps C5→G5
    assert "direct" in slugs(prev, cur, ctx("I", prev_roman="I"))


def test_direct_fifth_allowed_when_soprano_steps():
    prev = vc("F5", "E4", "C4", "C3")
    cur = vc("G5", "E4", "C4", "C4")          # outer → P5, soprano steps F5→G5
    assert "direct" not in slugs(prev, cur, ctx("I", prev_roman="I"))


# --- §5 leading-tone resolution (at V→I) -----------------------------------

def test_unresolved_leading_tone_in_soprano():
    prev = vc("B4", "G4", "D4", "G3")         # V (G-B-D), LT=B in soprano
    cur = vc("G4", "E4", "C4", "C3")          # I, soprano B4→G4 (LT falls)
    assert "leading_tone" in slugs(prev, cur, ctx("I", prev_roman="V"))


def test_resolved_leading_tone_ok():
    prev = vc("B4", "G4", "D4", "G3")         # V
    cur = vc("C5", "G4", "E4", "C3")          # I, soprano B4→C5 (resolves up)
    assert "leading_tone" not in slugs(prev, cur, ctx("I", prev_roman="V"))


# --- §6 chordal-seventh resolution (at V7→I) -------------------------------

def test_unresolved_seventh():
    prev = vc("D5", "B4", "F4", "G3")         # V7 (G-B-D-F), 7th=F in tenor
    cur = vc("C5", "E4", "C4", "C3")          # I, tenor F4→C4 (not down by step)
    assert "seventh" in slugs(prev, cur, ctx("I", prev_roman="V7"))


def test_resolved_seventh_ok():
    prev = vc("D5", "B4", "F4", "G3")         # V7
    cur = vc("C5", "G4", "E4", "C3")          # I, tenor F4→E4 (down by step)
    assert "seventh" not in slugs(prev, cur, ctx("I", prev_roman="V7"))


# --- §7 doubling hard carve-outs -------------------------------------------

def test_doubled_leading_tone():
    v = vc("B4", "D4", "B3", "G3")            # V = G-B-D with B (LT) doubled
    assert "doubled_leading_tone" in slugs(None, v, ctx("V"))


def test_doubled_seventh():
    v = vc("F5", "F4", "D4", "G3")            # V7 with F (7th) doubled
    assert "doubled_seventh" in slugs(None, v, ctx("V7"))
