# Research note: AccoMontage2 + POP909

**Date:** 2026-07-21
**Repos:**
- https://github.com/billyblu2000/AccoMontage2 (code, package name `chorderator`)
- https://github.com/zhaojw1998/AccoMontage (parent research project, texture engine)
- https://github.com/music-x-lab/POP909-Dataset (data)
**Authors:** Li Yi, Haochen Hu, Jingwei Zhao, Gus Xia (NYU Shanghai Music-X-Lab);
POP909 by Ziyu Wang, Ke Chen, Junyan Jiang, et al.
**Status:** Tier B peer #7 (arrangement track) — only relevant if arrangement
becomes a scoped Harmonyx milestone. **Not** classical/SATB; this is a **pop
melody → chords + full piano accompaniment** system.
**Source:** READMEs (AccoMontage2, POP909-Dataset), full repo file tree via
`gh api .../git/trees`, `chorderator/core.py`, `chorderator/utils/models/DP.py`
(read in full — the harmonization DP), directory structure of
`chorderator/utils/models/accomontage/` (texture engine, not read line-by-line —
it's the original zhaojw1998 AccoMontage research code, PyTorch + PianoTree VAE).
**Meta:** AccoMontage2 ~166★, MIT, **last real push 2023-05-03** (despite
"updated" timestamp showing 2026 star/watch activity — the code itself is
stale, correcting the landscape doc's implied recency). POP909-Dataset ~395★,
MIT, **last real push 2020-08-28**. ISMIR 2022 paper (AccoMontage2) /
ISMIR 2020 paper (POP909).

---

## 1. What it is

A **two-stage arrangement pipeline**, packaged as a Python library
(`chorderator`) plus an optional Flask+React GUI:

```
melody MIDI + meta (tonic/mode) + phrase segmentation string (e.g. "A8B8A8B8")
        │
        ▼
 [1] Harmonization (DP.py) ── retrieval + dynamic programming over a
        │                     5k+ chord-progression template library
        │                     (derived from "Niko's Ultimate MIDI Pack",
        │                     a commercial producer sample pack — see §5)
        ▼
   chord progression (per-phrase, style-labeled: pop_standard / pop_complex /
   dark / r&b)
        │
        ▼
 [2] Texture arrangement (AccoMontage.py, ported from zhaojw1998/AccoMontage)
        │  — PianoTree VAE embeddings + POP909-derived phrase library;
        │    retrieves and blends full piano accompaniment textures that
        │    match the chords/melody, with edge-weight transition scoring
        │    between adjacent phrases (style-transfer, not generation)
        ▼
   MIDI (melody + chords) + MIDI (melody + textured accompaniment) + JSON log
```

Segmentation (phrase labels like `A8A8B8B8`, 4- or 8-bar phrases only) is a
**mandatory hand-provided input**, not inferred. Pretrained artifacts
(`model_master_final.pt`, VAE state dict, precomputed edge-weight/phrase
`.npz` files) are **not fully in-repo** — some must be downloaded separately
from Google Drive, so the repo alone isn't fully reproducible.

---

## 2. The DP harmonization stage — the one piece structurally close to Harmonyx

`chorderator/utils/models/DP.py`'s `DP.solve()` is a **per-phrase template
retrieval + Viterbi-style DP**, not a generative model:

- For each melody phrase, `pick_templates()` retrieves candidate chord
  progressions (`ChordProgression` objects) from the template library.
- Each candidate gets a three-part score: **micro** (progression fits this
  phrase's actual melody notes), **mid** (progression's own internal
  coherence/style), **macro** (transition score to the *previous* phrase's
  chosen progression, weighted `0.9` DP-continuity vs `0.1` local fit).
- Standard DP: `_dp[i][j] = (best_path, cumulative_score)`, argmax backtrace
  at the end.

**This is architecturally the closest thing in the peer set to Harmonyx's own
L1 corpus retrieval** (`app/generation/corpus.py` picks few-shot examples by
tag) — both are "retrieve from a labeled progression library, score
candidates, pick a path" rather than a from-scratch generative model. The
differences matter more than the similarity:

- AccoMontage2's DP chains **whole per-phrase progressions** end-to-end with
  a transition score between phrases; Harmonyx's L1 corpus feeds few-shot
  **examples** to an LLM (L4, not started) or the rule grammar walks
  **chord-to-chord** (Q3), not phrase-to-phrase template splicing.
- The template library is **pop-style, licensed from a commercial MIDI pack**
  (Niko's Ultimate MIDI Pack via pianoforproducers.com) — not something to
  import into a classical/hymn corpus regardless of format compatibility.
- No hard theory gate: `SOLVE_WITHOUT_THESE_PROGRESSIONS` is a hardcoded
  ID blocklist (3 IDs), the opposite of Harmonyx's `validate.py` theory gate
  (L2) with named rules and a fixer (L3).

---

## 3. The texture stage — heavy ML, not a fit for Harmonyx's footprint

`accomontage/` (vendored from the original zhaojw1998/AccoMontage repo) is a
full research codebase: `amc_dl` (custom PyTorch training framework),
`ptvae.py` (PianoTree VAE for texture embedding), `AccoMontage.py` (phrase
retrieval + blending/"style transfer" over embeddings). This requires a
trained checkpoint, GPU-optional-but-assumed PyTorch inference, and a
precomputed phrase/edge-weight index built from **POP909**. It's a solid
piece of ISMIR-grade research engineering, but it's the opposite of
Harmonyx's philosophy (deterministic, locked-fixture, no-training-required
part-writing). Not a fit even conceptually — Harmonyx has no analogous
"accompaniment texture" surface today (SATB voicing is voice-leading-correct,
not textural/rhythmic variation).

---

## 4. POP909 — what it actually is

`music-x-lab/POP909-Dataset`: **909 pop songs**, each as a MIDI with
`MELODY`/`BRIDGE`/`PIANO` tracks plus separately extracted beat/chord/key
annotation text files (`chord_audio.txt`: start/end time + chord name;
`beat_midi.txt`; `key_audio.txt`), and multiple human-arranged `versions/`
per song. It's a **pop piano-arrangement corpus**, used here purely as the
texture-donor source for AccoMontage's embedding library (via
`process_pop909.py` and the `POP909 4bin quantization` index files shipped in
`chorderator/static`) — not as harmonic-analysis ground truth like
When-in-Rome (#06). No Roman-numeral content; chords are named
(`C`, `Am7`, etc.), not functionally labeled, and the genre (pop) doesn't
overlap with Harmonyx's chorale/hymn domain.

---

## 5. Steal / don't-steal

**Steal (ideas only, and only if arrangement is ever scoped):**
- The **micro/mid/macro scoring shape** for phrase-level template DP (fit to
  local melody, internal template quality, transition to neighbor) as a
  design pattern if Harmonyx ever does phrase-level retrieval beyond
  chord-to-chord grammar — conceptually adjacent to, but heavier than,
  today's L1 few-shot retrieval.
- Mandatory phrase-segmentation-as-input (`"A8B8A8B8"`) as a simple, honest
  UX pattern: don't pretend to infer structure the system can't reliably
  detect — same spirit as Harmonyx admitting the analyzer's NCT/cadence
  limits rather than hiding them.

**Don't steal:**
- No code port. The texture engine's PyTorch/VAE dependency, external
  pretrained-weights-on-Google-Drive requirement, and lack of any hard
  theory gate are all inconsistent with Harmonyx's deterministic,
  self-contained, locked-fixture approach.
- Don't treat the Niko chord-progression template library as an importable
  corpus — pop style, and sourced from a **commercial** producer MIDI pack
  (licensing chain unclear beyond "redistributed by this research repo"),
  unlike Harmonyx's own hand-written or (potentially) When-in-Rome-derived
  entries.
- Don't treat POP909 as harmonic ground truth (it isn't RN-labeled) — it's
  only a texture/arrangement corpus, orthogonal to Harmonyx's analyzer eval
  needs (When-in-Rome, #06, is the right corpus for that).

---

## 6. Open questions

- Is a "melody-in, generate pop/piano accompaniment" track ever actually on
  Harmonyx's roadmap, or does "arrangement" for this project mean something
  narrower and more classical (e.g. hymn keyboard reduction, organ
  accompaniment styles for existing SATB output)? AccoMontage2's whole
  design targets pop piano texture, which doesn't map cleanly onto either.
- If arrangement is ever scoped, is a from-scratch lightweight
  classical-accompaniment-texture library preferable to adopting a
  PyTorch/VAE stack that has no theory gate and would sit oddly next to the
  rest of Harmonyx's deterministic architecture?

This closes the currently-planned research queue (#01–#07 per
`docs/CLASSICAL-AI-LANDSCAPE.md` §10). Remaining §10 rows (JJazzLab,
rnbert/μMoE-RNBERT, ai-music-theory/MuTheoryEval) are lower priority and not
scheduled unless the human names one.
