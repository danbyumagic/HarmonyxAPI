"""Progression validator (theory house rules + optional engine realizability).

L2 of ``docs/LLM-PROGRESSION-SPEC.md``. Optional L3 suggestions via
``suggest=True`` (deterministic fixer in ``fix.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from . import chords as _chords
from .grammar import is_forbidden_transition, tonic_figure
from .realize import RealizationError, realize
from .voicing import candidate_voicings

# Issue codes from LLM-PROGRESSION-SPEC §6.3
CODE_EMPTY = "empty_progression"
CODE_UNKNOWN = "unknown_figure"
CODE_FORBIDDEN = "forbidden_transition"
CODE_CADENCE = "cadence_mismatch"
CODE_LOCK = "lock_conflict"
CODE_UNREAL_CHORD = "unrealizable_chord"
CODE_UNREAL_PATH = "unrealizable_path"
CODE_SPICE_STRIPPED = "spice_stripped"
CODE_NORMALIZED = "normalized_figure"

SEVERITY_BLOCK = "block"
SEVERITY_INFO = "info"

GATE_THEORY = "theory"
GATE_ENGINE = "engine"

_SUPPORTED_CADENCES = frozenset({"PAC", "HC"})


@dataclass(frozen=True)
class Suggestion:
    """A proposed alternate progression (filled by L3 fixer; empty in L2)."""

    label: str
    progression: Tuple[str, ...]
    edits: Tuple[Mapping[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "progression": list(self.progression),
            "edits": [dict(e) for e in self.edits],
        }


@dataclass(frozen=True)
class ProgressionIssue:
    """One validation problem (or info note) about a progression."""

    code: str
    severity: str
    message: str
    gate: str
    index: Optional[int] = None
    span: Optional[Tuple[int, int]] = None
    found: Optional[Mapping[str, Any]] = None
    suggestions: Tuple[Suggestion, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "gate": self.gate,
            "message": self.message,
            "suggestions": [s.as_dict() for s in self.suggestions],
        }
        if self.index is not None:
            out["index"] = self.index
        if self.span is not None:
            out["span"] = list(self.span)
        if self.found is not None:
            out["found"] = dict(self.found)
        return out


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of :func:`validate_progression`."""

    ok: bool
    progression: Tuple[str, ...]
    issues: Tuple[ProgressionIssue, ...] = ()
    key: Optional[str] = None
    cadence: Optional[str] = None
    suggestions: Tuple[Suggestion, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "progression": list(self.progression),
            "issues": [i.as_dict() for i in self.issues],
            "suggestions": [s.as_dict() for s in self.suggestions],
        }
        if self.key is not None:
            out["key"] = self.key
        if self.cadence is not None:
            out["cadence"] = self.cadence
        return out

    @property
    def blocking_issues(self) -> Tuple[ProgressionIssue, ...]:
        return tuple(i for i in self.issues if i.severity == SEVERITY_BLOCK)


def validate_progression(
    progression: Sequence[str],
    key_like: _chords.KeyLike,
    *,
    cadence: Optional[str] = None,
    locked: Optional[Mapping[int, str]] = None,
    check_engine: bool = True,
    suggest: bool = False,
    max_suggestions: int = 3,
) -> ValidationResult:
    """Validate a Roman-numeral progression against house rules and (optionally) the realizer.

    Parameters
    ----------
    progression:
        Ordered Roman figures (e.g. ``["I", "V", "I"]``).
    key_like:
        Key string or music21 Key (needed for figure parse + engine).
    cadence:
        If ``"PAC"`` or ``"HC"``, enforce the same cadence contract as the
        grammar. If ``None``, skip cadence checks (useful for open fragments).
    locked:
        Map of index → required figure; mismatches yield ``lock_conflict``.
    check_engine:
        When True (default), also require per-chord candidate voicings and a
        successful ``realize`` path. Set False for cheap theory-only checks.
    suggest:
        When True and validation fails, attach deterministic L3 fix suggestions
        (also copied onto the first blocking issue).
    max_suggestions:
        Cap on L3 suggestions (default 3).

    Returns
    -------
    ValidationResult
        ``ok`` is True iff there are no ``severity == "block"`` issues.
    """
    figures = [str(f).strip() for f in progression]
    key_str = str(key_like) if not isinstance(key_like, str) else key_like
    issues: List[ProgressionIssue] = []

    cadence_norm: Optional[str] = None
    if cadence is not None:
        cadence_norm = str(cadence).strip().upper()
        if cadence_norm not in _SUPPORTED_CADENCES:
            issues.append(
                ProgressionIssue(
                    code=CODE_CADENCE,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    message=(
                        f"Unsupported cadence {cadence!r}; "
                        f"expected one of {sorted(_SUPPORTED_CADENCES)} or omit."
                    ),
                    found={"cadence": cadence},
                )
            )
            # Still run other checks; do not apply PAC/HC shape rules.
            cadence_norm = None

    cadence_out = cadence_norm if cadence is not None else None

    # --- Gate A: theory / house style ------------------------------------
    if not figures or any(not f for f in figures):
        if not figures:
            issues.append(
                ProgressionIssue(
                    code=CODE_EMPTY,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    message="Progression is empty; provide at least one Roman numeral.",
                )
            )
        else:
            for i, f in enumerate(figures):
                if not f:
                    issues.append(
                        ProgressionIssue(
                            code=CODE_EMPTY,
                            severity=SEVERITY_BLOCK,
                            gate=GATE_THEORY,
                            index=i,
                            span=(i, i),
                            found={"figure": f},
                            message=(
                                f"Beat {i + 1}: empty figure; "
                                "each slot needs a Roman numeral."
                            ),
                        )
                    )
        return _with_suggestions(
            ValidationResult(
                ok=False,
                progression=tuple(figures),
                issues=tuple(issues),
                key=key_str,
                cadence=cadence_out,
            ),
            key_like=key_like,
            cadence=cadence_norm,
            locked=locked,
            check_engine=check_engine,
            suggest=suggest,
            max_suggestions=max_suggestions,
        )

    locked_map = _normalize_locked(locked, len(figures), issues)

    for i, fig in enumerate(figures):
        if not _figure_parseable(fig, key_like):
            issues.append(
                ProgressionIssue(
                    code=CODE_UNKNOWN,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    index=i,
                    span=(i, i),
                    found={"figure": fig},
                    message=(
                        f"Beat {i + 1}: {fig!r} is not a parseable Roman numeral "
                        f"in {key_str}."
                    ),
                )
            )

    for i, expected in locked_map.items():
        actual = figures[i]
        if actual != expected:
            issues.append(
                ProgressionIssue(
                    code=CODE_LOCK,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    index=i,
                    span=(i, i),
                    found={"expected": expected, "actual": actual},
                    message=(
                        f"Beat {i + 1}: locked to {expected!r} but progression "
                        f"has {actual!r}."
                    ),
                )
            )

    for i in range(len(figures) - 1):
        prev, cur = figures[i], figures[i + 1]
        # Only check pairs where both figures exist (empty already flagged).
        if not prev or not cur:
            continue
        if is_forbidden_transition(prev, cur):
            issues.append(
                ProgressionIssue(
                    code=CODE_FORBIDDEN,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    index=i,
                    span=(i, i + 1),
                    found={"from": prev, "to": cur},
                    message=(
                        f"Beat {i + 2}: {prev} → {cur} is a transition we don't "
                        f"allow in house style."
                    ),
                )
            )

    if cadence_norm is not None:
        issues.extend(_cadence_issues(figures, key_like, cadence_norm))

    # --- Gate B: engine --------------------------------------------------
    theory_unknown = any(i.code == CODE_UNKNOWN for i in issues)
    if check_engine and not theory_unknown:
        issues.extend(_engine_issues(figures, key_like))

    blocking = [i for i in issues if i.severity == SEVERITY_BLOCK]
    result = ValidationResult(
        ok=len(blocking) == 0,
        progression=tuple(figures),
        issues=tuple(issues),
        key=key_str,
        cadence=cadence_out,
    )
    return _with_suggestions(
        result,
        key_like=key_like,
        cadence=cadence_norm,
        locked=locked_map or locked,
        check_engine=check_engine,
        suggest=suggest,
        max_suggestions=max_suggestions,
    )


def _with_suggestions(
    result: ValidationResult,
    *,
    key_like: _chords.KeyLike,
    cadence: Optional[str],
    locked: Optional[Mapping[int, str]],
    check_engine: bool,
    suggest: bool,
    max_suggestions: int,
) -> ValidationResult:
    if not suggest or result.ok:
        return result
    # Lazy import avoids fix ↔ validate cycle at module load.
    from .fix import suggest_fixes

    suggestions = tuple(
        suggest_fixes(
            result.progression,
            key_like,
            cadence=cadence,
            locked=locked,
            check_engine=check_engine,
            max_suggestions=max_suggestions,
        )
    )
    if not suggestions:
        return replace(result, suggestions=())

    issues = list(result.issues)
    for i, issue in enumerate(issues):
        if issue.severity == SEVERITY_BLOCK:
            issues[i] = replace(issue, suggestions=suggestions)
            break
    return replace(result, issues=tuple(issues), suggestions=suggestions)


def _figure_parseable(figure: str, key_like: _chords.KeyLike) -> bool:
    try:
        _chords.roman_numeral(figure, key_like)
        return True
    except Exception:
        return False


def _normalize_locked(
    locked: Optional[Mapping[int, str]],
    length: int,
    issues: List[ProgressionIssue],
) -> dict[int, str]:
    if not locked:
        return {}
    out: dict[int, str] = {}
    for raw_i, figure in locked.items():
        try:
            i = int(raw_i)
        except (TypeError, ValueError):
            issues.append(
                ProgressionIssue(
                    code=CODE_LOCK,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    found={"index": raw_i, "figure": figure},
                    message=f"Lock index {raw_i!r} is not an integer.",
                )
            )
            continue
        if i < 0 or i >= length:
            issues.append(
                ProgressionIssue(
                    code=CODE_LOCK,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    index=i,
                    found={"index": i, "figure": figure, "length": length},
                    message=(
                        f"Lock index {i} is out of range for a progression "
                        f"of length {length}."
                    ),
                )
            )
            continue
        fig = str(figure).strip()
        if not fig:
            issues.append(
                ProgressionIssue(
                    code=CODE_LOCK,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    index=i,
                    span=(i, i),
                    found={"index": i, "figure": figure},
                    message=f"Beat {i + 1}: locked figure is empty.",
                )
            )
            continue
        out[i] = fig
    return out


def _cadence_issues(
    figures: Sequence[str],
    key_like: _chords.KeyLike,
    cadence: str,
) -> List[ProgressionIssue]:
    issues: List[ProgressionIssue] = []
    n = len(figures)
    tonic = tonic_figure(key_like)

    if cadence == "PAC":
        if n < 2:
            issues.append(
                ProgressionIssue(
                    code=CODE_CADENCE,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    found={"cadence": "PAC", "length": n},
                    message="PAC requires at least two chords (V|V7 → tonic).",
                )
            )
            return issues
        pen, final = figures[-2], figures[-1]
        if pen not in ("V", "V7"):
            issues.append(
                ProgressionIssue(
                    code=CODE_CADENCE,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    index=n - 2,
                    span=(n - 2, n - 1),
                    found={
                        "cadence": "PAC",
                        "penultimate": pen,
                        "final": final,
                        "expected_penultimate": ["V", "V7"],
                    },
                    message=(
                        f"Beat {n - 1}: PAC expects penultimate V or V7, "
                        f"found {pen!r}."
                    ),
                )
            )
        if final != tonic:
            issues.append(
                ProgressionIssue(
                    code=CODE_CADENCE,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    index=n - 1,
                    span=(n - 1, n - 1),
                    found={
                        "cadence": "PAC",
                        "final": final,
                        "expected_final": tonic,
                    },
                    message=(
                        f"Beat {n}: PAC expects final tonic {tonic!r}, "
                        f"found {final!r}."
                    ),
                )
            )
    elif cadence == "HC":
        final = figures[-1]
        if final not in ("V", "V7"):
            issues.append(
                ProgressionIssue(
                    code=CODE_CADENCE,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_THEORY,
                    index=n - 1,
                    span=(n - 1, n - 1),
                    found={
                        "cadence": "HC",
                        "final": final,
                        "expected_final": ["V", "V7"],
                    },
                    message=(
                        f"Beat {n}: HC expects final V or V7, found {final!r}."
                    ),
                )
            )
    return issues


def _engine_issues(
    figures: Sequence[str],
    key_like: _chords.KeyLike,
) -> List[ProgressionIssue]:
    issues: List[ProgressionIssue] = []
    for i, fig in enumerate(figures):
        try:
            cands = candidate_voicings(fig, key_like, limit=50)
        except Exception as exc:
            issues.append(
                ProgressionIssue(
                    code=CODE_UNREAL_CHORD,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_ENGINE,
                    index=i,
                    span=(i, i),
                    found={"figure": fig, "error": str(exc)},
                    message=(
                        f"Beat {i + 1}: {fig!r} could not be voiced "
                        f"({exc})."
                    ),
                )
            )
            continue
        if not cands:
            issues.append(
                ProgressionIssue(
                    code=CODE_UNREAL_CHORD,
                    severity=SEVERITY_BLOCK,
                    gate=GATE_ENGINE,
                    index=i,
                    span=(i, i),
                    found={"figure": fig},
                    message=(
                        f"Beat {i + 1}: no legal SATB voicing for {fig!r} "
                        f"in this key."
                    ),
                )
            )

    # If any chord is already unrealizable, path check is redundant noise.
    if any(i.code == CODE_UNREAL_CHORD for i in issues):
        return issues

    try:
        realize(list(figures), key_like)
    except RealizationError as exc:
        issues.append(
            ProgressionIssue(
                code=CODE_UNREAL_PATH,
                severity=SEVERITY_BLOCK,
                gate=GATE_ENGINE,
                found={"error": str(exc)},
                message=(
                    "No legal voice-leading path through this progression "
                    f"({exc}). Edit chords or try a shorter phrase."
                ),
            )
        )
    except Exception as exc:
        issues.append(
            ProgressionIssue(
                code=CODE_UNREAL_PATH,
                severity=SEVERITY_BLOCK,
                gate=GATE_ENGINE,
                found={"error": str(exc)},
                message=f"Realizer failed on this progression ({exc}).",
            )
        )
    return issues
