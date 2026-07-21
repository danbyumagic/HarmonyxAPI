"""Turn a Roman-numeral progression into a four-part SATB music21 Score.

The search: for each chord, enumerate rule-legal candidate voicings
(``voicing.candidate_voicings``), then run a Viterbi/DP pass across the whole
progression, pruning any transition that has a hard-invariant violation
(``rules.rule_violations``) and minimizing total ``rules.transition_cost``
among what's left. See ``docs/PARTWRITING-RULES.md`` and
``docs/IMPLEMENTATION-PLAN.md`` Milestone 1d/1e for the design.

This module has no FastAPI/HTTP dependency (PARTWRITING-RULES §11 / the
implementation plan's guiding constraints) so it's usable and testable
standalone.
"""

from __future__ import annotations

from typing import List, Optional

from music21 import key as m21key
from music21 import meter as m21meter
from music21 import note as m21note
from music21 import stream as m21stream

from . import chords as _chords
from .rules import RuleViolation, rule_violations, transition_cost
from .voicing import Voicing, candidate_voicings

_VOICE_NAMES = ("Soprano", "Alto", "Tenor", "Bass")
_VOICE_ATTRS = ("s", "a", "t", "b")


class RealizationError(Exception):
    """Raised when no legal voicing / voice-leading path exists."""


def check_soprano(
    progression: List[str], key_like: _chords.KeyLike, soprano: List[Optional[int]]
) -> List[dict]:
    """Validate a provided soprano line against its chords (§ soprano compatibility).

    Returns ``[]`` if every non-``None`` soprano entry is a chord tone of its
    Roman numeral; otherwise a list of per-index mismatch reports:
    ``{"index": i, "roman": figure, "soprano": pitch, "chord_tones": [...]}``.
    Entries where ``soprano[i] is None`` are skipped (that beat is left free
    for the realizer to choose).
    """
    if len(soprano) != len(progression):
        raise ValueError("soprano list length must match progression length")

    mismatches: List[dict] = []
    for i, (figure, pitch) in enumerate(zip(progression, soprano)):
        if pitch is None:
            continue
        if not _chords.is_chord_tone(pitch, figure, key_like):
            mismatches.append(
                {
                    "index": i,
                    "roman": figure,
                    "soprano": pitch,
                    "chord_tones": _chords.chord_pitch_classes(figure, key_like),
                }
            )
    return mismatches


def realize(
    progression: List[str],
    key_like: _chords.KeyLike,
    *,
    soprano: Optional[List[Optional[int]]] = None,
    time_signature: str = "4/4",
) -> m21stream.Score:
    """Realize a Roman-numeral progression as a 4-voice SATB ``music21.Score``.

    ``soprano``, if given, must be the same length as ``progression``; an
    entry may be ``None`` to leave that beat free. Callers should run
    ``check_soprano`` first and surface any mismatches (e.g. as a 422) rather
    than calling this directly with an unchecked soprano -- ``realize`` itself
    still raises ``RealizationError`` if an incompatible soprano leaves no
    candidate voicings, but ``check_soprano`` gives per-beat diagnostics.

    Raises ``RealizationError`` if the progression is empty, or if no
    hard-invariant-clean voice-leading path exists.
    """
    if not progression:
        raise RealizationError("progression must not be empty")
    if soprano is not None and len(soprano) != len(progression):
        raise ValueError("soprano list length must match progression length")

    contexts = [
        {
            "key": key_like,
            "prev_roman": progression[i - 1] if i > 0 else None,
            "cur_roman": figure,
        }
        for i, figure in enumerate(progression)
    ]

    candidate_lists: List[List[Voicing]] = []
    for i, figure in enumerate(progression):
        sop = soprano[i] if soprano is not None else None
        cands = candidate_voicings(figure, key_like, soprano=sop)
        if not cands:
            detail = f" with soprano={sop}" if sop is not None else ""
            raise RealizationError(f"no legal voicings for chord {i} ('{figure}'){detail}")
        candidate_lists.append(cands)

    voicings = _best_path(progression, candidate_lists, contexts)
    return _build_score(voicings, key_like, time_signature)


def _best_path(
    progression: List[str],
    candidate_lists: List[List[Voicing]],
    contexts: List[dict],
) -> List[Voicing]:
    """Viterbi/DP over candidate voicings, minimizing summed transition_cost
    while excluding any transition with a hard-invariant violation."""
    n = len(progression)
    inf = float("inf")

    dp_cost: List[List[float]] = [[inf] * len(candidate_lists[i]) for i in range(n)]
    dp_back: List[List[int]] = [[-1] * len(candidate_lists[i]) for i in range(n)]

    for j, v in enumerate(candidate_lists[0]):
        if rule_violations(None, v, contexts[0]):
            continue
        dp_cost[0][j] = transition_cost(None, v, contexts[0])

    for i in range(1, n):
        if all(c == inf for c in dp_cost[i - 1]):
            raise RealizationError(
                f"no rule-legal voicing reaches chord {i - 1} ('{progression[i - 1]}') "
                f"from chord {i - 2 if i >= 2 else 'start'}"
            )
        for j, v in enumerate(candidate_lists[i]):
            best_cost, best_k = inf, -1
            for k, pv in enumerate(candidate_lists[i - 1]):
                if dp_cost[i - 1][k] == inf:
                    continue
                if rule_violations(pv, v, contexts[i]):
                    continue
                cost = dp_cost[i - 1][k] + transition_cost(pv, v, contexts[i])
                if cost < best_cost:
                    best_cost, best_k = cost, k
            dp_cost[i][j] = best_cost
            dp_back[i][j] = best_k

    last = dp_cost[-1]
    if all(c == inf for c in last):
        raise RealizationError(
            f"no rule-legal voice-leading path found for this progression "
            f"(dead end at chord {n - 1}, '{progression[-1]}')"
        )

    best_j = min(range(len(last)), key=lambda j: last[j])
    path_idx = [0] * n
    path_idx[-1] = best_j
    for i in range(n - 1, 0, -1):
        path_idx[i - 1] = dp_back[i][path_idx[i]]

    return [candidate_lists[i][path_idx[i]] for i in range(n)]


def path_violations(voicings: List[Voicing], progression: List[str], key_like: _chords.KeyLike) -> List[RuleViolation]:
    """Every hard-invariant violation across an already-realized path.

    Used by the M2 eval and by tests to assert a realized progression is
    clean, independent of how it was constructed.
    """
    contexts = [
        {
            "key": key_like,
            "prev_roman": progression[i - 1] if i > 0 else None,
            "cur_roman": figure,
        }
        for i, figure in enumerate(progression)
    ]
    out: List[RuleViolation] = []
    for i, v in enumerate(voicings):
        prev = voicings[i - 1] if i > 0 else None
        out += rule_violations(prev, v, contexts[i])
    return out


def _build_score(voicings: List[Voicing], key_like: _chords.KeyLike, time_signature: str) -> m21stream.Score:
    k = _chords.to_key(key_like)
    score = m21stream.Score()
    for name, attr in zip(_VOICE_NAMES, _VOICE_ATTRS):
        part = m21stream.Part(id=name)
        part.partName = name
        part.append(m21meter.TimeSignature(time_signature))
        part.append(m21key.Key(k.tonic.name, k.mode))
        for v in voicings:
            n = m21note.Note()
            n.pitch.midi = getattr(v, attr)
            n.quarterLength = 1.0
            part.append(n)
        score.insert(0, part)
    return score.makeMeasures(inPlace=False)
