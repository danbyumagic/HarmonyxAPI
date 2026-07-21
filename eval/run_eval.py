"""Eval harness: key-detection agreement on a small Bach chorale set.

The brief's key idea: "that single number turns it from a demo into evidence."
This runs the deterministic analyzer over a curated set of chorales from the
music21 corpus and reports the percentage whose detected key matches the
ground truth in ``expected/keys.json``.

Run from the repo root:

    python -m eval.run_eval

It prints a per-chorale table and an overall agreement percentage, and exits
non-zero if agreement drops below ``--min`` (default 0.0, i.e. never fails) so
it can double as a regression gate in CI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from music21 import corpus

# Allow `python eval/run_eval.py` as well as `python -m eval.run_eval`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.analyzer import analyze_score  # noqa: E402

EXPECTED_PATH = os.path.join(os.path.dirname(__file__), "expected", "keys.json")


def _normalize(key_name: str) -> str:
    """Normalize a key string for comparison (case, spacing)."""
    return " ".join(key_name.strip().split()).lower()


def run(min_agreement: float) -> int:
    with open(EXPECTED_PATH) as f:
        expected = json.load(f)["chorales"]

    print(f"Evaluating key detection on {len(expected)} chorales\n")
    print(f"{'chorale':<16} {'expected':<10} {'detected':<10} match")
    print("-" * 48)

    matches = 0
    for name, want in sorted(expected.items()):
        score = corpus.parse(name)
        result = analyze_score(score)
        got = result.key
        ok = _normalize(got) == _normalize(want)
        matches += ok
        short = name.split("/")[-1]
        print(f"{short:<16} {want:<10} {got:<10} {'✓' if ok else '✗'}")

    agreement = matches / len(expected) if expected else 0.0
    print("-" * 48)
    print(f"\nAgreement: {matches}/{len(expected)} = {agreement:.0%}")

    if agreement < min_agreement:
        print(f"FAIL: below threshold {min_agreement:.0%}")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min",
        type=float,
        default=0.0,
        help="Fail (exit 1) if agreement drops below this fraction (0.0-1.0).",
    )
    args = parser.parse_args()
    sys.exit(run(args.min))


if __name__ == "__main__":
    main()
