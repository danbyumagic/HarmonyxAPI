"""Deterministic progression fixer (minimal-edit suggestions).

L3 of ``docs/LLM-PROGRESSION-SPEC.md``. Preference order:

1. Minimal number of chord edits
2. Honor locked slots
3. Preserve requested cadence
4. Prefer labeled musical fixes (resolve, deceptive, align cadence)
5. Fall back to bland textbook shapes when needed
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from . import chords as _chords
from .grammar import (
    is_forbidden_transition,
    is_minor_key,
    legal_successors,
    tonic_figure,
    transitions_for,
)
from .validate import Suggestion, validate_progression

# Cap search cost; L3 is interactive, not exhaustive.
_MAX_SUGGESTIONS = 3
_MAX_SINGLE_SLOT_ALTS = 12
_MAX_TWO_EDIT_PAIRS = 40

# Ordered pools for replacement search (common-practice textbook first).
_POOL_MAJOR: Tuple[str, ...] = (
    "I",
    "V",
    "V7",
    "IV",
    "ii",
    "ii6",
    "vi",
    "I6",
    "V6",
    "IV6",
    "iii",
    "viio6",
    "Cad64",
)
_POOL_MINOR: Tuple[str, ...] = (
    "i",
    "V",
    "V7",
    "iv",
    "iio6",
    "VI",
    "i6",
    "V6",
    "iv6",
    "III",
    "viio6",
    "Cad64",
)


def suggest_fixes(
    progression: Sequence[str],
    key_like: _chords.KeyLike,
    *,
    cadence: Optional[str] = None,
    locked: Optional[Mapping[int, str]] = None,
    check_engine: bool = False,
    max_suggestions: int = _MAX_SUGGESTIONS,
) -> List[Suggestion]:
    """Return up to ``max_suggestions`` alternate progressions that validate.

    Uses theory validation by default (``check_engine=False``) so suggestion
    search stays cheap; pass ``check_engine=True`` when suggestions must also
    realize.
    """
    max_suggestions = max(0, int(max_suggestions))
    if max_suggestions == 0:
        return []

    figures = [str(f).strip() for f in progression]
    cadence_arg = cadence
    if cadence is not None:
        c = str(cadence).strip().upper()
        cadence_arg = c if c in ("PAC", "HC") else None

    locked_map = _safe_locked(locked, len(figures) if figures else 0)

    # Empty → propose a short legal phrase.
    if not figures or any(not f for f in figures):
        return _empty_suggestions(
            key_like,
            cadence=cadence_arg,
            check_engine=check_engine,
            max_suggestions=max_suggestions,
        )

    # Already valid → nothing to fix.
    baseline = validate_progression(
        figures,
        key_like,
        cadence=cadence_arg,
        locked=locked_map or None,
        check_engine=check_engine,
        suggest=False,
    )
    if baseline.ok:
        return []

    # rank key: (n_edits, quality_score, strategy_priority, progression, label, edits)
    ranked: List[
        Tuple[int, int, int, Tuple[str, ...], str, Tuple[Dict[str, Any], ...]]
    ] = []
    seen: set[Tuple[str, ...]] = set()

    def consider(candidate: Sequence[str], label: str, priority: int) -> None:
        prog = tuple(str(x).strip() for x in candidate)
        if len(prog) != len(figures) or prog in seen:
            return
        if not _honors_locks(prog, locked_map):
            return
        edits = _edits(figures, prog)
        if not edits and prog != tuple(figures):
            return
        result = validate_progression(
            prog,
            key_like,
            cadence=cadence_arg,
            locked=locked_map or None,
            check_engine=check_engine,
            suggest=False,
        )
        if not result.ok:
            return
        seen.add(prog)
        quality = _quality_score(figures, prog, edits, label)
        ranked.append((len(edits), quality, priority, prog, label, edits))

    # --- Strategy A: cadence-only repair ---------------------------------
    cad_fixed = _apply_cadence_repair(figures, key_like, cadence_arg, locked_map)
    if cad_fixed != figures:
        consider(cad_fixed, "Align cadence", priority=0)

    # --- Strategy C first: fix forbidden edge (prefer changing "to") -----
    for i in range(len(figures) - 1):
        prev, cur = figures[i], figures[i + 1]
        if not prev or not cur or not is_forbidden_transition(prev, cur):
            continue
        # Change destination (best musical default for retrogressions).
        if (i + 1) not in locked_map:
            for fig in _successors_of(prev, key_like):
                trial = list(figures)
                trial[i + 1] = fig
                trial = _apply_cadence_repair(trial, key_like, cadence_arg, locked_map)
                consider(
                    trial,
                    _label_for_edit(i + 1, cur, trial[i + 1], key_like),
                    priority=0,
                )
        # Change source.
        if i not in locked_map:
            for fig in _predecessors_of(cur, key_like):
                trial = list(figures)
                trial[i] = fig
                trial = _apply_cadence_repair(trial, key_like, cadence_arg, locked_map)
                consider(
                    trial,
                    _label_for_edit(i, prev, trial[i], key_like),
                    priority=2,
                )

    # --- Strategy B: single-slot replacements ----------------------------
    for i in range(len(figures)):
        if i in locked_map:
            continue
        for fig in _alternatives_for_slot(figures, i, key_like):
            if fig == figures[i]:
                continue
            trial = list(figures)
            trial[i] = fig
            trial = _apply_cadence_repair(trial, key_like, cadence_arg, locked_map)
            label = _label_for_edit(i, figures[i], trial[i], key_like)
            consider(trial, label, priority=1)

    # --- Strategy D: two-slot edits (only if still few suggestions) ------
    if len(ranked) < max_suggestions:
        unlocked = [i for i in range(len(figures)) if i not in locked_map]
        pairs_tried = 0
        for a_i, idx_a in enumerate(unlocked):
            for idx_b in unlocked[a_i + 1 :]:
                if pairs_tried >= _MAX_TWO_EDIT_PAIRS:
                    break
                alts_a = _alternatives_for_slot(figures, idx_a, key_like)[
                    :_MAX_SINGLE_SLOT_ALTS
                ]
                alts_b = _alternatives_for_slot(figures, idx_b, key_like)[
                    :_MAX_SINGLE_SLOT_ALTS
                ]
                for fa in alts_a:
                    if fa == figures[idx_a]:
                        continue
                    for fb in alts_b:
                        if fb == figures[idx_b]:
                            continue
                        pairs_tried += 1
                        if pairs_tried > _MAX_TWO_EDIT_PAIRS:
                            break
                        trial = list(figures)
                        trial[idx_a] = fa
                        trial[idx_b] = fb
                        trial = _apply_cadence_repair(
                            trial, key_like, cadence_arg, locked_map
                        )
                        consider(trial, "Two-chord textbook fix", priority=3)
                if pairs_tried >= _MAX_TWO_EDIT_PAIRS:
                    break
            if pairs_tried >= _MAX_TWO_EDIT_PAIRS:
                break

    # --- Strategy E: bland phrase of same length -------------------------
    if len(ranked) < max_suggestions:
        bland = _bland_phrase(len(figures), key_like, cadence_arg, locked_map)
        if bland is not None:
            consider(bland, "Bland textbook phrase", priority=5)

    ranked.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    out: List[Suggestion] = []
    for _n, _q, _p, prog, label, edits in ranked[:max_suggestions]:
        out.append(
            Suggestion(
                label=label,
                progression=prog,
                edits=tuple(edits),
            )
        )
    return out


def _quality_score(
    original: Sequence[str],
    candidate: Sequence[str],
    edits: Tuple[Dict[str, Any], ...],
    label: str,
) -> int:
    """Lower is better. Prefer musical labels and fixing forbidden *destinations*."""
    score = 0
    if label in ("Resolve to tonic", "Deceptive", "Align cadence", "Use dominant"):
        score -= 10
    if label == "Bland textbook phrase":
        score += 20
    if label == "Two-chord textbook fix":
        score += 8

    edit_idxs = {e["index"] for e in edits}
    for i in range(len(original) - 1):
        if is_forbidden_transition(original[i], original[i + 1]):
            if (i + 1) in edit_idxs:
                score -= 6  # fixed the bad arrival chord
            elif i in edit_idxs:
                score += 2  # rewrote the departure chord instead

    # Cad64 should only sit immediately before V/V7.
    for i, fig in enumerate(candidate):
        if fig != "Cad64":
            continue
        nxt = candidate[i + 1] if i + 1 < len(candidate) else None
        if nxt not in ("V", "V7"):
            score += 12
    return score


def _empty_suggestions(
    key_like: _chords.KeyLike,
    *,
    cadence: Optional[str],
    check_engine: bool,
    max_suggestions: int,
) -> List[Suggestion]:
    tonic = tonic_figure(key_like)
    seeds: List[Tuple[str, List[str]]] = []
    if cadence == "HC":
        seeds.append(("Short half cadence", [tonic, "IV", "V"]))
        seeds.append(("Minimal HC", [tonic, "V"]))
    else:
        seeds.append(("Short PAC", [tonic, "V", tonic]))
        seeds.append(("Textbook PAC", [tonic, "IV", "V", tonic]))
        if cadence != "PAC":
            seeds.append(("Short half cadence", [tonic, "IV", "V"]))

    out: List[Suggestion] = []
    for label, prog in seeds:
        result = validate_progression(
            prog,
            key_like,
            cadence=cadence,
            check_engine=check_engine,
            suggest=False,
        )
        if result.ok:
            out.append(
                Suggestion(
                    label=label,
                    progression=tuple(prog),
                    edits=tuple(
                        {"index": i, "from": None, "to": fig}
                        for i, fig in enumerate(prog)
                    ),
                )
            )
        if len(out) >= max_suggestions:
            break
    return out


def _safe_locked(
    locked: Optional[Mapping[int, str]], length: int
) -> Dict[int, str]:
    if not locked or length <= 0:
        return {}
    out: Dict[int, str] = {}
    for raw_i, figure in locked.items():
        try:
            i = int(raw_i)
        except (TypeError, ValueError):
            continue
        if 0 <= i < length:
            fig = str(figure).strip()
            if fig:
                out[i] = fig
    return out


def _honors_locks(prog: Sequence[str], locked: Mapping[int, str]) -> bool:
    for i, fig in locked.items():
        if i < 0 or i >= len(prog) or prog[i] != fig:
            return False
    return True


def _edits(
    original: Sequence[str], candidate: Sequence[str]
) -> Tuple[Dict[str, Any], ...]:
    edits: List[Dict[str, Any]] = []
    for i, (a, b) in enumerate(zip(original, candidate)):
        if a != b:
            edits.append({"index": i, "from": a, "to": b})
    return tuple(edits)


def _apply_cadence_repair(
    figures: Sequence[str],
    key_like: _chords.KeyLike,
    cadence: Optional[str],
    locked: Mapping[int, str],
) -> List[str]:
    """Force free cadence slots toward PAC/HC when a cadence is requested."""
    out = list(figures)
    if not cadence or not out:
        return out
    n = len(out)
    tonic = tonic_figure(key_like)
    if cadence == "PAC" and n >= 2:
        if (n - 1) not in locked:
            out[n - 1] = tonic
        if (n - 2) not in locked and out[n - 2] not in ("V", "V7"):
            # Prefer V; keep V7 if already a dominant seventh.
            out[n - 2] = "V"
    elif cadence == "HC":
        if (n - 1) not in locked and out[n - 1] not in ("V", "V7"):
            out[n - 1] = "V"
    return out


def _pool(key_like: _chords.KeyLike) -> Tuple[str, ...]:
    return _POOL_MINOR if is_minor_key(key_like) else _POOL_MAJOR


def _successors_of(prev: str, key_like: _chords.KeyLike) -> List[str]:
    """Legal or preferred figures after ``prev`` (deterministic order)."""
    ordered: List[str] = []
    seen: set[str] = set()

    def add(fig: str) -> None:
        if fig and fig not in seen and not is_forbidden_transition(prev, fig):
            seen.add(fig)
            ordered.append(fig)

    # Grammar table first (when known).
    for fig, _w in legal_successors(prev, key_like):
        add(fig)

    # Secondary-dominant heuristic: V/x or V7/x → x (and V if x is V).
    if "/" in prev:
        target = prev.split("/", 1)[1]
        add(target)
        if target in ("V", "V7"):
            add("V")
            add("V7")

    tonic = tonic_figure(key_like)
    # Dominant defaults.
    if prev in ("V", "V7", "V6", "Cad64"):
        add(tonic)
        if not is_minor_key(key_like):
            add("vi")
        else:
            add("VI")
        add("V7" if prev != "V7" else "V")

    if prev == "viio6":
        add(tonic)

    for fig in _pool(key_like):
        add(fig)
    return ordered


def _predecessors_of(cur: str, key_like: _chords.KeyLike) -> List[str]:
    ordered: List[str] = []
    seen: set[str] = set()

    def add(fig: str) -> None:
        if fig and fig not in seen and not is_forbidden_transition(fig, cur):
            seen.add(fig)
            ordered.append(fig)

    table = transitions_for(key_like)
    for prev, edges in table.items():
        if any(fig == cur and w > 0 for fig, w in edges):
            add(prev)
    for fig in _pool(key_like):
        add(fig)
    return ordered


def _alternatives_for_slot(
    figures: Sequence[str],
    index: int,
    key_like: _chords.KeyLike,
) -> List[str]:
    """Ranked replacement figures for ``figures[index]``."""
    prev = figures[index - 1] if index > 0 else None
    nxt = figures[index + 1] if index + 1 < len(figures) else None
    ordered: List[str] = []
    seen: set[str] = set()

    def add(fig: str) -> None:
        if not fig or fig in seen:
            return
        if prev is not None and is_forbidden_transition(prev, fig):
            return
        if nxt is not None and is_forbidden_transition(fig, nxt):
            return
        seen.add(fig)
        ordered.append(fig)

    if prev is not None:
        for fig in _successors_of(prev, key_like):
            add(fig)
    if nxt is not None:
        for fig in _predecessors_of(nxt, key_like):
            add(fig)
    for fig in _pool(key_like):
        add(fig)
    # Unknown / empty slot: always allow tonic.
    add(tonic_figure(key_like))
    return ordered[:_MAX_SINGLE_SLOT_ALTS]


def roman_alternatives_for_slot(
    progression: Sequence[str],
    key_like: _chords.KeyLike,
    index: int,
    *,
    locked: Optional[Mapping[int, str]] = None,
    cadence: Optional[str] = None,
    max_alternatives: int = 6,
) -> List[Dict[str, str]]:
    """Up to ``max_alternatives`` theory-valid replacement figures for
    ``progression[index]``.

    Each candidate from ``_alternatives_for_slot`` (already filtered for
    forbidden transitions into/out of the immediate neighbors) is swapped in
    and re-checked against the *whole* progression via
    ``validate_progression`` (theory gate only, ``check_engine=False``) --
    this also catches cadence-shape and non-adjacent forbidden-edge
    violations that a neighbor-only check would miss.

    Returns ``[]`` if ``index`` is locked (nothing to suggest) or if no
    candidate keeps the progression valid. Raises ``ValueError`` if
    ``index`` is out of range.
    """
    figures = [str(f).strip() for f in progression]
    if index < 0 or index >= len(figures):
        raise ValueError(
            f"index {index} out of range for progression of length {len(figures)}"
        )

    locked_map = _safe_locked(locked, len(figures))
    if index in locked_map:
        return []

    cadence_arg = cadence
    if cadence is not None:
        c = str(cadence).strip().upper()
        cadence_arg = c if c in ("PAC", "HC") else None

    current = figures[index]
    out: List[Dict[str, str]] = []
    for fig in _alternatives_for_slot(figures, index, key_like):
        if fig == current:
            continue
        trial = list(figures)
        trial[index] = fig
        result = validate_progression(
            trial,
            key_like,
            cadence=cadence_arg,
            locked=locked_map or None,
            check_engine=False,
            suggest=False,
        )
        if not result.ok:
            continue
        out.append(
            {"figure": fig, "label": _label_for_edit(index, current, fig, key_like)}
        )
        if len(out) >= max_alternatives:
            break
    return out


def _label_for_edit(
    index: int,
    old: str,
    new: str,
    key_like: _chords.KeyLike,
) -> str:
    tonic = tonic_figure(key_like)
    if new == tonic and old != tonic:
        return "Resolve to tonic"
    if new in ("vi", "VI") and old not in ("vi", "VI"):
        return "Deceptive"
    if new in ("V", "V7") and old not in ("V", "V7"):
        return "Use dominant"
    if old and not old.strip():
        return f"Fill beat {index + 1}"
    return f"Beat {index + 1}: {old} → {new}"


def _bland_phrase(
    length: int,
    key_like: _chords.KeyLike,
    cadence: Optional[str],
    locked: Mapping[int, str],
) -> Optional[List[str]]:
    """Construct a simple legal phrase of ``length``, honoring locks."""
    if length < 1:
        return None
    tonic = tonic_figure(key_like)
    if cadence == "HC":
        template = [tonic, "IV", "V"]
    else:
        template = [tonic, "IV", "V", tonic]

    # Stretch/shrink template to length.
    if length <= len(template):
        # Prefer keeping the cadence end of the template.
        if cadence == "HC":
            base = (template * length)[:length]
            base[-1] = "V"
            if length >= 2:
                base[0] = tonic
        else:
            base = [tonic] * length
            if length >= 2:
                base[-1] = tonic
                base[-2] = "V"
            if length >= 3:
                base[-3] = "IV"
            if length >= 4:
                base[0] = tonic
    else:
        base = [tonic]
        while len(base) < length - 2:
            # Oscillate blandly without forbidden edges.
            base.append("IV" if not is_minor_key(key_like) else "iv")
            if len(base) < length - 2:
                base.append(tonic)
        if cadence == "HC":
            while len(base) < length - 1:
                base.append(tonic)
            base.append("V")
        else:
            while len(base) < length - 2:
                base.append(tonic)
            base.extend(["V", tonic])
        base = base[:length]
        if cadence == "PAC" and length >= 2:
            base[-1] = tonic
            base[-2] = "V"
        elif cadence == "HC":
            base[-1] = "V"

    for i, fig in locked.items():
        if 0 <= i < length:
            base[i] = fig
    # Re-apply cadence on free slots after locks.
    base = _apply_cadence_repair(base, key_like, cadence, locked)
    return base
