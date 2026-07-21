"""Progression corpus loader (LLM few-shot grounding).

L1 of ``docs/LLM-PROGRESSION-SPEC.md``: load and schema-validate curated
Roman-numeral phrases. Theory-house validation of transitions is L2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Mapping, Optional, Sequence, Union

PathLike = Union[str, Path]

# Minimal required fields per LLM-PROGRESSION-SPEC §5.2
_REQUIRED_FIELDS = frozenset({"id", "key", "progression", "cadence", "tags"})
_SUPPORTED_CADENCES = frozenset({"PAC", "HC", "IAC", "DC", "PC", "other"})
_SUPPORTED_MODES = frozenset({"major", "minor"})


class CorpusError(ValueError):
    """Raised when the corpus file or an entry fails schema validation."""


@dataclass(frozen=True)
class CorpusSource:
    type: str
    ref: str = ""
    license: str = ""


@dataclass(frozen=True)
class CorpusQuality:
    spice: Optional[int] = None
    student_safe: Optional[bool] = None
    realizer_ok: Optional[bool] = None


@dataclass(frozen=True)
class CorpusEntry:
    """One curated progression phrase for few-shot / retrieval."""

    id: str
    key: str
    progression: tuple[str, ...]
    cadence: str
    tags: tuple[str, ...]
    mode: Optional[str] = None
    length: Optional[int] = None
    source: Optional[CorpusSource] = None
    region: Optional[tuple[Mapping[str, Any], ...]] = None
    quality: Optional[CorpusQuality] = None
    notes: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        """Serialize back to a JSON-friendly dict (for tests / dump)."""
        out: dict[str, Any] = {
            "id": self.id,
            "key": self.key,
            "progression": list(self.progression),
            "cadence": self.cadence,
            "tags": list(self.tags),
        }
        if self.mode is not None:
            out["mode"] = self.mode
        if self.length is not None:
            out["length"] = self.length
        if self.source is not None:
            out["source"] = {
                "type": self.source.type,
                "ref": self.source.ref,
                "license": self.source.license,
            }
        if self.region is not None:
            out["region"] = [dict(r) for r in self.region]
        if self.quality is not None:
            q: dict[str, Any] = {}
            if self.quality.spice is not None:
                q["spice"] = self.quality.spice
            if self.quality.student_safe is not None:
                q["student_safe"] = self.quality.student_safe
            if self.quality.realizer_ok is not None:
                q["realizer_ok"] = self.quality.realizer_ok
            if q:
                out["quality"] = q
        if self.notes is not None:
            out["notes"] = self.notes
        return out


def default_corpus_path() -> Path:
    """Repo ``data/progression_corpus.json`` (relative to this package)."""
    # app/generation/corpus.py -> parents[2] == repo root
    return Path(__file__).resolve().parents[2] / "data" / "progression_corpus.json"


def load_corpus(path: Optional[PathLike] = None) -> List[CorpusEntry]:
    """Load and schema-validate the progression corpus from disk.

    Parameters
    ----------
    path:
        JSON file path. Defaults to :func:`default_corpus_path`.

    Returns
    -------
    list[CorpusEntry]
        Validated entries in file order.

    Raises
    ------
    CorpusError
        Missing file, bad JSON shape, or invalid entry.
    """
    corpus_path = Path(path) if path is not None else default_corpus_path()
    if not corpus_path.is_file():
        raise CorpusError(f"corpus file not found: {corpus_path}")
    try:
        raw = json.loads(corpus_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusError(f"invalid JSON in {corpus_path}: {exc}") from exc
    return parse_corpus_payload(raw, source=str(corpus_path))


def parse_corpus_payload(
    data: Any,
    *,
    source: str = "<payload>",
) -> List[CorpusEntry]:
    """Validate an in-memory corpus payload and return entries.

    Accepts either ``{"version": ..., "entries": [...]}`` or a bare list of
    entry objects.
    """
    if isinstance(data, list):
        entries_raw = data
    elif isinstance(data, Mapping):
        if "entries" not in data:
            raise CorpusError(f"{source}: top-level object must contain 'entries'")
        entries_raw = data["entries"]
        if not isinstance(entries_raw, list):
            raise CorpusError(f"{source}: 'entries' must be a list")
        version = data.get("version")
        if version is not None and not isinstance(version, int):
            raise CorpusError(f"{source}: 'version' must be an int when present")
    else:
        raise CorpusError(f"{source}: expected object or list, got {type(data).__name__}")

    if not entries_raw:
        raise CorpusError(f"{source}: corpus has no entries")

    entries: List[CorpusEntry] = []
    seen_ids: set[str] = set()
    for i, item in enumerate(entries_raw):
        entry = _parse_entry(item, index=i, source=source)
        if entry.id in seen_ids:
            raise CorpusError(f"{source}: duplicate entry id {entry.id!r}")
        seen_ids.add(entry.id)
        entries.append(entry)
    return entries


def filter_entries(
    entries: Sequence[CorpusEntry],
    *,
    tags: Optional[Sequence[str]] = None,
    cadence: Optional[str] = None,
    mode: Optional[str] = None,
    max_spice: Optional[int] = None,
    require_all_tags: bool = False,
) -> List[CorpusEntry]:
    """Simple retrieval helper for later few-shot selection (not full RAG).

    - ``tags``: keep entries that share any tag (or all if ``require_all_tags``).
    - ``cadence`` / ``mode``: exact match when set.
    - ``max_spice``: keep entries whose ``quality.spice`` is None or ≤ max.
    """
    tag_set = {t.lower() for t in tags} if tags else None
    out: List[CorpusEntry] = []
    for e in entries:
        if cadence is not None and e.cadence != cadence:
            continue
        if mode is not None:
            entry_mode = e.mode or _mode_from_key(e.key)
            if entry_mode != mode:
                continue
        if max_spice is not None and e.quality is not None and e.quality.spice is not None:
            if e.quality.spice > max_spice:
                continue
        if tag_set is not None:
            entry_tags = {t.lower() for t in e.tags}
            if require_all_tags:
                if not tag_set.issubset(entry_tags):
                    continue
            elif not tag_set.intersection(entry_tags):
                continue
        out.append(e)
    return out


def _mode_from_key(key: str) -> Optional[str]:
    parts = key.strip().split()
    if len(parts) >= 2:
        m = parts[1].lower()
        if m in _SUPPORTED_MODES:
            return m
    return None


def _parse_entry(item: Any, *, index: int, source: str) -> CorpusEntry:
    loc = f"{source} entry[{index}]"
    if not isinstance(item, Mapping):
        raise CorpusError(f"{loc}: must be an object")

    missing = _REQUIRED_FIELDS - set(item.keys())
    if missing:
        raise CorpusError(f"{loc}: missing required fields: {sorted(missing)}")

    entry_id = item["id"]
    if not isinstance(entry_id, str) or not entry_id.strip():
        raise CorpusError(f"{loc}: 'id' must be a non-empty string")

    key = item["key"]
    if not isinstance(key, str) or not key.strip():
        raise CorpusError(f"{loc} ({entry_id}): 'key' must be a non-empty string")

    progression = item["progression"]
    if not isinstance(progression, list) or not progression:
        raise CorpusError(f"{loc} ({entry_id}): 'progression' must be a non-empty list")
    figures: list[str] = []
    for j, fig in enumerate(progression):
        if not isinstance(fig, str) or not fig.strip():
            raise CorpusError(
                f"{loc} ({entry_id}): progression[{j}] must be a non-empty string"
            )
        figures.append(fig.strip())

    cadence = item["cadence"]
    if not isinstance(cadence, str) or not cadence.strip():
        raise CorpusError(f"{loc} ({entry_id}): 'cadence' must be a non-empty string")
    cadence = cadence.strip()
    if cadence not in _SUPPORTED_CADENCES:
        raise CorpusError(
            f"{loc} ({entry_id}): unsupported cadence {cadence!r}; "
            f"expected one of {sorted(_SUPPORTED_CADENCES)}"
        )

    tags_raw = item["tags"]
    if not isinstance(tags_raw, list):
        raise CorpusError(f"{loc} ({entry_id}): 'tags' must be a list")
    tags: list[str] = []
    for j, tag in enumerate(tags_raw):
        if not isinstance(tag, str) or not tag.strip():
            raise CorpusError(f"{loc} ({entry_id}): tags[{j}] must be a non-empty string")
        tags.append(tag.strip())

    mode = item.get("mode")
    if mode is not None:
        if not isinstance(mode, str) or mode not in _SUPPORTED_MODES:
            raise CorpusError(
                f"{loc} ({entry_id}): 'mode' must be 'major' or 'minor' when present"
            )

    length = item.get("length")
    if length is not None:
        if not isinstance(length, int) or isinstance(length, bool):
            raise CorpusError(f"{loc} ({entry_id}): 'length' must be an int when present")
        if length != len(figures):
            raise CorpusError(
                f"{loc} ({entry_id}): 'length' ({length}) != len(progression) ({len(figures)})"
            )

    notes = item.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise CorpusError(f"{loc} ({entry_id}): 'notes' must be a string when present")

    source_obj = _parse_source(item.get("source"), loc=loc, entry_id=entry_id)
    quality = _parse_quality(item.get("quality"), loc=loc, entry_id=entry_id)
    region = _parse_region(item.get("region"), loc=loc, entry_id=entry_id)

    return CorpusEntry(
        id=entry_id.strip(),
        key=key.strip(),
        progression=tuple(figures),
        cadence=cadence,
        tags=tuple(tags),
        mode=mode,
        length=length if length is not None else len(figures),
        source=source_obj,
        region=region,
        quality=quality,
        notes=notes,
    )


def _parse_source(
    raw: Any, *, loc: str, entry_id: str
) -> Optional[CorpusSource]:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise CorpusError(f"{loc} ({entry_id}): 'source' must be an object")
    stype = raw.get("type", "")
    if not isinstance(stype, str) or not stype.strip():
        raise CorpusError(f"{loc} ({entry_id}): source.type must be a non-empty string")
    ref = raw.get("ref", "")
    license_ = raw.get("license", "")
    if not isinstance(ref, str) or not isinstance(license_, str):
        raise CorpusError(f"{loc} ({entry_id}): source.ref/license must be strings")
    return CorpusSource(type=stype.strip(), ref=ref, license=license_)


def _parse_quality(
    raw: Any, *, loc: str, entry_id: str
) -> Optional[CorpusQuality]:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise CorpusError(f"{loc} ({entry_id}): 'quality' must be an object")
    spice = raw.get("spice")
    if spice is not None:
        if not isinstance(spice, int) or isinstance(spice, bool) or not (0 <= spice <= 5):
            raise CorpusError(
                f"{loc} ({entry_id}): quality.spice must be an int 0–5 when present"
            )
    student_safe = raw.get("student_safe")
    if student_safe is not None and not isinstance(student_safe, bool):
        raise CorpusError(f"{loc} ({entry_id}): quality.student_safe must be a bool")
    realizer_ok = raw.get("realizer_ok")
    if realizer_ok is not None and not isinstance(realizer_ok, bool):
        raise CorpusError(f"{loc} ({entry_id}): quality.realizer_ok must be a bool")
    return CorpusQuality(
        spice=spice,
        student_safe=student_safe,
        realizer_ok=realizer_ok,
    )


def _parse_region(
    raw: Any, *, loc: str, entry_id: str
) -> Optional[tuple[Mapping[str, Any], ...]]:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise CorpusError(f"{loc} ({entry_id}): 'region' must be a list when present")
    regions: list[dict[str, Any]] = []
    for j, r in enumerate(raw):
        if not isinstance(r, Mapping):
            raise CorpusError(f"{loc} ({entry_id}): region[{j}] must be an object")
        regions.append(dict(r))
    return tuple(regions)
