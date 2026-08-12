"""Soft cost ranking tests (PARTWRITING-RULES §8) — not hard-invariant fixtures."""

from __future__ import annotations

from app.generation.rules import (
    _tb_open_spacing_cost,
    rule_violations,
    transition_cost,
)
from app.generation.voicing import Voicing


def test_tb_spacing_free_at_or_below_octave():
    close = Voicing(s=72, a=67, t=60, b=48)  # T–B = 12
    under = Voicing(s=72, a=67, t=55, b=48)  # T–B = 7
    assert _tb_open_spacing_cost(close) == 0.0
    assert _tb_open_spacing_cost(under) == 0.0


def test_tb_spacing_light_band_13_to_15():
    # gap 13, 14, 15 → 1, 2, 3
    assert _tb_open_spacing_cost(Voicing(s=72, a=67, t=61, b=48)) == 1.0
    assert _tb_open_spacing_cost(Voicing(s=72, a=67, t=62, b=48)) == 2.0
    assert _tb_open_spacing_cost(Voicing(s=72, a=67, t=63, b=48)) == 3.0


def test_tb_spacing_firm_band_from_16():
    # gap 16 → 3 + 2.5 = 5.5; gap 19 → 3 + 10 = 13
    assert _tb_open_spacing_cost(Voicing(s=76, a=71, t=64, b=48)) == 5.5
    assert _tb_open_spacing_cost(Voicing(s=76, a=71, t=67, b=48)) == 13.0


def test_tb_open_still_legal_under_hard_rules():
    """Wide T–B must not become a hard spacing violation."""
    wide = Voicing(s=72, a=67, t=60, b=40)  # T–B = 20
    ctx = {"key": "C major", "prev_roman": None, "cur_roman": "I"}
    slugs = {v.rule for v in rule_violations(None, wide, ctx)}
    assert "spacing" not in slugs


def test_transition_cost_prefers_closer_tb_when_motion_equal():
    """Same outer motion class: closer T–B ranks cheaper than hollow."""
    ctx = {"key": "C major", "prev_roman": "I", "cur_roman": "I"}
    prev = Voicing(s=72, a=67, t=60, b=48)
    close = Voicing(s=72, a=67, t=60, b=48)  # T–B = 12
    wide = Voicing(s=72, a=67, t=64, b=48)  # T–B = 16; S/A held
    # Hold S/A; only T moves on the wide option — isolate spacing effect.
    assert transition_cost(prev, close, ctx) < transition_cost(prev, wide, ctx)
