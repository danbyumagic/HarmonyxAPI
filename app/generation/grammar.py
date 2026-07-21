"""Layer 1: functional-harmony progression grammar.

Weighted Markov walk over the transition table in
``docs/PARTWRITING-RULES.md`` §9. Cadence-aware and lock-aware. No FastAPI
dependency — ``POST /progression`` (M3 Chunk B) will call this later.
"""

from __future__ import annotations

import random
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from . import chords as _chords

# --- Function groups (documentation / future filters) -------------------

FUNCTION_MAJOR = {
    "T": frozenset({"I", "vi", "iii", "I6"}),
    "PD": frozenset({"ii", "ii6", "IV", "IV6"}),
    "D": frozenset({"V", "V7", "viio6", "V6", "Cad64"}),
}

FUNCTION_MINOR = {
    "T": frozenset({"i", "VI", "III", "i6"}),
    "PD": frozenset({"iio6", "iv", "iv6"}),
    "D": frozenset({"V", "V7", "viio6", "V6", "Cad64"}),
}

# Relative weights from PARTWRITING-RULES §9 (major); minor is analogous.
# Q3a: higher inversion traffic + approach edges into Cad64 (still no applied chords).
_TRANSITIONS_MAJOR: Dict[str, List[Tuple[str, float]]] = {
    "I": [
        ("V", 4),
        ("V7", 3),
        ("IV", 3),
        ("ii", 3),
        ("vi", 2),
        ("I6", 4),  # Q3a: was 2
        ("iii", 1),
        ("V6", 2),  # Q3a: path into V6
        ("IV6", 1),  # Q3a: path into IV6
    ],
    "I6": [
        ("ii", 3),
        ("IV", 3),
        ("V", 2),
        ("ii6", 3),  # Q3a: was 2
        ("V7", 2),
        ("IV6", 2),
        ("Cad64", 2),
    ],
    "ii": [
        ("V", 5),
        ("V7", 4),
        ("viio6", 1),
        ("Cad64", 2),
        ("V6", 1),
    ],
    "ii6": [
        ("V", 5),
        ("V7", 4),
        ("Cad64", 3),  # common cadential approach
    ],
    "IV": [
        ("V", 5),
        ("V7", 4),
        ("I", 2),
        ("ii", 1),
        ("IV6", 2),
        ("Cad64", 2),
        ("I6", 1),
        ("V6", 1),
    ],
    "IV6": [
        ("V", 3),
        ("I", 2),
        ("V7", 2),
        ("Cad64", 2),
        ("ii6", 1),
    ],
    "V": [("I", 5), ("vi", 2), ("V7", 2)],
    "V7": [("I", 6), ("vi", 2)],
    "V6": [("I", 5)],
    "vi": [
        ("ii", 3),
        ("IV", 3),
        ("V", 2),
        ("ii6", 2),  # Q3a: was 1
        ("IV6", 1),
        ("I6", 1),
    ],
    "iii": [("vi", 3), ("IV", 2), ("I6", 1)],
    "viio6": [("I", 6)],
    "Cad64": [("V", 4), ("V7", 2)],  # Q3a: was V only at weight 1
}

_TRANSITIONS_MINOR: Dict[str, List[Tuple[str, float]]] = {
    "i": [
        ("V", 4),
        ("V7", 3),
        ("iv", 3),
        ("iio6", 2),
        ("VI", 2),
        ("i6", 4),  # Q3a: was 2
        ("III", 1),
        ("V6", 2),
        ("iv6", 1),
    ],
    "i6": [
        ("iio6", 3),
        ("iv", 3),
        ("V", 2),
        ("V7", 2),
        ("iv6", 2),
        ("Cad64", 2),
    ],
    "iio6": [
        ("V", 5),
        ("V7", 4),
        ("Cad64", 3),
        ("V6", 1),
    ],
    "iv": [
        ("V", 5),
        ("V7", 4),
        ("i", 2),
        ("iio6", 1),
        ("iv6", 2),
        ("Cad64", 2),
        ("i6", 1),
        ("V6", 1),
    ],
    "iv6": [
        ("V", 3),
        ("i", 2),
        ("V7", 2),
        ("Cad64", 2),
        ("iio6", 1),
    ],
    "V": [("i", 5), ("VI", 2), ("V7", 2)],
    "V7": [("i", 6), ("VI", 2)],
    "V6": [("i", 5)],
    "VI": [
        ("iio6", 3),
        ("iv", 3),
        ("V", 2),
        ("iv6", 1),
        ("i6", 1),
    ],
    "III": [("VI", 3), ("iv", 2), ("i6", 1)],
    "viio6": [("i", 6)],
    "Cad64": [("V", 4), ("V7", 2)],
}

# Explicit forbidden edges (weight 0) — also never appear in the tables above.
FORBIDDEN_TRANSITIONS = frozenset(
    {
        ("V", "IV"),
        ("V", "ii"),
        ("V", "iv"),
        ("V", "iio6"),
        ("V7", "IV"),
        ("V7", "iv"),
        ("V", "I6"),  # avoid at PAC; keep out of free walk into tonic inversion
        ("V", "i6"),
        ("V7", "I6"),
        ("V7", "i6"),
    }
)

_CADENCE_PAC = "PAC"
_CADENCE_HC = "HC"
_SUPPORTED_CADENCES = frozenset({_CADENCE_PAC, _CADENCE_HC})

_MAX_ATTEMPTS = 64


class GrammarError(ValueError):
    """Raised when a progression cannot be generated under the given constraints."""


def is_minor_key(key_like: _chords.KeyLike) -> bool:
    return _chords.to_key(key_like).mode == "minor"


def transitions_for(key_like: _chords.KeyLike) -> Dict[str, List[Tuple[str, float]]]:
    return _TRANSITIONS_MINOR if is_minor_key(key_like) else _TRANSITIONS_MAJOR


def tonic_figure(key_like: _chords.KeyLike) -> str:
    return "i" if is_minor_key(key_like) else "I"


def is_forbidden_transition(prev: str, cur: str) -> bool:
    if (prev, cur) in FORBIDDEN_TRANSITIONS:
        return True
    # viio6 may only go to tonic (table already encodes this; enforce hard).
    if prev == "viio6" and cur not in ("I", "i"):
        return True
    return False


def legal_successors(
    prev: str,
    key_like: _chords.KeyLike,
    *,
    must_precede: Optional[str] = None,
) -> List[Tuple[str, float]]:
    """Weighted successors of ``prev``, excluding forbidden edges.

    If ``must_precede`` is set, keep only chords that can legally move to that
    figure (one-step lookahead for locked / cadence slots).
    """
    table = transitions_for(key_like)
    raw = list(table.get(prev, []))
    out: List[Tuple[str, float]] = []
    for fig, weight in raw:
        if weight <= 0 or is_forbidden_transition(prev, fig):
            continue
        if must_precede is not None and not _can_move(fig, must_precede, key_like):
            continue
        out.append((fig, weight))
    return out


def _can_move(prev: str, cur: str, key_like: _chords.KeyLike) -> bool:
    if is_forbidden_transition(prev, cur):
        return False
    table = transitions_for(key_like)
    return any(fig == cur and w > 0 for fig, w in table.get(prev, []))


def _weighted_choice(rng: random.Random, options: Sequence[Tuple[str, float]]) -> str:
    figures, weights = zip(*options)
    return rng.choices(list(figures), weights=list(weights), k=1)[0]


def _normalize_locked(
    locked: Optional[Mapping[int, str]], length: int
) -> Dict[int, str]:
    if not locked:
        return {}
    out: Dict[int, str] = {}
    for raw_i, figure in locked.items():
        i = int(raw_i)
        if i < 0 or i >= length:
            raise GrammarError(f"locked index {i} out of range for length {length}")
        fig = str(figure).strip()
        if not fig:
            raise GrammarError(f"locked figure at index {i} is empty")
        out[i] = fig
    return out


def _apply_cadence_template(
    result: List[Optional[str]],
    key_like: _chords.KeyLike,
    cadence: str,
    locked: Dict[int, str],
    rng: random.Random,
) -> None:
    """Force the final 1–2 free slots toward a PAC or HC (unless locked)."""
    n = len(result)
    tonic = tonic_figure(key_like)

    if cadence == _CADENCE_PAC:
        if n < 2:
            raise GrammarError("PAC requires length >= 2")
        # Final chord: root-position tonic.
        if n - 1 not in locked:
            result[n - 1] = tonic
        elif result[n - 1] != tonic:
            raise GrammarError(
                f"PAC requires final chord {tonic!r}, but index {n - 1} is locked to "
                f"{result[n - 1]!r}"
            )
        # Penultimate: V or V7 (root position dominant).
        if n - 2 not in locked:
            pen_options = [("V", 5.0), ("V7", 4.0)]
            # Keep only those that can move to the final tonic.
            pen_options = [
                (f, w) for f, w in pen_options if _can_move(f, tonic, key_like)
            ]
            result[n - 2] = _weighted_choice(rng, pen_options)
        else:
            pen = result[n - 2]
            if pen not in ("V", "V7"):
                raise GrammarError(
                    f"PAC requires penultimate V or V7, but index {n - 2} is locked to "
                    f"{pen!r}"
                )
            if not _can_move(pen, tonic, key_like):
                raise GrammarError(
                    f"PAC lock conflict: {pen!r} cannot move to {tonic!r}"
                )
    elif cadence == _CADENCE_HC:
        if n - 1 not in locked:
            result[n - 1] = "V"
        elif result[n - 1] not in ("V", "V7"):
            raise GrammarError(
                f"HC requires final V or V7, but index {n - 1} is locked to "
                f"{result[n - 1]!r}"
            )
    else:
        raise GrammarError(
            f"unsupported cadence {cadence!r}; expected one of "
            f"{sorted(_SUPPORTED_CADENCES)}"
        )


def _fill_left_to_right(
    result: List[Optional[str]],
    key_like: _chords.KeyLike,
    rng: random.Random,
) -> bool:
    """Fill None slots. Returns False if stuck (caller may retry)."""
    n = len(result)
    tonic = tonic_figure(key_like)

    if result[0] is None:
        # Open on tonic (most common); rare alternate tonics later if needed.
        result[0] = tonic

    for i in range(1, n):
        if result[i] is not None:
            prev = result[i - 1]
            assert prev is not None
            if not _can_move(prev, result[i], key_like):
                return False
            continue

        prev = result[i - 1]
        assert prev is not None
        must_precede = result[i + 1] if i + 1 < n and result[i + 1] is not None else None
        options = legal_successors(prev, key_like, must_precede=must_precede)
        if not options:
            return False
        result[i] = _weighted_choice(rng, options)
    return True


def generate_progression(
    key_like: _chords.KeyLike,
    *,
    length: int = 8,
    locked: Optional[Mapping[int, str]] = None,
    cadence: str = _CADENCE_PAC,
    seed: Optional[int] = None,
) -> List[str]:
    """Generate an idiomatic Roman-numeral progression.

    Parameters
    ----------
    key_like:
        Key string or music21 Key (selects major vs minor figure set).
    length:
        Number of chords (>= 1; PAC needs >= 2).
    locked:
        Map of index → Roman figure that must appear at that slot.
    cadence:
        ``"PAC"`` → ends ``V|V7 → I/i``; ``"HC"`` → ends on ``V`` (or locked V7).
    seed:
        If set, the walk is deterministic for the same arguments.
    """
    if length < 1:
        raise GrammarError("length must be >= 1")
    cadence = cadence.upper()
    if cadence not in _SUPPORTED_CADENCES:
        raise GrammarError(
            f"unsupported cadence {cadence!r}; expected one of "
            f"{sorted(_SUPPORTED_CADENCES)}"
        )
    if cadence == _CADENCE_PAC and length < 2:
        raise GrammarError("PAC requires length >= 2")

    locked_map = _normalize_locked(locked, length)
    rng = random.Random(seed)

    last_error: Optional[Exception] = None
    for _ in range(_MAX_ATTEMPTS):
        result: List[Optional[str]] = [None] * length
        for i, fig in locked_map.items():
            result[i] = fig
        try:
            _apply_cadence_template(result, key_like, cadence, locked_map, rng)
        except GrammarError as exc:
            # Lock/cadence conflict is permanent — don't retry.
            raise exc
        if _fill_left_to_right(result, key_like, rng):
            out = [f for f in result if f is not None]
            if len(out) != length:
                last_error = GrammarError("internal: incomplete progression")
                continue
            if not _validate_path(out, key_like, cadence):
                last_error = GrammarError("internal: path failed validation")
                continue
            return out
        last_error = GrammarError("could not fill progression under constraints")

    raise GrammarError(
        f"failed to generate progression after {_MAX_ATTEMPTS} attempts"
        + (f" ({last_error})" if last_error else "")
    )


def _validate_path(progression: List[str], key_like: _chords.KeyLike, cadence: str) -> bool:
    for a, b in zip(progression, progression[1:]):
        if is_forbidden_transition(a, b):
            return False
        if not _can_move(a, b, key_like):
            return False
    tonic = tonic_figure(key_like)
    if cadence == _CADENCE_PAC:
        if len(progression) < 2:
            return False
        if progression[-1] != tonic:
            return False
        if progression[-2] not in ("V", "V7"):
            return False
    elif cadence == _CADENCE_HC:
        if progression[-1] not in ("V", "V7"):
            return False
    return True
