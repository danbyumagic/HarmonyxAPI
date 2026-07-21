# AI diary — Harmonyx API

A chronological log of how this project got built, with the reasoning and the
gotchas, so another AI assistant (e.g. Grok) can pick up with full context.
Pairs with [`STATUS.md`](STATUS.md) (current-state snapshot).

Written by Claude Code across one working session on 2026-07-21. Newest entries
at the bottom.

---

## Entry 1 — Initial build (v1)
Started from an almost-empty repo (stub README only) and a project brief for a
"Harmonic Analysis API": score in → Roman-numeral analysis out.

Built, in order:
1. **`app/analyzer.py`** — the deterministic core. Pipeline:
   `converter.parse` → `analyze('key')` → `chordify()` →
   `roman.romanNumeralFromChord` per slice → **cleanup pass** → cadence
   detection. The cleanup pass is the actual craft: drop slices shorter than a
   duration threshold (passing tones) and merge repeated adjacent chords (same
   Roman + same pitch-class set), accumulating duration. Cadences come from
   adjacent Roman-numeral pairs (authentic/plagal/half/deceptive) via a
   `_degree()` helper that strips figures/accidentals to the bare scale degree.
2. **`app/models.py`** — Pydantic response models (also power Swagger `/docs`).
3. **`app/explainer.py`** — optional LLM walkthrough. Chose the **explainer**
   (narrate the deterministic analysis) over the **disambiguator** as the
   first, lower-risk AI angle. Gated on `ANTHROPIC_API_KEY`; returns `None`
   when absent so the core has zero LLM dependency. Uses `claude-opus-4-8` with
   adaptive thinking. (Consulted the claude-api skill for current model IDs and
   the adaptive-thinking API shape.)
4. **`app/main.py`** — FastAPI: `POST /analyze` (file + `duration_threshold` +
   `explain`), `GET /health`, static frontend at `/`, Swagger at `/docs`.
5. **`app/static/index.html`** — first-pass drop-zone frontend.
6. **Eval harness** (`eval/run_eval.py` + `eval/expected/keys.json`),
   **tests**, **Docker/Railway/Fly**, **CI workflow**, **README**.

### Gotchas hit and fixed
- **`analyze_score` re-parsed already-parsed Streams.** The eval passes music21
  corpus `Score` objects; `converter.parse(Score)` blew up. Fix: `_parse()`
  short-circuits when given a `stream.Stream`.
- **`_degree("bVII")` returned `""`.** It broke on the leading accidental. Fix:
  skip leading accidentals (`b # - + ♭ ♯`) before reading numerals. Caught by a
  test.

### Eval ground truth (transparent, reproducible)
Deriving key from the final chord alone mislabels Picardy-third endings (minor
chorales ending on a major tonic chord). Fixed by deriving **mode from the key
signature** and **tonic from the final chord root**. That gives sensible labels
(bwv66.6 = F♯ minor, etc.). Result: **65% (13/20)** key-detection agreement.
The misses are mostly relative major/minor confusion — an honest number, and
exactly the kind of ambiguity a single eval metric surfaces.

### State at end of Entry 1
13 tests passing, eval green, all routes serve. Committed and pushed to
`claude/harmonic-analysis-api-loc82f`; opened draft **PR #1**; CI passed.

---

## Entry 2 — Analyzed real scores
- **BWV 140/7 "Wachet auf"** (from the music21 corpus): detected **E♭ major**
  (correct). The default half-beat resolution returned 93 sonorities with lots
  of passing-tone noise and 40 over-fired cadences; the quarter-note reduction
  (`duration_threshold=1.0`) gave a clean I–ii–V–I skeleton with the real
  phrase cadences at m4/m8/m17. This concretely exposed the tool's three
  limits: NCT noise, over-eager cadences, no modulation tracking.
- **"Nearer, My God, to Thee"** (user-uploaded MusicXML, encoded by "Maestria,"
  with some garbled lyric tokens that didn't affect harmony): detected
  **F major** (correct). Clean AABA reading; three passing/suspension artifacts
  (`v7`, `i5`) noted honestly.

Takeaway recorded for the roadmap: the coarse reduction is genuinely useful;
the fine-grained chromatic labeling is approximate.

---

## Entry 3 — Frontend redesign
Rewrote `app/static/index.html` into a polished page: refined drop zone, a
key + confidence hero with a gradient bar, a colour-coded cadence timeline,
chords grouped into **per-measure cards** with quality-coloured Roman numerals
(major = terracotta, minor = purple, dim = green) and pitch pills, a light/dark
theme toggle, a loading spinner, and a **resolution toggle**
(Detailed/Standard/Reduced) that maps to `duration_threshold` and re-analyzes
the current file. Verified end-to-end with a live uvicorn server +
Playwright screenshots (pointed at the pre-installed Chromium) in both themes,
using the user's hymn as the live example. Tests still green.

---

## Entry 4 — Roadmap & direction decisions (discussion, then docs)
Discussed future work; captured in `ROADMAP.md` and `chorale-generation.md`.
Decisions reached with the user:
- **OCR deferred** — not near-term.
- **Chorale generation** is the next big direction: `key + RN progression →
  part-writing engine → SATB → MusicXML four-part hymn`. It's the inverse of
  the analyzer, so the two round-trip and validate each other (generate →
  analyze → check the RNs come back).
- **partwriter.com reuse question resolved:** we will **not** copy its code.
  Part-writing rules are standard music theory (not IP), so we build our own
  **clean-room Python engine** from first principles. This removed the earlier
  license and port-vs-Node-sidecar questions. Plan: candidate voicings per
  chord + DP/search minimizing voice-leading cost + rule penalties, building on
  music21's `voiceLeading` module for parallel/hidden-interval detection.

Also identified but not yet built: the **LLM disambiguator** (feed ambiguous
slices to the model, show rule-based vs. model side by side) as the higher-value
AI angle once NCT filtering and modulation detection land.

### Still open for a human
- "Output choral Roman numerals" = realize / analyze / round-trip both?
- Generator: soprano given or free?
- Generation: rule-based only vs. hybrid LLM + realizer.

---

## Notes for the next assistant
- The deterministic analyzer and the eval harness are the stable foundation;
  don't regress the 13 tests or the eval gate (`python -m eval.run_eval`).
- Biggest quality win available now: **NCT filtering (A1)** +
  **fermata-based phrase/cadence segmentation (A2)** — see `ROADMAP.md`.
- The generator (B2) should emit MusicXML via music21 and round-trip cleanly
  back through `/analyze` — use that round-trip as its correctness eval.
- Keep the core service lean and deterministic; anything heavy or stylistic
  (LLM layers) stays optional/gated like the explainer already is.
