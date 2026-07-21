# Project status — Harmonyx API

Snapshot for handoff. Pairs with [`START-HERE.md`](START-HERE.md) (plain language),
[`AI-DIARY.md`](AI-DIARY.md), [`LLM-PROGRESSION-SPEC.md`](LLM-PROGRESSION-SPEC.md),
[`IMPLEMENTATION-PLAN.md`](IMPLEMENTATION-PLAN.md), [`PARTWRITING-RULES.md`](PARTWRITING-RULES.md),
[`chorale-generation.md`](chorale-generation.md), [`ROADMAP.md`](ROADMAP.md).

_Last updated: 2026-07-21 (handoff after grand staff + playback)._

## One-liner

Two-way harmony tool. **Analyze:** MusicXML/MIDI → Roman numerals JSON.
**Generate:** RN progression → grand-staff SATB MusicXML + browser preview/play.
Deterministic core (music21 + clean-room part-writing). Optional LLM explainer
on analyze; **optional LLM progression proposer is designed, not built**
(see `LLM-PROGRESSION-SPEC.md`).

## Where the code lives

- Repo: `danbyumagic/HarmonyxAPI`
- Working branch: `claude/harmonic-analysis-api-loc82f`
- PR: **#1** (may need status refresh vs older description)
- Default branch: `main`

## What's built (working)

```
app/
  analyzer.py, explainer.py, models.py, main.py
  generation/
    chords.py      RN ↔ pitch-class helpers, normalize_rn, rn_agreement
    voicing.py     candidate_voicings (rejects non-chord-tone soprano)
    rules.py       rule_violations + transition_cost
    realize.py     DP realize; grand-staff score; playback_from_voicings
    grammar.py     weighted functional-harmony generate_progression
  static/index.html   Analyze + Generate tabs; OSMD; Play @ 75 BPM
eval/
  run_eval.py                 key agreement (Bach set)
  run_generation_eval.py      RN round-trip + hard violations (M2)
  expected/keys.json
  expected/generation_fixtures.json
tests/   analyzer, partwriting (LOCKED), generation_*, generate/progression endpoints
```

### Milestone map (IMPLEMENTATION-PLAN)

| Milestone | Status |
|-----------|--------|
| M0 scaffolding | Done |
| M1 realizer + `POST /generate` | Done |
| M2 generation eval + CI | Done |
| M3 grammar + `POST /progression` | Done |
| M4 `POST /check` | **Not done** |
| M5 frontend generate panel | Done (plus OSMD + play beyond original M5) |

## API surface

| Route | Method | Notes |
|-------|--------|--------|
| `/analyze` | POST | file upload; `duration_threshold`, `explain` |
| `/progression` | POST | `{key, length?, locked?, cadence?, seed?}` → RN list |
| `/generate` | POST | `{key, progression, time_signature?, soprano?}` → `{musicxml, playback}` |
| `/health` | GET | liveness |
| `/` | GET | frontend |
| `/docs` | GET | Swagger |

**`/generate` playback:** `{ tempo_bpm: 75, events: [{beat, midi, duration}, ...] }`
— block chords (4 notes per beat).

**Score layout:** braced grand staff — Treble: S (stem up) + A (stem down);
Bass: T (stem up) + B (stem down).

## How to run / verify

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
# music21 10.x needs Python ≥ 3.11
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

.venv/bin/python -m pytest tests/ -q          # expect 83 passed (as of handoff)
.venv/bin/python -m eval.run_eval --min 0.6
.venv/bin/python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0
```

## Quality (honest)

- Key detection eval: **~65% (13/20)** Bach chorales (relative major/minor).
- Generation eval (curated fixtures): **100% primary RN round-trip, 0 hard violations**.
- Grammar output: idiomatic but **plain** (root-heavy, single key).

## Known limitations

**Analyzer:** NCT noise; over-eager half cadences; no modulation tracking; key 65%.

**Generator:** grammar lacks rich inversions / secondary dominants / modulation;
realizer is block-chord hymn style (no NCTs/suspensions); playback is basic Web Audio.

## Decisions (stable)

- OCR deferred.
- Clean-room part-writing engine (do not copy third-party partwriter code).
- Rule grammar is default Layer 1; **LLM proposer is optional**, API-key-gated,
  never trains from scratch — corpus few-shot + validator (spec written).
- `tests/test_partwriting.py` is **locked** — implement to match, never edit fixtures.
- Work in **small chunks**; ask before large continuous burns (`AGENTS.md`).

## Open queue

See [`START-HERE.md`](START-HERE.md) open queue. Headline leftovers:

1. LLM progression system (`LLM-PROGRESSION-SPEC.md`) — design only.
2. M4 `POST /check`.
3. Grammar enrichment / style presets (no LLM).
4. Analyzer A1 / A2 / A7.

## Suggested next session shape

1. Fresh chat; agent reads START-HERE + AGENTS (+ LLM spec if relevant).
2. **Stop and wait** for one narrow task from the human.
3. Do not “continue the whole plan.”
