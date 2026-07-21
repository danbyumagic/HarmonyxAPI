"""Optional LLM layer: a plain-English walkthrough of a progression.

This is the *explainer* option from the project brief -- the lower-risk of the
two AI angles.  The deterministic music21 analysis stays authoritative; the
model only narrates it.  It never changes a Roman numeral or a key.

The explainer is gated on ``ANTHROPIC_API_KEY``: if no key is configured (or
the ``anthropic`` SDK isn't installed), ``explain_progression`` returns
``None`` and the API simply omits the ``explanation`` field.  That keeps the
core ``/analyze`` endpoint fully functional and deterministic without any LLM
dependency.
"""

from __future__ import annotations

import os
from typing import List, Optional

from .analyzer import AnalysisResult

# Opus 4.8 is the current, most capable Claude model. Adaptive thinking lets
# the model decide how much reasoning a given progression warrants.
MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = (
    "You are a music theory tutor. You are given a deterministic, "
    "rule-based harmonic analysis of a short passage (key, and a list of "
    "chords with Roman numerals). Write a concise, plain-English walkthrough "
    "of the progression for a student: name the key, describe the harmonic "
    "motion, and point out any cadences. Do not contradict or 'correct' the "
    "given Roman numerals -- explain them. Keep it to a short paragraph."
)


def explain_progression(analysis: AnalysisResult) -> Optional[str]:
    """Return a plain-English walkthrough, or ``None`` if the LLM is unavailable.

    Availability requires both the ``anthropic`` package and an
    ``ANTHROPIC_API_KEY`` in the environment.  Any error talking to the API is
    swallowed and reported as ``None`` -- the deterministic analysis must never
    be blocked by the optional narration layer.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None

    try:
        import anthropic
    except ImportError:
        return None

    prompt = _build_prompt(analysis)

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception:
        return None

    text_parts = [block.text for block in response.content if block.type == "text"]
    explanation = "".join(text_parts).strip()
    return explanation or None


def _build_prompt(analysis: AnalysisResult) -> str:
    lines: List[str] = [
        f"Key: {analysis.key} (detection confidence {analysis.confidence:.2f})",
        "",
        "Chords (measure.beat  Roman  quality):",
    ]
    for c in analysis.chords:
        lines.append(
            f"  m{c.measure} b{c.beat}: {c.roman}  ({c.quality}, inversion {c.inversion})"
        )

    if analysis.cadences:
        lines.append("")
        lines.append("Cadences:")
        for cad in analysis.cadences:
            lines.append(f"  m{cad.measure}: {cad.type}")

    lines.append("")
    lines.append("Write the walkthrough now.")
    return "\n".join(lines)
