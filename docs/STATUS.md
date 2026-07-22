# Project status — Harmonyx API

Snapshot for handoff. Pairs with [`START-HERE.md`](START-HERE.md) (plain language),
[`AI-DIARY.md`](AI-DIARY.md), [`RICH-GRAMMAR-SPEC.md`](RICH-GRAMMAR-SPEC.md),
[`LLM-PROGRESSION-SPEC.md`](LLM-PROGRESSION-SPEC.md),
[`IMPLEMENTATION-PLAN.md`](IMPLEMENTATION-PLAN.md), [`PARTWRITING-RULES.md`](PARTWRITING-RULES.md),
[`chorale-generation.md`](chorale-generation.md), [`ROADMAP.md`](ROADMAP.md).

_Last updated: 2026-07-21 (Q3a–c richer grammar implemented)._

## One-liner

Two-way harmony tool. **Analyze:** MusicXML/MIDI → Roman numerals JSON.
**Generate:** RN progression → grand-staff SATB MusicXML + browser preview/play.
Deterministic core (music21 + clean-room part-writing). Optional LLM explainer
on analyze. **LLM progression path:** corpus + validator + fixer **implemented**
(L1–L3); LLM API client **not** built (L4+). **Richer rule grammar (Q3):**
Q3a–c **implemented** — inversions/Cad64, `spice` 0–3, `style` presets
(`student` / `hymnal` / `spicy`); see `RICH-GRAMMAR-SPEC.md` + PARTWRITING-RULES §9b.

## Where the code lives

- Repo: `danbyumagic/HarmonyxAPI`
- Working branch: `claude/harmonic-analysis-api-loc82f`
- PR: **#1** (may need status refresh vs older description)
- Default branch: `main`
- Note: some environments use a git worktree (e.g. under `/private/tmp/...`);
  confirm `git status` / remote ahead-count before push.

## What's built (working)

```
app/
  analyzer.py, explainer.py, models.py, main.py
  generation/
    chords.py      RN ↔ pitch-class helpers, normalize_rn, rn_agreement
    voicing.py     candidate_voicings (rejects non-chord-tone soprano)
    rules.py       rule_violations + transition_cost
    realize.py     DP realize; grand-staff score; playback_from_voicings
    grammar.py     weighted generate_progression (Q3 spice/style + applied)
    corpus.py      L1 progression corpus loader
    validate.py    L2 validate_progression (theory + engine gates)
    fix.py         L3 suggest_fixes (minimal-edit suggestions)
  static/index.html   Analyze + Generate tabs; OSMD; Play @ 75 BPM
data/
  progression_corpus.json   ~40 hand-written RN phrases (few-shot seed)
eval/
  run_eval.py                 key agreement (Bach set)
  run_generation_eval.py      RN round-trip + hard violations (M2)
  expected/keys.json
  expected/generation_fixtures.json
tests/   analyzer, partwriting (LOCKED), generation_*, generate/progression,
         test_generation_corpus, test_generation_validate, test_generation_fix
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

### LLM progression phases (`LLM-PROGRESSION-SPEC.md`)

| Phase | Status |
|-------|--------|
| L0 design | Done |
| L1 corpus + loader | **Done** |
| L2 validator | **Done** |
| L3 deterministic fixer | **Done** |
| L4 LLM client | Not started |
| L5 API `source: llm\|grammar` | Not started |
| L6 frontend AI propose | Not started |
| L7 optional LLM repair | Not started |

### Q3 richer grammar (`RICH-GRAMMAR-SPEC.md`)

| Chunk | Status |
|-------|--------|
| Q3a inversions + Cad64 | **Done** |
| Q3b secondary dominants + `spice` API | **Done** |
| Q3c style presets + polish | **Done** |
| Frontend spice UI | **Done** (Generate tab slider + pills) |

`style` → spice: `student`=0, `hymnal`=1, `spicy`=2. Style wins if both set.
Default omit → spice 0 (no free-walk secondary dominants). spice=3 is
integer-only (max color: also `V/vi` / `V/ii`).

## API surface

| Route | Method | Notes |
|-------|--------|--------|
| `/analyze` | POST | file upload; `duration_threshold`, `explain` |
| `/progression` | POST | `{key, length?, locked?, cadence?, seed?, spice?, style?}` → RN list (+ echoes spice/style) |
| `/generate` | POST | `{key, progression, time_signature?, soprano?}` → `{musicxml, playback}` |
| `/health` | GET | liveness |
| `/` | GET | frontend |
| `/docs` | GET | Swagger |

Library-only (not yet HTTP): `validate_progression`, `suggest_fixes`, `load_corpus`.

**`/generate` playback:** `{ tempo_bpm: 75, events: [{beat, midi, duration}, ...] }`
— block chords (4 notes per beat).

**Score layout:** braced grand staff — Treble: S (stem up) + A (stem down);
Bass: T (stem up) + B (stem down).

## How to run / verify

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
# music21 10.x needs Python ≥ 3.11
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

.venv/bin/python -m pytest tests/ -q          # expect ~150+ passed (after Q3)
.venv/bin/python -m eval.run_eval --min 0.6
.venv/bin/python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0
```

## Quality (honest)

- Key detection eval: **~65% (13/20)** Bach chorales (relative major/minor).
- Generation eval (curated fixtures): **100% primary RN round-trip, 0 hard violations**.
- Grammar output: idiomatic but **plain** (root-heavy, single key) until Q3.
- L2 theory gate: forbids house retrogressions; allows secondary dominants.
- L3 fixer: suggestions re-pass validator (theory-first by default).

## Known limitations

**Analyzer:** NCT noise; over-eager half cadences; no modulation tracking; key 65%.

**Generator:** grammar lacks rich inversions / secondary dominants / modulation
(Q3 not built); realizer is block-chord hymn style (no NCTs/suspensions);
playback is basic Web Audio.

**LLM path:** no API call, no `/progression` flag, no UI chips yet (L4–L6).

## Decisions (stable)

- OCR deferred.
- Clean-room part-writing engine (do not copy third-party partwriter code).
- Rule grammar is default Layer 1; LLM proposer optional and API-key-gated
  (L4+); never train from scratch — corpus few-shot + validator.
- Q3 enriches grammar **in parallel** with LLM path; default `spice=0`.
- `tests/test_partwriting.py` is **locked** — implement to match, never edit fixtures.
- Work in **small chunks**; ask before large continuous burns (`AGENTS.md`).

## Open queue

See [`START-HERE.md`](START-HERE.md). Headline leftovers:

1. **Q3 richer rule grammar** — implement from `RICH-GRAMMAR-SPEC.md` (Q3a first).
2. LLM L4+ — client / endpoint / UI.
3. M4 `POST /check`.
4. ~~Analyzer A1 / A2 / A7.~~ Done — NCT filtering, fermata phrase
   segmentation + PAC/IAC, RN-agreement eval (`eval/run_rn_eval.py`, 42%
   primary / 38% strict baseline, CI visibility-only).
5. Push/PR polish if L1–L3 commits are still local-only.

## Suggested next session shape

1. Fresh chat; agent reads START-HERE + AGENTS (+ RICH-GRAMMAR-SPEC if Q3).
2. **Stop and wait** for one narrow task (e.g. “implement Q3a only”).
3. Do not “continue the whole plan” or start Q3b in the same run as Q3a
   without explicit approval.
