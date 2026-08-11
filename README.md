# Harmonyx

**Two-way harmony for the browser and the API.**

Upload a chorale → get Roman numerals.  
Propose a progression → get a four-part SATB MusicXML you can preview, play, and download.

Deterministic core (music21 + a clean-room part-writing engine). Optional LLM walkthrough on analyze. No model required for the main loop.

[![CI](https://github.com/danbyumagic/HarmonyxAPI/actions/workflows/ci.yml/badge.svg)](https://github.com/danbyumagic/HarmonyxAPI/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What you get

| Analyze | Generate |
|--------|----------|
| MusicXML / MIDI in | Roman numerals in |
| Key, RNs, cadences out | Grand-staff SATB MusicXML out |
| Drop-zone UI | Propose · edit · lock · realize · play |
| Optional plain-English explainer | Spice / style for richer grammar |
| | Soprano-line alternatives |

**Live UI** at `/` · **Swagger** at `/docs` · **health** at `/health`

---

## Quick start

```bash
# Python ≥ 3.11 (music21 10.x)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# → http://127.0.0.1:8000
```

```bash
# Analyze a score
curl -s -F "file=@chorale.musicxml" "http://127.0.0.1:8000/analyze" | jq .

# Propose a progression (student-safe by default)
curl -s -X POST "http://127.0.0.1:8000/progression" \
  -H "Content-Type: application/json" \
  -d '{"key":"C major","length":8,"cadence":"PAC"}' | jq .

# Realize it as SATB MusicXML + playback events
curl -s -X POST "http://127.0.0.1:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"key":"C major","progression":["I","IV","V","I"]}' | jq '{keys: keys, playback: .playback.tempo_bpm}'
```

Optional LLM walkthrough on analyze (never rewrites RNs or key):

```bash
export ANTHROPIC_API_KEY=sk-...
curl -s -F "file=@chorale.musicxml" "http://127.0.0.1:8000/analyze?explain=true" | jq .explanation
```

---

## API

| Method | Path | What it does |
|--------|------|----------------|
| `POST` | `/analyze` | Score file → key, chords (RN), cadences; `?explain=true` for LLM text |
| `POST` | `/progression` | `{key, length?, locked?, cadence?, seed?, spice?, style?}` → RN list |
| `POST` | `/generate` | `{key, progression, time_signature?, soprano?}` → MusicXML + playback |
| `POST` | `/generate/soprano-options` | Up to N distinct soprano lines for a progression |
| `GET`  | `/health` | Liveness |
| `GET`  | `/` | Frontend |
| `GET`  | `/docs` | OpenAPI / Swagger |

**Accepted uploads:** `.musicxml` · `.xml` · `.mxl` · `.mid` · `.midi`

**Spice / style** (propose only): default `spice=0` (homework-safe).  
`style`: `student` → 0 · `hymnal` → 1 · `spicy` → 2 (style wins if both set).  
Integer `spice=3` is max color (extra applied dominants).

---

## How generation works

```
RN progression
      │
      ▼
 candidate SATB voicings   (ranges, spacing, doubling)
      │
      ▼
 DP / Viterbi search       (smoothness + hard rule costs)
      │
      ▼
 grand-staff MusicXML      + block-chord playback events
```

Part-writing constraints (ranges, spacing, doubling, parallels, leading-tone and seventh resolution) are enforced in the realizer. The locked fixtures in `tests/test_partwriting.py` define the hard contract.

Progression propose uses a weighted functional-harmony grammar (`app/generation/grammar.py`). A corpus + validator + fixer stack is prepared for an optional LLM proposer; that path is **not** wired to the API yet.

---

## Evaluation

| Check | Result |
|-------|--------|
| Key detection (20 Bach chorales) | **~65%** (CI gate ≥ 60%) |
| Generation round-trip (fixtures) | **100%** primary RN agreement |
| Hard part-writing violations (fixtures) | **0** |
| RN agreement vs labelled corpus | **~42%** primary · **~38%** strict *(reported in CI, not a gate)* |

```bash
pytest tests/ -q
python -m eval.run_eval --min 0.6
python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0
```

---

## Project layout

```
app/
  analyzer.py          score → RN / key / cadences
  explainer.py         optional LLM walkthrough (API-key gated)
  models.py            Pydantic request/response models
  main.py              FastAPI routes
  generation/          realizer, grammar, rules, corpus, validate, fix
  static/index.html    Analyze + Generate UI (OSMD + play)
data/progression_corpus.json
eval/                  key, generation, RN-agreement harnesses
tests/                 unit + endpoint + locked part-writing fixtures
```

---

## Deploy

Container-first:

```bash
docker build -t harmonyx . && docker run -p 8000:8000 harmonyx

# Fly.io / Railway — fly.toml and railway.json are ready
# Health check: GET /health   (platforms inject $PORT)
```

---

## Scope

**In scope (v1):** four-part chorale texture, single major/minor key, block-chord hymn style, browser playback (Web Audio, not SoundFonts).

**Out of scope for now:** modulation tracking as a first-class feature, full contrapuntal NCTs/suspensions in the realizer, score → part-writing checker HTTP endpoint, LLM-proposed progressions in the UI.

Key detection still confuses some relative major/minor cases. Generation quality is measured on curated fixtures and gated in CI.

---

## License

[MIT](LICENSE)
