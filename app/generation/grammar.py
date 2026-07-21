"""Layer 1: functional-harmony progression grammar.

Weighted Markov walk over the transition table in
``docs/PARTWRITING-RULES.md`` §9 (+ §9b extended figures). Cadence-aware and
lock-aware. Q3b/Q3c: opt-in color via ``spice`` (0–3) and named ``style``
presets (``student`` / ``hymnal`` / ``spicy``).
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
    "SD": frozenset({"V/V", "V7/V", "V6/V", "V/vi", "V/ii"}),  # Q3b applied
}

FUNCTION_MINOR = {
    "T": frozenset({"i", "VI", "III", "i6"}),
    "PD": frozenset({"iio6", "iv", "iv6"}),
    "D": frozenset({"V", "V7", "viio6", "V6", "Cad64"}),
    "SD": frozenset({"V/V", "V7/V", "V6/V", "V/III", "V/iv"}),  # Q3b applied
}

# Minimum spice required before the free walk may emit these figures.
# (Locked slots may still name them; connectivity uses the full table.)
_SPICE_REQUIRED: Dict[str, int] = {
    "V/V": 2,
    "V7/V": 2,
    "V6/V": 2,
    "V/vi": 3,
    "V/ii": 3,
    "V/III": 3,
    "V/iv": 3,
}

SECONDARY_DOMINANTS = frozenset(_SPICE_REQUIRED)

_MIN_SPICE = 0
_MAX_SPICE = 3

# Q3c named presets → spice (weight packs, not separate engines).
# ``spicy`` maps to spice=2 (V/V family). spice=3 is integer-only (max color).
STYLE_PRESETS: Dict[str, int] = {
    "student": 0,
    "hymnal": 1,
    "spicy": 2,
}
SUPPORTED_STYLES = frozenset(STYLE_PRESETS)

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

# Q3b: secondary-dominant nodes + low-weight approaches (spice-gated in the walk).
# Resolutions only to their local tonics (V/V → V|V7, V/vi → vi, …).
_APPLIED_NODES_MAJOR: Dict[str, List[Tuple[str, float]]] = {
    "V/V": [("V", 5), ("V7", 3)],
    "V7/V": [("V", 5), ("V7", 2)],
    "V6/V": [("V", 5), ("V7", 2)],
    "V/vi": [("vi", 6)],
    "V/ii": [("ii", 5), ("ii6", 2)],
}

_APPLIED_NODES_MINOR: Dict[str, List[Tuple[str, float]]] = {
    "V/V": [("V", 5), ("V7", 3)],
    "V7/V": [("V", 5), ("V7", 2)],
    "V6/V": [("V", 5), ("V7", 2)],
    "V/III": [("III", 6)],
    "V/iv": [("iv", 5), ("iv6", 2)],
}

# Extra edges into applied chords, merged into the diatonic table.
_APPLIED_APPROACHES_MAJOR: Dict[str, List[Tuple[str, float]]] = {
    "I": [("V/V", 1.2), ("V7/V", 1.0), ("V6/V", 0.6), ("V/vi", 0.7), ("V/ii", 0.5)],
    "I6": [("V/V", 0.8), ("V7/V", 0.5), ("V/vi", 0.4)],
    "IV": [("V/V", 1.0), ("V7/V", 0.8), ("V6/V", 0.4)],
    "IV6": [("V/V", 0.5)],
    "vi": [("V/V", 1.0), ("V7/V", 0.6), ("V6/V", 0.5), ("V/ii", 0.4)],
    "iii": [("V/vi", 0.9), ("V/V", 0.4)],
    "ii": [("V/V", 0.4)],
    "ii6": [("V/V", 0.3)],
}

_APPLIED_APPROACHES_MINOR: Dict[str, List[Tuple[str, float]]] = {
    "i": [("V/V", 1.2), ("V7/V", 1.0), ("V6/V", 0.6), ("V/III", 0.7), ("V/iv", 0.5)],
    "i6": [("V/V", 0.8), ("V7/V", 0.5), ("V/III", 0.4)],
    "iv": [("V/V", 1.0), ("V7/V", 0.8), ("V6/V", 0.4)],
    "iv6": [("V/V", 0.5)],
    "VI": [("V/V", 1.0), ("V7/V", 0.6), ("V6/V", 0.5), ("V/iv", 0.4)],
    "III": [("V/III", 0.5), ("V/V", 0.4)],
    "iio6": [("V/V", 0.4)],
}


def _merge_edges(
    base: Dict[str, List[Tuple[str, float]]],
    extra: Mapping[str, List[Tuple[str, float]]],
) -> Dict[str, List[Tuple[str, float]]]:
    out: Dict[str, List[Tuple[str, float]]] = {
        k: list(v) for k, v in base.items()
    }
    for src, edges in extra.items():
        out.setdefault(src, []).extend(edges)
    return out


def _full_transitions_major() -> Dict[str, List[Tuple[str, float]]]:
    merged = _merge_edges(_TRANSITIONS_MAJOR, _APPLIED_APPROACHES_MAJOR)
    merged.update({k: list(v) for k, v in _APPLIED_NODES_MAJOR.items()})
    return merged


def _full_transitions_minor() -> Dict[str, List[Tuple[str, float]]]:
    merged = _merge_edges(_TRANSITIONS_MINOR, _APPLIED_APPROACHES_MINOR)
    merged.update({k: list(v) for k, v in _APPLIED_NODES_MINOR.items()})
    return merged


# Precompute full tables (diatonic + applied connectivity for locks / spice≥2).
_TRANSITIONS_MAJOR_FULL = _full_transitions_major()
_TRANSITIONS_MINOR_FULL = _full_transitions_minor()

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


def spice_required(figure: str) -> int:
    """Minimum ``spice`` for the free walk to emit ``figure``."""
    return _SPICE_REQUIRED.get(figure, 0)


def is_secondary_dominant(figure: str) -> bool:
    return figure in SECONDARY_DOMINANTS or (
        "/" in figure and figure.split("/", 1)[0].startswith(("V", "v", "vii", "VII"))
    )


def transitions_for(key_like: _chords.KeyLike) -> Dict[str, List[Tuple[str, float]]]:
    """Full transition table (diatonic + applied connectivity).

    Applied chords stay in the table so locked secondary dominants remain
    path-legal; the free walk filters them via :func:`legal_successors` and
    ``spice``.
    """
    return (
        _TRANSITIONS_MINOR_FULL
        if is_minor_key(key_like)
        else _TRANSITIONS_MAJOR_FULL
    )


def tonic_figure(key_like: _chords.KeyLike) -> str:
    return "i" if is_minor_key(key_like) else "I"


def _normalize_spice(spice: int) -> int:
    if not isinstance(spice, int) or isinstance(spice, bool):
        raise GrammarError(f"spice must be an int 0–{_MAX_SPICE}, got {spice!r}")
    if spice < _MIN_SPICE or spice > _MAX_SPICE:
        raise GrammarError(
            f"spice must be in {_MIN_SPICE}..{_MAX_SPICE}, got {spice}"
        )
    return spice


def resolve_spice_and_style(
    *,
    spice: int = 0,
    style: Optional[str] = None,
) -> Tuple[int, Optional[str]]:
    """Resolve effective spice and normalized style name.

    If ``style`` is set, it wins over ``spice`` (preset maps to an integer).
    Returns ``(effective_spice, normalized_style_or_None)``.
    """
    if style is None or (isinstance(style, str) and not style.strip()):
        return _normalize_spice(spice), None
    if not isinstance(style, str):
        raise GrammarError(f"style must be a string, got {style!r}")
    key = style.strip().lower()
    if key not in STYLE_PRESETS:
        raise GrammarError(
            f"unsupported style {style!r}; expected one of "
            f"{sorted(SUPPORTED_STYLES)}"
        )
    return STYLE_PRESETS[key], key


def is_forbidden_transition(prev: str, cur: str) -> bool:
    if (prev, cur) in FORBIDDEN_TRANSITIONS:
        return True
    # viio6 may only go to tonic (table already encodes this; enforce hard).
    if prev == "viio6" and cur not in ("I", "i"):
        return True
    # Secondary of V must resolve to V|V7 (house law).
    if prev in ("V/V", "V7/V", "V6/V") and cur not in ("V", "V7"):
        return True
    if prev == "V/vi" and cur != "vi":
        return True
    if prev == "V/ii" and cur not in ("ii", "ii6"):
        return True
    if prev == "V/III" and cur != "III":
        return True
    if prev == "V/iv" and cur not in ("iv", "iv6"):
        return True
    return False


def legal_successors(
    prev: str,
    key_like: _chords.KeyLike,
    *,
    must_precede: Optional[str] = None,
    spice: int = 0,
) -> List[Tuple[str, float]]:
    """Weighted successors of ``prev``, excluding forbidden edges.

    If ``must_precede`` is set, keep only chords that can legally move to that
    figure (one-step lookahead for locked / cadence slots).

    Figures that require a higher ``spice`` than requested are omitted from
    free-walk options (locked slots still use :func:`_can_move` on the full table).
    """
    table = transitions_for(key_like)
    raw = list(table.get(prev, []))
    out: List[Tuple[str, float]] = []
    for fig, weight in raw:
        if weight <= 0 or is_forbidden_transition(prev, fig):
            continue
        if spice_required(fig) > spice:
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
    *,
    spice: int = 0,
) -> bool:
    """Fill None slots. Returns False if stuck (caller may retry)."""
    n = len(result)

    if result[0] is None:
        # Open on tonic (most common); rare alternate tonics later if needed.
        result[0] = tonic_figure(key_like)

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
        options = legal_successors(
            prev, key_like, must_precede=must_precede, spice=spice
        )
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
    spice: int = 0,
    style: Optional[str] = None,
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
        If set, the walk is deterministic for the same arguments
        (including effective ``spice`` / ``style``).
    spice:
        0–3 color knob. ``0`` (default) is student-safe: no secondary
        dominants in free walk. ``2+`` enables ``V/V`` family; ``3`` also
        ``V/vi`` / ``V/ii`` (major) or minor analogues.
    style:
        Optional preset alias: ``student`` (0), ``hymnal`` (1), ``spicy`` (2).
        When set, **style wins** over ``spice``.
    """
    if length < 1:
        raise GrammarError("length must be >= 1")
    spice, _ = resolve_spice_and_style(spice=spice, style=style)
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
        if _fill_left_to_right(result, key_like, rng, spice=spice):
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
    # Applied chords are never final (cadence template already enforces V/I).
    if progression and is_secondary_dominant(progression[-1]):
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
