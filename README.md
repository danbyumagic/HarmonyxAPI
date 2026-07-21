# Harmonyx API

**Send it a score, get back a chord-by-chord Roman numeral analysis as structured JSON.**

`POST /analyze` with a MusicXML or MIDI file →

```json
{
  "key": "G major",
  "confidence": 0.91,
  "chords": [
    {"measure": 1, "beat": 1, "pitches": ["G3", "B3", "D4"],
     "roman": "I", "quality": "major", "inversion": 0},
    {"measure": 1, "beat": 3, "pitches": ["C4", "E4", "G4"],
     "roman": "IV", "quality": "major", "inversion": 0}
  ],
  "cadences": [{"measure": 8, "type": "authentic"}]
}
```

Interactive Swagger UI at `/docs`. A drop-zone frontend at `/`.

---

## How it works

The pipeline is deliberately small — [`app/analyzer.py`](app/analyzer.py) is the core:

1. **Parse** the uploaded score (`music21.converter.parse`).
2. **Detect the key** (`score.analyze('key')`, Krumhansl-Schmuckler).
3. **Chordify** — collapse the multi-voice texture into vertical sonorities.
4. **Label** each sonority with a Roman numeral (`roman.romanNumeralFromChord`).
5. **Clean up** — this is where the craft is. `chordify()` produces a lot of
   junk: passing tones and suspensions momentarily spell "chords" no analyst
   would label. The cleanup pass:
   - drops slices shorter than a duration threshold (passing motion), and
   - merges repeated adjacent chords (a harmony held or re-struck across beats).
6. **Detect cadences** from adjacent Roman-numeral pairs (authentic, plagal,
   half, deceptive).

## The AI part

`music21` alone is deterministic, rule-based analysis. The optional **LLM
explainer** ([`app/explainer.py`](app/explainer.py)) keeps that analysis
authoritative and adds a plain-English walkthrough of the progression on top —
the lower-risk of the two AI angles in the design. It never changes a Roman
numeral or a key.

Pass `?explain=true` and set `ANTHROPIC_API_KEY`. Without a key the field is
simply omitted; the core `/analyze` endpoint stays fully deterministic and has
no LLM dependency. The explainer uses `claude-opus-4-8` with adaptive thinking.

## The eval number

> A single number turns a demo into evidence.

[`eval/run_eval.py`](eval/run_eval.py) runs the analyzer over 20 Bach chorales
from the `music21` corpus and reports the percentage whose detected key matches
the ground truth in [`eval/expected/keys.json`](eval/expected/keys.json).

```
$ python -m eval.run_eval
...
Agreement: 13/20 = 65%
```

**Current key-detection agreement: 65% (13/20).** The ground truth is derived
transparently — each chorale's key signature gives the mode, its final chord
root gives the tonic — so Picardy-third endings are labelled by their true
minor key rather than the major final chord. Most misses are relative
major/minor confusions in `music21`'s global key analysis (e.g. F♯ major vs.
its relative B minor), which is exactly the kind of ambiguity a single honest
number surfaces. It doubles as a CI regression gate: `python -m eval.run_eval
--min 0.6` exits non-zero if agreement drops below 60%.

## Scope discipline (v1)

V1 handles **four-part chorale texture in a single major/minor key, no
modulation.** Modulation detection is the thing most likely to stall this
project, so it's deliberately out of scope. Chromatic chords are labelled as
best `music21` can within the detected key.

---

## Running locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# open http://localhost:8000  (frontend)  or  /docs  (Swagger)
```

Analyze a file:

```bash
curl -F "file=@chorale.musicxml" "http://localhost:8000/analyze"
# with the LLM walkthrough:
curl -F "file=@chorale.musicxml" "http://localhost:8000/analyze?explain=true"
```

### Query parameters

| Param                | Default | Meaning                                                        |
| -------------------- | ------- | -------------------------------------------------------------- |
| `duration_threshold` | `0.5`   | Minimum slice length (quarter notes) to keep; below = passing. |
| `explain`            | `false` | Add an LLM walkthrough (needs `ANTHROPIC_API_KEY`).            |

Accepted uploads: `.musicxml`, `.xml`, `.mxl`, `.mid`, `.midi`.

## Tests & eval

```bash
pip install -r requirements-dev.txt
python -m pytest tests/      # unit + endpoint tests
python -m eval.run_eval      # key-detection agreement
```

## Deploy

Container-first, so it drops onto Railway or Fly.io with a live URL:

```bash
# Docker
docker build -t harmonyx . && docker run -p 8000:8000 harmonyx

# Fly.io
fly launch --no-deploy && fly deploy

# Railway: point a new service at this repo — railway.json handles the rest.
```

Both platforms inject `$PORT`; the health check is `GET /health`.

## Project layout

```
app/
  analyzer.py   music21 core + the cleanup pass (the craft)
  explainer.py  optional LLM walkthrough (gated on ANTHROPIC_API_KEY)
  models.py     Pydantic response models (drive /docs)
  main.py       FastAPI app: /analyze, /health, static frontend
  static/       drop-zone frontend + results table
eval/
  run_eval.py   key-detection agreement harness
  expected/     ground-truth keys
tests/          unit + endpoint tests
```
