"""Part-writing rule checker and voice-leading cost function.

Implements PARTWRITING-RULES §0-§9. Hard invariants (§0-§7 carve-outs) are
pass/fail via ``rule_violations``; soft preferences (§7 doubling conventions,
§8 cost weights) shape ``transition_cost``, the search objective ``realize``
uses to pick among rule-legal voicings.

This module is the fixed contract ``tests/test_partwriting.py`` was written
against -- see PARTWRITING-RULES "Fixed contract" and "How this maps to code".
Do not change ``rule_violations``'s signature or the canonical ``.rule`` slugs
without updating that (locked) test file and the spec together.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import chords as _chords
from .voicing import Voicing

# Canonical rule slugs (this set is the contract; keep in sync with
# PARTWRITING-RULES.md and tests/test_partwriting.py).
RULE_SLUGS = frozenset(
    {
        "range",
        "spacing",
        "crossing",
        "overlap",
        "parallel_fifths",
        "parallel_octaves",
        "direct",
        "leading_tone",
        "seventh",
        "doubled_leading_tone",
        "doubled_seventh",
    }
)

S_RANGE = (60, 79)
A_RANGE = (55, 74)
T_RANGE = (48, 67)
B_RANGE = (40, 60)
MAX_UPPER_SPACING = 12

_VOICE_PAIRS_ALL = [("s", "a"), ("s", "t"), ("s", "b"), ("a", "t"), ("a", "b"), ("t", "b")]
_ADJACENT_PAIRS = [("s", "a"), ("a", "t"), ("t", "b")]


@dataclass(frozen=True)
class RuleViolation:
    rule: str
    detail: str = ""


# --------------------------------------------------------------------------
# Static rules (checked on `cur` regardless of whether `prev` is available)
# --------------------------------------------------------------------------


def _check_range(cur: Voicing) -> list[RuleViolation]:
    out = []
    for name, val, bounds in (
        ("s", cur.s, S_RANGE),
        ("a", cur.a, A_RANGE),
        ("t", cur.t, T_RANGE),
        ("b", cur.b, B_RANGE),
    ):
        lo, hi = bounds
        if not (lo <= val <= hi):
            out.append(RuleViolation("range", f"{name}={val} outside [{lo},{hi}]"))
    return out


def _check_spacing(cur: Voicing) -> list[RuleViolation]:
    out = []
    if cur.s - cur.a > MAX_UPPER_SPACING:
        out.append(RuleViolation("spacing", "S-A exceeds an octave"))
    if cur.a - cur.t > MAX_UPPER_SPACING:
        out.append(RuleViolation("spacing", "A-T exceeds an octave"))
    return out


def _check_crossing(cur: Voicing) -> list[RuleViolation]:
    if not (cur.s >= cur.a >= cur.t >= cur.b):
        return [RuleViolation("crossing", "S/A/T/B order violated")]
    return []


def _check_doubled_leading_tone(cur: Voicing, ctx: dict) -> list[RuleViolation]:
    lt_pc = _chords.leading_tone_pitch_class(ctx["key"])
    pcs = [cur.s % 12, cur.a % 12, cur.t % 12, cur.b % 12]
    if pcs.count(lt_pc) > 1:
        return [RuleViolation("doubled_leading_tone", "leading tone doubled")]
    return []


def _check_doubled_seventh(cur: Voicing, ctx: dict) -> list[RuleViolation]:
    cur_roman = ctx.get("cur_roman")
    if not cur_roman:
        return []
    seventh_pc = _chords.chord_members(cur_roman, ctx["key"]).get("seventh")
    if seventh_pc is None:
        return []
    pcs = [cur.s % 12, cur.a % 12, cur.t % 12, cur.b % 12]
    if pcs.count(seventh_pc) > 1:
        return [RuleViolation("doubled_seventh", "chordal seventh doubled")]
    return []


# --------------------------------------------------------------------------
# Transition rules (need `prev`)
# --------------------------------------------------------------------------


def _check_overlap(prev: Voicing, cur: Voicing) -> list[RuleViolation]:
    out = []
    for upper, lower in _ADJACENT_PAIRS:
        prev_upper, prev_lower = getattr(prev, upper), getattr(prev, lower)
        cur_upper, cur_lower = getattr(cur, upper), getattr(cur, lower)
        if cur_lower > prev_upper or cur_upper < prev_lower:
            out.append(RuleViolation("overlap", f"{upper}/{lower} voice overlap"))
    return out


def _interval_class(a: int, b: int) -> int:
    return abs(a - b) % 12


def _perfect_kind(ic: int) -> Optional[str]:
    if ic == 7:
        return "fifth"
    if ic == 0:
        return "octave"
    return None


def _check_parallels(prev: Voicing, cur: Voicing) -> list[RuleViolation]:
    out = []
    for v1, v2 in _VOICE_PAIRS_ALL:
        p1, p2 = getattr(prev, v1), getattr(prev, v2)
        c1, c2 = getattr(cur, v1), getattr(cur, v2)
        prev_kind = _perfect_kind(_interval_class(p1, p2))
        cur_kind = _perfect_kind(_interval_class(c1, c2))
        if prev_kind is None or cur_kind is None or prev_kind != cur_kind:
            continue
        d1, d2 = c1 - p1, c2 - p2
        if d1 == 0 or d2 == 0:
            continue  # no motion in at least one voice -> not a parallel
        if (d1 > 0) != (d2 > 0):
            continue  # not similar motion
        rule = "parallel_fifths" if prev_kind == "fifth" else "parallel_octaves"
        out.append(RuleViolation(rule, f"{v1}/{v2}"))
    return out


def _check_direct(prev: Voicing, cur: Voicing) -> list[RuleViolation]:
    kind = _perfect_kind(_interval_class(cur.s, cur.b))
    if kind is None:
        return []
    d_s, d_b = cur.s - prev.s, cur.b - prev.b
    if d_s == 0 or d_b == 0 or (d_s > 0) != (d_b > 0):
        return []  # not similar motion in both outer voices
    if abs(d_s) > 2:  # soprano arrives by leap
        return [RuleViolation("direct", f"hidden {kind} in outer voices")]
    return []


def _check_leading_tone(prev: Voicing, cur: Voicing, ctx: dict) -> list[RuleViolation]:
    if not ctx.get("prev_roman"):
        return []
    lt_pc = _chords.leading_tone_pitch_class(ctx["key"])
    out = []
    for voice in ("s", "b"):
        p = getattr(prev, voice)
        if p % 12 != lt_pc:
            continue
        c = getattr(cur, voice)
        if c - p != 1:
            out.append(RuleViolation("leading_tone", f"{voice} leading tone not resolved up by semitone"))
    return out


def _check_seventh(prev: Voicing, cur: Voicing, ctx: dict) -> list[RuleViolation]:
    prev_roman = ctx.get("prev_roman")
    if not prev_roman:
        return []
    seventh_pc = _chords.chord_members(prev_roman, ctx["key"]).get("seventh")
    if seventh_pc is None:
        return []
    out = []
    for voice in ("s", "a", "t", "b"):
        p = getattr(prev, voice)
        if p % 12 != seventh_pc:
            continue
        c = getattr(cur, voice)
        delta = c - p
        if not (-2 <= delta <= -1):  # must fall by a step (1 or 2 semitones)
            out.append(RuleViolation("seventh", f"{voice} chordal seventh not resolved down by step"))
    return out


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def rule_violations(prev: Optional[Voicing], cur: Voicing, ctx: dict) -> list[RuleViolation]:
    """All hard-invariant violations of the transition ``prev -> cur``.

    ``prev`` may be ``None`` for the first chord in a progression, in which
    case only the static rules (range/spacing/crossing/doubled LT & 7th) run.
    ``ctx`` is ``{"key": str, "prev_roman": str | None, "cur_roman": str}``.
    """
    out: list[RuleViolation] = []
    out += _check_range(cur)
    out += _check_spacing(cur)
    out += _check_crossing(cur)
    out += _check_doubled_leading_tone(cur, ctx)
    out += _check_doubled_seventh(cur, ctx)
    if prev is not None:
        out += _check_overlap(prev, cur)
        out += _check_parallels(prev, cur)
        out += _check_direct(prev, cur)
        out += _check_leading_tone(prev, cur, ctx)
        out += _check_seventh(prev, cur, ctx)
    return out


# --------------------------------------------------------------------------
# Soft preferences: doubling conventions (§7 soft half) + cost (§8)
# --------------------------------------------------------------------------

# Tenor–bass open spacing (soft only; hard §1 still allows T–B > octave).
# Band B: free ≤12, light 13–15, firm ≥16.
_TB_SPACING_FREE = 12  # semitones
_TB_SPACING_LIGHT_MAX = 15
_TB_SPACING_LIGHT_PER_SEMI = 1.0  # gap 13→1, 14→2, 15→3
_TB_SPACING_FIRM_PER_SEMI = 2.5  # added per semi past 15 (16→5.5, …)


def _expected_doubled_pc(cur_roman: str, key_like) -> Optional[int]:
    """The conventionally-preferred doubled pitch class for this chord/inversion
    (PARTWRITING-RULES §7 soft half). Returns None when there's no strong
    convention to check against.
    """
    members = _chords.chord_members(cur_roman, key_like)
    rn = _chords.roman_numeral(cur_roman, key_like)
    inversion = rn.inversion()
    is_cad64 = cur_roman.strip().lower().startswith("cad64")
    is_diminished = rn.quality == "diminished"

    if is_cad64:
        return members["fifth"]  # cadential 6-4: double the bass (scale-degree 5)
    if is_diminished:
        return members["third"]  # diminished triads: double the third
    if inversion == 0:
        return members["root"]
    # First/other inversions: no single strong convention encoded here beyond
    # "prefer root or soprano over the bass/third" -- handled as a smaller
    # penalty in transition_cost rather than a single expected pc.
    return None


def _doubling_deviation_cost(cur: Voicing, ctx: dict) -> float:
    cur_roman = ctx.get("cur_roman")
    if not cur_roman:
        return 0.0
    try:
        expected_pc = _expected_doubled_pc(cur_roman, ctx["key"])
    except Exception:
        return 0.0
    if expected_pc is None:
        return 0.0
    pcs = [cur.s % 12, cur.a % 12, cur.t % 12, cur.b % 12]
    # Find the actually-doubled pitch class, if any (a pc appearing 2+ times).
    doubled = [pc for pc in set(pcs) if pcs.count(pc) > 1]
    if not doubled:
        return 0.0
    if expected_pc in doubled:
        return 0.0
    return 4.0  # §8: doubling deviation penalty


def _frustrated_leading_tone_cost(prev: Optional[Voicing], cur: Voicing, ctx: dict) -> float:
    """Inner-voice LT falling to 5 instead of rising to 1: allowed, soft penalty."""
    if prev is None or not ctx.get("prev_roman"):
        return 0.0
    lt_pc = _chords.leading_tone_pitch_class(ctx["key"])
    tonic_pc = _chords.tonic_pitch_class(ctx["key"])
    cost = 0.0
    for voice in ("a", "t"):
        p = getattr(prev, voice)
        if p % 12 != lt_pc:
            continue
        c = getattr(cur, voice)
        if c - p != 1 and c % 12 != tonic_pc:
            cost += 2.0  # §8: frustrated leading tone (inner voice)
    return cost


def _tb_open_spacing_cost(cur: Voicing) -> float:
    """Soft penalty when tenor sits more than an octave above bass.

    Hard rules still allow T–B > octave (PARTWRITING-RULES §1). This only
    ranks denser voicings ahead of habitually hollow ones:

    * gap ≤ 12: free
    * 13–15: light ramp (1 per semitone over 12)
    * ≥ 16: firm ramp (light cost at 15, then +2.5 per extra semitone)
    """
    gap = cur.t - cur.b
    if gap <= _TB_SPACING_FREE:
        return 0.0
    if gap <= _TB_SPACING_LIGHT_MAX:
        return _TB_SPACING_LIGHT_PER_SEMI * (gap - _TB_SPACING_FREE)
    light_cap = _TB_SPACING_LIGHT_PER_SEMI * (
        _TB_SPACING_LIGHT_MAX - _TB_SPACING_FREE
    )
    return light_cap + _TB_SPACING_FIRM_PER_SEMI * (gap - _TB_SPACING_LIGHT_MAX)


def transition_cost(prev: Optional[Voicing], cur: Voicing, ctx: dict) -> float:
    """Voice-leading cost of moving from ``prev`` to ``cur`` (PARTWRITING-RULES §8).

    Lower is better. This is the search objective ``realize`` minimizes; it is
    a *soft* preference layer on top of the hard invariants in
    ``rule_violations`` (those are enforced separately by excluding
    rule-violating candidates from the search, not by cost).
    """
    cost = 0.0
    if prev is not None:
        voices = ("s", "a", "t", "b")
        deltas = [getattr(cur, v) - getattr(prev, v) for v in voices]
        cost += sum(abs(d) for d in deltas)  # total motion, weight 1.0/semitone
        for d in deltas:
            if abs(d) > 5:  # more than a perfect 4th
                cost += 3.0  # large leap
        if abs(cur.b - prev.b) > 7:  # bass leap beyond a perfect 5th
            cost += 1.0
        directions = {(1 if d > 0 else -1) for d in deltas if d != 0}
        if len(directions) == 1 and all(d != 0 for d in deltas):
            cost += 2.0  # all four voices move in the same direction
        cost += _frustrated_leading_tone_cost(prev, cur, ctx)
    cost += _doubling_deviation_cost(cur, ctx)
    cost += _tb_open_spacing_cost(cur)
    return cost
