# Harmony Studio

**Create, hear, and explore classical harmony in your browser.**

Harmony Studio opens directly into **Create**, where you can suggest and edit
Roman-numeral progressions, generate four-part SATB scores, preview notation,
listen, choose soprano alternatives, and export MusicXML. **Analyze** turns an
uploaded MusicXML or MIDI score into key, Roman-numeral, and cadence results.

The Harmony Studio API powers these workspaces and provides programmatic access
for developers. The musical core is deterministic (music21 + clean-room
part-writing); progression suggestions use a rule grammar. An optional
server-configured explainer can add a walkthrough to analysis without changing
its labels. Accounts, saved projects, and AI progression generation are not
implemented.

[![CI](https://github.com/danbyumagic/HarmonyxAPI/actions/workflows/ci.yml/badge.svg)](https://github.com/danbyumagic/HarmonyxAPI/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Quick start: open the studio

```bash
python -m venv .venv && source .venv/bin/activate   # Python ≥ 3.11
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [Harmony Studio](http://127.0.0.1:8000/) in your browser. No API key is
needed to create scores or run harmonic analysis.

### Create a four-part score

1. Choose a key, chord count, ending, and harmonic color, then **Suggest progression**.
2. Edit individual Roman numerals and lock chords you want to keep. Use
   **Suggest unlocked chords** to vary the rest; **Suggest progression** starts fresh.
3. Select **Generate score** to see the SATB notation (soprano, alto, tenor, bass).
4. Preview soprano alternatives and select a melody to regenerate the score.
   **More options** requests additional alternatives when available.
5. Use **Play / Stop** to hear the score and download MusicXML for a notation editor.

Roman numerals describe chords relative to the selected key. Advanced settings
include an optional seed for repeatable progression suggestions. Playback uses
basic synthesized audio; score export uses a braced grand staff.

### Analyze an existing score

Switch to **Analyze**, choose or drop a `.musicxml`, `.xml`, `.mxl`, `.mid`, or
`.midi` file, and run the analysis. Review the detected key, chord labels, and
cadences. The duration threshold filters short vertical slices, measured in
quarter notes. The optional plain-English walkthrough depends on server
configuration and availability; the analysis itself needs no explainer key.

### Developers

The studio's **Developers** link opens the [API showcase](http://127.0.0.1:8000/demo)
(`/demo`; `/portfolio` serves the same page). Open the
[interactive API reference](http://127.0.0.1:8000/docs) for schemas and request
examples. Both developer surfaces provide a path back to the studio.
The repository remains [danbyumagic/HarmonyxAPI](https://github.com/danbyumagic/HarmonyxAPI).

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok"}
```

## API reference

| Method | Path | Content type | Summary |
|--------|------|--------------|---------|
| `POST` | [`/analyze`](#post-analyze) | `multipart/form-data` | Score → key, Roman numerals, cadences |
| `POST` | [`/progression`](#post-progression) | `application/json` | Propose an idiomatic RN progression |
| `POST` | [`/generate`](#post-generate) | `application/json` | RN list → SATB MusicXML + playback JSON |
| `POST` | [`/generate/soprano-options`](#post-generatesoprano-options) | `application/json` | Distinct soprano lines for a progression |
| `GET` | `/health` | — | Liveness `{ "status": "ok" }` |
| `GET` | `/docs` | — | Swagger UI (OpenAPI) |
| `GET` | `/` | — | Harmony Studio browser workspace |
| `GET` | `/demo`, `/portfolio` | — | Harmony Studio API developer showcase |

---

## `POST /analyze`

Upload a score; get structured harmonic analysis.

**Query params**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `duration_threshold` | float | `0.5` | Drop vertical slices shorter than this (quarter notes) |
| `explain` | bool | `false` | If true and `ANTHROPIC_API_KEY` is set, add plain-English `explanation` |

**Upload:** field name `file` — `.musicxml`, `.xml`, `.mxl`, `.mid`, `.midi`

```bash
curl -s -F "file=@chorale.musicxml" \
  "http://127.0.0.1:8000/analyze" | jq .
```

**Response** (`AnalysisResponse`)

```json
{
  "key": "G major",
  "confidence": 0.91,
  "chords": [
    {
      "measure": 1,
      "beat": 1.0,
      "pitches": ["G3", "B3", "D4"],
      "roman": "I",
      "quality": "major",
      "inversion": 0,
      "fermata": false
    }
  ],
  "cadences": [{ "measure": 8, "type": "PAC" }],
  "explanation": null
}
```

Cadence `type` values: `PAC` · `IAC` · `plagal` · `half` · `deceptive` (and legacy `authentic` only if key is unavailable in internal helpers).

Optional explainer (labels unchanged):

```bash
export ANTHROPIC_API_KEY=sk-...
curl -s -F "file=@chorale.musicxml" \
  "http://127.0.0.1:8000/analyze?explain=true" | jq .explanation
```

---

## `POST /progression`

Rule-grammar proposal of Roman numerals (deterministic when `seed` is set).

**Body** (`ProgressionRequest`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `key` | string | required | e.g. `"C major"`, `"A minor"` |
| `length` | int | `8` | Chord count (1–64; PAC needs ≥ 2) |
| `locked` | object | `null` | Map of index → forced figure, e.g. `{"1":"IV"}` |
| `cadence` | string | `"PAC"` | `"PAC"` or `"HC"` |
| `seed` | int | `null` | Reproducible generation |
| `spice` | int | `0` | 0–3 harmonic color (secondary dominants at higher levels) |
| `style` | string | `null` | `"student"` · `"hymnal"` · `"spicy"` (overrides `spice` if both set) |

`style` → spice: `student`=0, `hymnal`=1, `spicy`=2. Default omit → spice 0.

```bash
curl -s -X POST "http://127.0.0.1:8000/progression" \
  -H "Content-Type: application/json" \
  -d '{"key":"C major","length":8,"cadence":"PAC","seed":42}' | jq .
```

**Response** (`ProgressionResponse`)

```json
{
  "key": "C major",
  "length": 8,
  "cadence": "PAC",
  "seed": 42,
  "spice": 0,
  "style": null,
  "progression": ["I", "IV", "ii6", "V", "I", "vi", "V7", "I"]
}
```

---

## `POST /generate`

Realize a Roman-numeral list as four-part SATB MusicXML (grand staff) plus playback events.

**Body** (`GenerateRequest`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `key` | string | required | e.g. `"C major"` |
| `progression` | string[] | required | RN figures in order |
| `time_signature` | string | `"4/4"` | Written meter |
| `soprano` | (int\|null)[] | `null` | Optional MIDI pitches per chord; length must match progression |

```bash
curl -s -X POST "http://127.0.0.1:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"key":"C major","progression":["I","IV","V","I"]}' \
  | jq '{key, progression, time_signature, musicxml: (.musicxml|length), playback}'
```

**Response** (`GenerateResponse`)

```json
{
  "key": "C major",
  "progression": ["I", "IV", "V", "I"],
  "time_signature": "4/4",
  "musicxml": "<?xml version='1.0' encoding='utf-8'?>...",
  "playback": {
    "tempo_bpm": 75,
    "events": [
      { "beat": 0, "midi": 72, "duration": 1.0 },
      { "beat": 0, "midi": 67, "duration": 1.0 },
      { "beat": 0, "midi": 64, "duration": 1.0 },
      { "beat": 0, "midi": 48, "duration": 1.0 }
    ]
  }
}
```

**Errors:** `422` if a fixed soprano pitch is not a chord tone (body lists offending indices).

Part-writing (ranges, spacing, doubling, parallels, LT/7th resolution) is enforced in the realizer; hard rules are locked by `tests/test_partwriting.py`.

---

## `POST /generate/soprano-options`

Return up to `count` distinct soprano MIDI lines for a progression (best first).

**Body** (`SopranoOptionsRequest`): `key`, `progression`, `count` (1–10, default 3).

```bash
curl -s -X POST "http://127.0.0.1:8000/generate/soprano-options" \
  -H "Content-Type: application/json" \
  -d '{"key":"C major","progression":["I","IV","V","I"],"count":3}' | jq .
```

**Response**

```json
{
  "options": [
    { "soprano": [72, 72, 71, 72], "pitches": ["C5", "C5", "B4", "C5"] },
    { "soprano": [64, 65, 62, 64], "pitches": ["E4", "F4", "D4", "E4"] }
  ]
}
```

Pass a chosen `soprano` array back into `POST /generate` to re-realize with that melody fixed.

---

## Pipeline (library behind the routes)

```
POST /analyze
  parse → key detect → NCT filter → chordify → RN labels → cadences

POST /progression
  weighted functional-harmony grammar (spice / style)

POST /generate
  candidate SATB voicings → DP/Viterbi → MusicXML + playback events
```

Library-only today (not HTTP): progression `validate` / `suggest_fixes` / corpus loader — prepared for an optional LLM proposer; not exposed on the API yet.

---

## Evaluation & CI

| Check | Result |
|-------|--------|
| Key detection (20 Bach chorales) | **90%** (CI gate ≥ 85%) |
| Generation round-trip (fixtures) | **100%** primary RN |
| Hard part-writing violations (fixtures) | **0** |
| RN agreement vs labelled corpus | **~42%** primary · **~38%** strict *(CI visibility only)* |

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
python -m eval.run_eval --min 0.85
python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0
```

---

## Deploy

```bash
docker build -t harmony-studio .
docker run -p 8000:8000 harmony-studio
# Health: GET /health   (Fly/Railway inject $PORT; fly.toml + railway.json included)
```

---

## Layout

```
app/
  main.py              FastAPI routes
  models.py            Pydantic request/response schemas (drive /docs)
  analyzer.py          score → analysis
  explainer.py         optional LLM walkthrough (ANTHROPIC_API_KEY)
  generation/          grammar, voicing, rules, DP realizer
  static/index.html    Harmony Studio Create / Analyze workspaces
  static/portfolio.html  secondary developer showcase (/demo, /portfolio)
eval/                  regression harnesses
tests/                 unit + endpoint + locked part-writing fixtures
```

---

## Scope (v1)

- Single major/minor key; four-part chorale texture; block-chord hymn realization  
- No first-class modulation tracking; no `POST /check` (score → rule violations) yet  
- Playback payload is simple Web Audio events, not SoundFonts  

---

## License

[MIT](LICENSE)
