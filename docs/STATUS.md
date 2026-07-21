# Project status — Harmonyx API

Snapshot for handoff (to Grok or any collaborator). Pairs with
[`AI-DIARY.md`](AI-DIARY.md) (chronological log), [`ROADMAP.md`](ROADMAP.md),
[`chorale-generation.md`](chorale-generation.md), the step-by-step
[`IMPLEMENTATION-PLAN.md`](IMPLEMENTATION-PLAN.md) (modules, signatures, tests,
milestones), and [`PARTWRITING-RULES.md`](PARTWRITING-RULES.md) — the
**authoritative rule spec** (hard invariants as fixtures, soft preferences as
documented weights) that makes the engine correct independent of which agent
builds it.

_Last updated: 2026-07-21._

## One-liner
A two-way, multi-utility harmony tool. **Analyze:** send a MusicXML/MIDI score
to `POST /analyze`, get a chord-by-chord Roman-numeral analysis (key, chords,
cadences) as JSON. **Generate:** turn a Roman-numeral progression into a
four-part SATB hymn as MusicXML (planned — see `chorale-generation.md`). The
two directions are inverses that round-trip and validate each other.
Deterministic core (music21) + an optional LLM "explainer."

## Where the code lives
- Repo: `danbyumagic/HarmonyxAPI`
- Working branch: `claude/harmonic-analysis-api-loc82f`
- PR: **#1** (draft, open, CI green) — https://github.com/danbyumagic/HarmonyxAPI/pull/1
- Default branch: `main`

## What's built (all working)
```
app/
  analyzer.py   music21 core + the cleanup pass (parse → key → chordify →
                romanNumeralFromChord → drop short slices + merge repeats →
                cadence detection). Accepts a path/string OR a parsed
                music21 Stream.
  explainer.py  optional LLM walkthrough. Gated on ANTHROPIC_API_KEY; returns
                None when absent so the core stays deterministic.
                Model: claude-opus-4-8, adaptive thinking.
  models.py     Pydantic response models (drive Swagger /docs).
  main.py       FastAPI app.
  static/       redesigned drop-zone frontend (key hero, cadence timeline,
                per-measure chord cards, light/dark, resolution toggle).
eval/
  run_eval.py       key-detection agreement harness (also a CI gate: --min)
  expected/keys.json ground truth for 20 Bach chorales
tests/test_analyzer.py   13 tests (cleanup, cadences, degree parsing,
                         full pipeline, endpoint)
tests/test_partwriting.py  18 PRE-WRITTEN, LOCKED fixtures for the SATB engine's
                         hard invariants (skips until app/generation/ exists)
docs/             ROADMAP.md, chorale-generation.md, STATUS.md, AI-DIARY.md
Dockerfile, railway.json, fly.toml   container-first deploy
.github/workflows/ci.yml             runs pytest + the eval gate
requirements.txt, requirements-dev.txt, .env.example, .gitignore
README.md
```

## API surface
| Route | Method | Notes |
|---|---|---|
| `/analyze` | POST | `file` (upload) + query `duration_threshold` (default 0.5), `explain` (default false). Returns `{key, confidence, chords[], cadences[], explanation?}`. |
| `/health` | GET | `{status: "ok"}` (deploy probe). |
| `/` | GET | Frontend. |
| `/docs` | GET | Swagger UI. |

Accepted uploads: `.musicxml`, `.xml`, `.mxl`, `.mid`, `.midi`.

## How to run / verify
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://localhost:8000  (/ and /docs)

pip install -r requirements-dev.txt
python -m pytest tests/            # 13 passed
python -m eval.run_eval            # Agreement: 13/20 = 65%
```

## Current quality (honest)
- **Key detection eval: 65% (13/20)** on the Bach chorale set. Most misses are
  relative major/minor confusion in music21's global key analysis.
- **Analyzed by hand this session:** BWV 140/7 "Wachet auf" → E♭ major ✓;
  "Nearer, My God, to Thee" (user upload) → F major ✓.

## Known limitations (these are the next work items)
1. **Non-chord-tone noise** at fine resolution — passing tones/suspensions get
   verticalized into fake chords (`V42`, `quartal trichord`, `i5`,
   `v7 "incomplete dominant-seventh"`). The duration-threshold cleanup helps but
   doesn't do true NCT analysis.
2. **Over-eager cadence detection** — fires "half" on every →V, mid-phrase
   included. No phrase segmentation yet (fermatas would give it for free).
3. **No modulation/tonicization** — everything forced into one global key;
   tonicizations show up as chromatic chords (`II` = V/V, etc.).
4. **Key detection** — relative major/minor confusion (the 65%).

## Decisions made
- **OCR / optical music recognition: deferred.** Not near-term.
- **Chorale generation direction confirmed:** `key + RN progression →
  part-writing engine → SATB → MusicXML four-part hymn`, the clean inverse of
  the analyzer (they round-trip and validate each other).
- **Build our own part-writing engine (clean-room).** The rules are standard
  music theory, not partwriter.com's IP — reimplement in Python from first
  principles; do NOT copy their code. No license gate, no Node sidecar.
- **LLM explainer** shipped (low-risk AI angle). The **LLM disambiguator** (the
  more interesting angle) is planned but not built.

## Decisions on the generator
- **Two layers.** (1) A **progression generator** driven by a
  **functional-harmony grammar** (weighted chord-transition table, cadence-aware)
  — idiomatic RNs, not random. (2) The **realizer** (clean-room part-writing
  engine) turns the RN progression into SATB → MusicXML.
- **Progressions are editable.** The user can change or **lock** individual
  Roman numerals and regenerate the rest around the locked slots, then
  re-realize.
- **Soprano is optional.** No soprano → the engine voices all four parts
  freely. Soprano provided → it voices alto/tenor/bass beneath it, after a
  **compatibility check**: each soprano note must be a chord tone of its Roman
  numeral's chord; incompatible notes are rejected with a clear per-beat message
  (422 with the offending beat).
- **Rule-based grammar is the default;** an LLM progression proposer is an
  optional later alternative.
- Planned endpoints: `POST /progression` (Layer 1) and `POST /generate`
  (Layer 2). See [`chorale-generation.md`](chorale-generation.md).

## Open questions (need a human decision)
_None outstanding on direction._ Resolved: Harmonyx is a **multi-utility tool
that does both** — analyze (score → RNs) and generate (RNs → score) — designed
as inverses that round-trip. Remaining decisions are implementation details
covered in `chorale-generation.md` (e.g. one realization vs. alternates).

## Suggested next steps
See [`IMPLEMENTATION-PLAN.md`](IMPLEMENTATION-PLAN.md) for the concrete,
milestone-by-milestone build plan. Summary order:
- **M0–M1:** realizer core (`app/generation/`) + `POST /generate` — build first.
- **M2:** round-trip + rule-violation eval (measurable quality).
- **M3:** functional-harmony progression grammar + `POST /progression`.
- **M4:** part-writing checker (`POST /check`).
- **M5:** frontend generation panel.
- **Parallel analyzer track:** NCT filtering (A1), fermata cadences (A2),
  RN-agreement eval (A7).
