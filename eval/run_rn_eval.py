"""Eval harness: chord-by-chord Roman-numeral agreement (A7).

Replaces key-only agreement (``eval/run_eval.py``) as the headline analyzer
metric: matching the overall key while getting most of the interior
harmonies wrong is not useful, and gives no signal on where the analyzer is
actually going wrong.

Ground truth is music21's bundled hand analyses of Bach chorales
(``music21/corpus/bach/choraleAnalyses/*.rntxt``, Riemenschneider-numbered,
by Andrew Jones et al.) -- see ``eval/expected/rn_corpus.json`` for the
curated subset whose BWV number also resolves to a corpus MusicXML score.
This ships with music21 itself (already a dependency), unlike the
Humdrum/KernScores corpus flagged in docs/research/15-tier3-remainder.md as
needing licensing clearance.

For each ground-truth Roman numeral event (measure, beat, figure), this
finds the analyzer's harmony sounding at that moment and compares figures
using the same agreement definition as the M2 generation round-trip eval
(PARTWRITING-RULES §10, via ``app.generation.chords.rn_agreement``):

  * primary (default): scale degree + quality match
  * strict:             + inversion + seventh-presence match

Both are figure-level comparisons against the analyzer's own detected key,
not absolute-pitch comparisons -- if the analyzer picks the wrong key
entirely (see ``run_eval.py``), figures may agree or disagree by coincidence
rather than genuine harmonic agreement. This is the same tradeoff the M2
generation eval already accepts.

Run from the repo root:

    python -m eval.run_rn_eval
    python -m eval.run_rn_eval --min 0.5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional, Tuple

import music21
from music21 import converter, corpus, roman as m21roman

# Allow `python eval/run_rn_eval.py` as well as `python -m eval.run_rn_eval`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.analyzer import ChordAnalysis, analyze_score  # noqa: E402
from app.generation.chords import rn_agreement  # noqa: E402

CORPUS_PATH = os.path.join(os.path.dirname(__file__), "expected", "rn_corpus.json")
ANALYSES_DIR = os.path.join(
    os.path.dirname(music21.__file__), "corpus", "bach", "choraleAnalyses"
)


def _load_expected(rntxt_path: str) -> List[Tuple[int, float, str]]:
    """Parse a RomanText analysis into (measure, beat, figure) events."""
    score = converter.parse(rntxt_path, format="romantext")
    events = [
        (rn.measureNumber, round(float(rn.beat), 3), rn.figure)
        for rn in score.recurse().getElementsByClass(m21roman.RomanNumeral)
    ]
    events.sort(key=lambda e: (e[0], e[1]))
    return events


def _chord_at(
    chords: List[ChordAnalysis], measure: int, beat: float
) -> Optional[ChordAnalysis]:
    """The analyzed harmony sounding at (measure, beat): the last chord at
    or before that point. ``chords`` must be in chronological order."""
    candidate = None
    for c in chords:
        if (c.measure, c.beat) <= (measure, beat):
            candidate = c
        else:
            break
    return candidate


def _eval_chorale(riemenschneider: str, bwv: str) -> Tuple[int, int, int]:
    """Returns (total events, primary hits, strict hits) for one chorale."""
    expected_events = _load_expected(os.path.join(ANALYSES_DIR, riemenschneider))
    result = analyze_score(corpus.parse(bwv))

    primary_hits = strict_hits = 0
    for measure, beat, expected_figure in expected_events:
        chord = _chord_at(result.chords, measure, beat)
        if chord is None:
            continue
        if rn_agreement(expected_figure, chord.roman, result.key):
            primary_hits += 1
        if rn_agreement(expected_figure, chord.roman, result.key, strict=True):
            strict_hits += 1

    return len(expected_events), primary_hits, strict_hits


def run(min_agreement: float) -> int:
    with open(CORPUS_PATH) as f:
        chorales = json.load(f)["chorales"]

    print(f"Evaluating chord-by-chord RN agreement on {len(chorales)} chorales\n")
    print(f"{'chorale':<14} {'events':>6} {'primary':>16} {'strict':>16}")
    print("-" * 56)

    total_events = total_primary = total_strict = 0
    for entry in chorales:
        events, primary, strict = _eval_chorale(entry["riemenschneider"], entry["bwv"])
        total_events += events
        total_primary += primary
        total_strict += strict
        short = entry["bwv"].split("/")[-1]
        primary_cell = f"{primary}/{events} = {primary / events:.0%}"
        strict_cell = f"{strict}/{events} = {strict / events:.0%}"
        print(f"{short:<14} {events:>6} {primary_cell:>16} {strict_cell:>16}")

    primary_agreement = total_primary / total_events if total_events else 0.0
    strict_agreement = total_strict / total_events if total_events else 0.0
    print("-" * 56)
    print(
        f"\nPrimary (degree+quality): {total_primary}/{total_events} = "
        f"{primary_agreement:.0%}"
    )
    print(
        f"Strict (+inversion+7th):  {total_strict}/{total_events} = "
        f"{strict_agreement:.0%}"
    )

    if primary_agreement < min_agreement:
        print(f"FAIL: primary agreement below threshold {min_agreement:.0%}")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min",
        type=float,
        default=0.0,
        help="Fail (exit 1) if primary agreement drops below this fraction (0.0-1.0).",
    )
    args = parser.parse_args()
    sys.exit(run(args.min))


if __name__ == "__main__":
    main()
