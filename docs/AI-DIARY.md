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
- _(resolved in Entry 7 — none outstanding on direction.)_

## Entry 5 — Generator: soprano decision
User decided the **soprano is optional**. Free-soprano mode has the engine
choose all four voices; given-soprano mode voices A/T/B beneath the provided
line, but only after a **chord-membership compatibility check** — each soprano
note must be a legal tone of its Roman numeral's chord, else reject with a clear
per-beat message. Reuses the analyzer's chord-membership logic. Folded into
`chorale-generation.md`, `ROADMAP.md`, and `STATUS.md`.

## Entry 6 — Generation is two layers (functional grammar + editable RNs)
User clarified that "random" generation should be **governed by tonal harmony**,
not uniform chance — not every RN combo sounds good. Split generation into two
layers:
- **Layer 1 — progression generator:** a functional-harmony grammar (chords
  grouped by Tonic/Predominant/Dominant function; a weighted transition table
  encoding norms like `ii→V`, `V→I`/`V→vi`, cadential ⁶⁴→V, and forbidding
  retrogressions like `V→IV`; cadence-aware). Rule-based grammar is the default;
  LLM proposer is an optional later alternative. Progressions are an **editable
  list** — change or **lock** individual RNs and regenerate the rest around the
  locked slots (constrained generation).
- **Layer 2 — realizer:** the clean-room part-writing engine from Entry 4/5.
Planned endpoints `POST /progression` (Layer 1) and `POST /generate` (Layer 2);
chain them or go straight to `/generate` with a hand-written progression. This
also resolved the earlier rule-based-vs-hybrid-LLM open question (rule-based
default, LLM optional). Folded into the three planning docs.

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

## Entry 7 — Confirmed: multi-utility, both directions
User confirmed Harmonyx is a **multi-utility tool that does both** — analyze
(score → Roman numerals) and generate (Roman numerals → score). The two are
designed as inverses that round-trip and validate each other. This closes the
last open direction question; remaining decisions are implementation details
(e.g. one realization vs. several alternates). Updated STATUS and ROADMAP.

## Entry 8 — Rules as source of truth (agent-independent correctness)
User's principle: the part-writing rules must be **truths regardless of the
agent** — not left to a model's latent music knowledge. Wrote
`PARTWRITING-RULES.md` as the authoritative spec: hard invariants (ranges,
spacing, crossing/overlap, parallel & direct 5ths/8ves, LT & 7th resolution)
defined precisely with **golden fixtures** (voicing pairs + expected result),
plus soft preferences (doubling, voice-leading cost weights) and the functional
transition table with weights, RN-normalization rules for the round-trip eval,
and a music21 gotchas section. The fixtures ARE the spec: an implementation is
correct when `tests/test_partwriting.py` passes and realized progressions have
zero hard-invariant violations — so a lower-context (e.g. Sonnet-level) agent
can build the engine correctly against external truths rather than guessing.
Linked from IMPLEMENTATION-PLAN and STATUS.

## Entry 9 — Pre-wrote and locked the hard-invariant fixtures
Before handing off to a Sonnet-level agent, encoded the §0–§7 hard invariants
from `PARTWRITING-RULES.md` as runnable tests in `tests/test_partwriting.py`
(18 fixtures: ranges, spacing, crossing/overlap, parallel & direct 5ths/8ves,
LT & 7th resolution, doubled LT/7th). Each fixture is a concrete SATB voicing
pair with the expected `.rule` slug. The module `importorskip`s
`app.generation.voicing`/`rules`, so it **skips cleanly today (CI green:
13 passed, 1 skipped)** and activates the moment those modules exist. This locks
the target: the implementing agent builds the engine to satisfy fixtures it
cannot edit, so musical correctness is external to the model. Pinned the fixed
contract (Voicing shape, `rule_violations(prev, cur, ctx)` signature, ctx dict
schema, canonical slug set) in `PARTWRITING-RULES.md` and referenced it from
`IMPLEMENTATION-PLAN.md`. Handoff-ready for Sonnet.
