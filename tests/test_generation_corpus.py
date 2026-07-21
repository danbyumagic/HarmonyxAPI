"""Tests for app.generation.corpus (L1 — load + schema only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.generation.chords import roman_numeral
from app.generation.corpus import (
    CorpusError,
    CorpusEntry,
    default_corpus_path,
    filter_entries,
    load_corpus,
    parse_corpus_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = REPO_ROOT / "data" / "progression_corpus.json"


def test_default_corpus_path_points_at_repo_data():
    assert default_corpus_path() == CORPUS_PATH
    assert default_corpus_path().is_file()


def test_load_corpus_from_default_path():
    entries = load_corpus()
    assert 20 <= len(entries) <= 100
    assert all(isinstance(e, CorpusEntry) for e in entries)


def test_load_corpus_explicit_path():
    entries = load_corpus(CORPUS_PATH)
    assert len(entries) >= 20


def test_entry_ids_unique_and_required_fields():
    entries = load_corpus()
    ids = [e.id for e in entries]
    assert len(ids) == len(set(ids))
    for e in entries:
        assert e.id
        assert e.key
        assert e.progression
        assert e.cadence in {"PAC", "HC", "IAC", "DC", "PC", "other"}
        assert isinstance(e.tags, tuple)
        assert e.length == len(e.progression)


def test_corpus_has_major_and_minor_and_cadences():
    entries = load_corpus()
    modes = {e.mode or e.key.split()[-1].lower() for e in entries}
    cadences = {e.cadence for e in entries}
    assert "major" in modes
    assert "minor" in modes
    assert "PAC" in cadences
    assert "HC" in cadences


def test_corpus_has_spicy_tags():
    entries = load_corpus()
    all_tags = {t for e in entries for t in e.tags}
    assert "has_secondary_dominant" in all_tags
    assert "has_inversion" in all_tags
    assert "has_cad64" in all_tags


def test_all_figures_parseable_with_music21():
    """Corpus figures must be parseable RN strings (not full L2 theory)."""
    entries = load_corpus()
    for e in entries:
        for fig in e.progression:
            # Raises if music21 cannot parse the figure in this key.
            roman_numeral(fig, e.key)


def test_filter_by_cadence_and_tags():
    entries = load_corpus()
    pac = filter_entries(entries, cadence="PAC")
    assert pac and all(e.cadence == "PAC" for e in pac)
    spicy = filter_entries(entries, tags=["has_secondary_dominant"])
    assert spicy and all("has_secondary_dominant" in e.tags for e in spicy)
    mild = filter_entries(entries, max_spice=1)
    for e in mild:
        if e.quality and e.quality.spice is not None:
            assert e.quality.spice <= 1


def test_parse_minimal_entry():
    payload = {
        "version": 1,
        "entries": [
            {
                "id": "min-01",
                "key": "C major",
                "progression": ["I", "V", "I"],
                "cadence": "PAC",
                "tags": ["basic"],
            }
        ],
    }
    entries = parse_corpus_payload(payload)
    assert len(entries) == 1
    assert entries[0].id == "min-01"
    assert entries[0].length == 3
    assert entries[0].progression == ("I", "V", "I")


def test_reject_missing_required_field():
    with pytest.raises(CorpusError, match="missing required"):
        parse_corpus_payload(
            {
                "entries": [
                    {
                        "id": "bad",
                        "key": "C major",
                        "progression": ["I", "V", "I"],
                        "cadence": "PAC",
                        # tags missing
                    }
                ]
            }
        )


def test_reject_duplicate_ids():
    entry = {
        "id": "dup",
        "key": "C major",
        "progression": ["I", "V", "I"],
        "cadence": "PAC",
        "tags": ["x"],
    }
    with pytest.raises(CorpusError, match="duplicate"):
        parse_corpus_payload({"entries": [entry, dict(entry)]})


def test_reject_length_mismatch():
    with pytest.raises(CorpusError, match="length"):
        parse_corpus_payload(
            {
                "entries": [
                    {
                        "id": "len-bad",
                        "key": "C major",
                        "progression": ["I", "V", "I"],
                        "cadence": "PAC",
                        "tags": ["x"],
                        "length": 99,
                    }
                ]
            }
        )


def test_reject_empty_progression():
    with pytest.raises(CorpusError, match="progression"):
        parse_corpus_payload(
            {
                "entries": [
                    {
                        "id": "empty",
                        "key": "C major",
                        "progression": [],
                        "cadence": "PAC",
                        "tags": ["x"],
                    }
                ]
            }
        )


def test_reject_unknown_cadence():
    with pytest.raises(CorpusError, match="cadence"):
        parse_corpus_payload(
            {
                "entries": [
                    {
                        "id": "cad-bad",
                        "key": "C major",
                        "progression": ["I", "V", "I"],
                        "cadence": "NOT_A_CADENCE",
                        "tags": ["x"],
                    }
                ]
            }
        )


def test_reject_missing_file():
    with pytest.raises(CorpusError, match="not found"):
        load_corpus("/tmp/does-not-exist-harmonyx-corpus.json")


def test_reject_invalid_json(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(CorpusError, match="invalid JSON"):
        load_corpus(bad)


def test_as_dict_roundtrip_minimal():
    entries = parse_corpus_payload(
        {
            "entries": [
                {
                    "id": "rt-01",
                    "key": "A minor",
                    "mode": "minor",
                    "progression": ["i", "V", "i"],
                    "cadence": "PAC",
                    "tags": ["minor", "basic"],
                    "quality": {"spice": 0, "student_safe": True},
                }
            ]
        }
    )
    d = entries[0].as_dict()
    assert d["id"] == "rt-01"
    assert d["progression"] == ["i", "V", "i"]
    assert d["quality"]["spice"] == 0
    # Re-parse serialized form
    again = parse_corpus_payload({"entries": [d]})
    assert again[0].id == "rt-01"


def test_on_disk_json_is_object_with_entries():
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    assert "entries" in raw
    assert isinstance(raw["entries"], list)
    assert len(raw["entries"]) >= 20
