"""Eval harness: generation quality — rule violations + RN round-trip.

For each curated fixture in ``expected/generation_fixtures.json``:

1. Realize the RN progression as SATB (``app.generation.realize``).
2. Count hard-invariant violations on the realized path (target: 0).
3. Write MusicXML, re-analyze with ``analyze_score``, compare recovered
   Roman numerals to the input via ``rn_agreement`` (§10 primary/strict).

Run from the repo root::

    python -m eval.run_generation_eval
    python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0

Exits non-zero if primary round-trip agreement is below ``--min-roundtrip``
or total hard violations exceed ``--max-violations`` (CI regression gate).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from typing import List, Optional

from music21 import converter

# Allow `python eval/run_generation_eval.py` as well as `python -m ...`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.analyzer import analyze_score  # noqa: E402
from app.generation.chords import rn_agreement  # noqa: E402
from app.generation.realize import path_violations, realize, satb_voicings_from_score  # noqa: E402

FIXTURES_PATH = os.path.join(
    os.path.dirname(__file__), "expected", "generation_fixtures.json"
)


def _write_and_reparse(score):
    """Round-trip through MusicXML so the eval exercises the real I/O path."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "realized.musicxml")
        score.write("musicxml", fp=path)
        return converter.parse(path)


def _score_roundtrip(
    input_rns: List[str], recovered_rns: List[str], key: str
) -> tuple[int, int, int, int]:
    """Return (primary_matches, strict_matches, compared, input_len).

    If lengths differ, only the shared prefix is compared chord-by-chord;
    unmatched input chords count as misses for both metrics (so agreement
    is matches / len(input)).
    """
    n_in = len(input_rns)
    n_out = len(recovered_rns)
    n_cmp = min(n_in, n_out)
    primary = 0
    strict = 0
    for i in range(n_cmp):
        if rn_agreement(input_rns[i], recovered_rns[i], key, strict=False):
            primary += 1
        if rn_agreement(input_rns[i], recovered_rns[i], key, strict=True):
            strict += 1
    # Length mismatch: remaining input slots are misses (already not counted).
    return primary, strict, n_cmp, n_in


def run(*, min_roundtrip: float, max_violations: int) -> int:
    with open(FIXTURES_PATH) as f:
        data = json.load(f)
    fixtures = data["fixtures"]

    print(f"Generation eval — {len(fixtures)} fixtures\n")
    header = (
        f"{'fixture':<22} {'chords':>6} {'rt_pri':>8} {'rt_str':>8} "
        f"{'viols':>6} status"
    )
    print(header)
    print("-" * len(header))

    total_primary = 0
    total_strict = 0
    total_chords = 0
    total_violations = 0
    any_fail = False

    for fix in fixtures:
        name = fix["name"]
        key = fix["key"]
        progression: List[str] = fix["progression"]
        soprano: Optional[List[Optional[int]]] = fix.get("soprano")

        score = realize(progression, key, soprano=soprano)
        voicings = satb_voicings_from_score(score)
        viols = path_violations(voicings, progression, key)
        n_viol = len(viols)
        total_violations += n_viol

        reparsed = _write_and_reparse(score)
        analysis = analyze_score(reparsed)
        recovered = [c.roman for c in analysis.chords]

        primary, strict, _n_cmp, n_in = _score_roundtrip(
            progression, recovered, key
        )
        total_primary += primary
        total_strict += strict
        total_chords += n_in

        length_ok = len(recovered) == n_in
        fixture_ok = n_viol == 0 and primary == n_in and length_ok
        if not fixture_ok:
            any_fail = True
        mark = "OK" if fixture_ok else "FAIL"
        print(
            f"{name:<22} {n_in:>6} {primary:>2}/{n_in:<2}   {strict:>2}/{n_in:<2}   "
            f"{n_viol:>6} {mark}"
        )
        if not length_ok:
            print(f"  (length mismatch: recovered {recovered})")
        elif primary < n_in:
            print(f"  input:     {progression}")
            print(f"  recovered: {recovered}")
        if n_viol:
            print(f"  violations: {[v.rule for v in viols]}")

    print("-" * len(header))
    agreement = total_primary / total_chords if total_chords else 0.0
    strict_agr = total_strict / total_chords if total_chords else 0.0
    print(
        f"\nRound-trip (primary):  {total_primary}/{total_chords} = {agreement:.0%}"
    )
    print(
        f"Round-trip (strict):   {total_strict}/{total_chords} = {strict_agr:.0%}"
    )
    print(f"Hard violations:       {total_violations}")

    failed = False
    if agreement < min_roundtrip:
        print(
            f"FAIL: primary round-trip {agreement:.0%} "
            f"below threshold {min_roundtrip:.0%}"
        )
        failed = True
    if total_violations > max_violations:
        print(
            f"FAIL: {total_violations} hard violations "
            f"(max allowed {max_violations})"
        )
        failed = True
    if not failed:
        print("OK")
    # any_fail is informational for the per-fixture table; gates use totals.
    _ = any_fail
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-roundtrip",
        type=float,
        default=1.0,
        help=(
            "Fail if primary RN agreement (degree+quality) is below this "
            "fraction (0.0-1.0). Default 1.0 for the curated fixture set."
        ),
    )
    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Fail if total hard-invariant violations exceed this (default 0).",
    )
    args = parser.parse_args()
    sys.exit(
        run(min_roundtrip=args.min_roundtrip, max_violations=args.max_violations)
    )


if __name__ == "__main__":
    main()
