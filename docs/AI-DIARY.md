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

## Entry 10 — M1 realizer built end-to-end; a real bug found; session-cost lesson

Built most of Milestone 1 in one continuous run:
- `chords.py`, `voicing.py`, `rules.py` — all 18 locked `test_partwriting.py`
  fixtures pass on the first real attempt.
- `realize.py` (the DP/Viterbi search) — manually verified against several
  progressions, including the exact M1 acceptance case (`I-IV-V-I` in
  C major): produced a genuinely idiomatic, zero-violation voicing (common-
  tone retention, correct leading-tone resolution) on the very first real
  end-to-end run.
- Wrote `tests/test_generation_chords.py`, `tests/test_generation_voicing.py`,
  `tests/test_generation_realize.py`.

**A real bug surfaced:** `voicing.candidate_voicings` does not verify that an
explicitly-given soprano note is actually a chord tone before building the
other three voices around it. If alto/tenor/bass can still cover the chord's
other tones, it returns a "valid" voicing with a wrong note sitting in the
soprano -- `rule_violations` has no check for "is this voice a chord tone at
all," so nothing catches it. This is a seam bug: `voicing.py` and
`realize.py` were each individually correct against their own narrow tests,
but the assumption `realize.py`'s docstring made ("an incompatible soprano
always yields zero candidates") was never actually enforced by `voicing.py`.
Caught by `test_realize_incompatible_soprano_raises_realization_error`
failing (1 failed, 62 passed). **Not fixed yet -- deferred to the next
chunk**, on purpose, per the session-cost decision below.

**Session-cost lesson (drove real decisions):** this all happened as one
long, continuous session, plus a lot of interactive debugging (~15-20
separate script runs while chasing a DP dead-end investigation -- which
turned out to be correct behavior, not a bug, but took real back-and-forth to
confirm). The user flagged the cost, and we agreed on:

1. Break future work into small, narrowly-scoped chunks with explicit stop
   points -- not "implement Milestone 1," but "implement exactly this
   function against exactly this test."
2. Adopt a compartmentalized / need-to-know model for future implementer
   agents (the user's analogy: like Apple engineers, each only sees their own
   narrow piece), with an orchestrator role (full context) explicitly owning
   the *seams* between chunks -- because seam bugs (like the one above) are
   exactly what a narrowly-scoped agent structurally cannot catch on its own.
3. Added `AGENTS.md` at the repo root: any agent working here must ask for
   confirmation before a large continuous task, work in small chunks, and
   read the orientation docs first.
4. Added `docs/START-HERE.md`: a plain-language, human-readable status doc,
   separate from the more technical `STATUS.md` / `AI-DIARY.md`.
5. Learned this session's environment is **ephemeral** -- uncommitted work
   can be lost if the session ends. Commit discipline needs to happen at
   natural checkpoints, not only at the end.

**State at end of this entry:** `app/generation/` (chords.py, voicing.py,
rules.py, realize.py) + 3 new test files, committed and pushed as-is (bug
included, documented, not fixed). No further implementation work started
past this point -- the next session should pick up with a single narrow task,
not "continue the plan" broadly. The finer chunk breakdown discussed this
session still needs to be formalized into `IMPLEMENTATION-PLAN.md` in a
future, separate step.

## Entry 11 — Post-M1–M5 feature burst + handoff docs (2026-07-21)

Later the same calendar day (and a long Grok session), the deferred soprano
bug was fixed and the plan was driven much further than Entry 10 expected:

- M2 generation eval + CI
- `POST /generate`, `POST /progression` (grammar)
- Frontend Generate tab; OSMD preview; grand-staff MusicXML; Play @ 75 BPM
- Commits through `c1cc643` on `claude/harmonic-analysis-api-loc82f`

User feedback: rule-grammar progressions feel Theory-I vanilla. Brainstormed
optional **LLM progression proposer**: no train-from-scratch; API key; curated
corpus few-shot; validator + visible closest-fix; grammar remains default.
Captured as `docs/LLM-PROGRESSION-SPEC.md` (design only — not implemented).

**Handoff (token discipline):** refreshed `docs/START-HERE.md`, `docs/STATUS.md`,
`docs/AGENT-START-HERE.md` so the next session does not re-read this chat and
does not re-open fixed bugs. Open queue: LLM phases L1+, M4 `/check`, richer
grammar, analyzer A1/A2/A7.

Next human action: start a **fresh** chat; paste the START-HERE blurb; name
one chunk only.

## Entry 12 — LLM L1–L3 implemented; Q3 scoped (2026-07-21)

Same day, a focused Grok session implemented the LLM **foundation** only
(no API client, no UI):

| Phase | Commit (feature branch) | Artifacts |
|-------|-------------------------|-----------|
| L1 corpus | `f0ae8ab` | `data/progression_corpus.json` (~40 hand templates), `app/generation/corpus.py`, `tests/test_generation_corpus.py` |
| L2 validator | `154155f` | `app/generation/validate.py`, `tests/test_generation_validate.py` — theory gate (empty/unknown/forbidden/cadence/locks) + optional engine gate |
| L3 fixer | `78eb0d7` | `app/generation/fix.py`, `tests/test_generation_fix.py` — `suggest_fixes`; `validate_progression(..., suggest=True)` |

Full suite after L3: **~133 passed**. Branch was **ahead of origin by 3**
(L1–L3) at handoff — **push if not yet remote**.

Design choice (L2): secondary dominants are **not** house-forbidden; only
explicit retrogressions (`V→IV`, etc.) fail theory. L3 prefers fixing the
forbidden *destination* chord (e.g. IV→I) over rewriting the dominant.

User asked to **scope Q3** (richer rule grammar, no LLM) then continue in a
**new chat** to save credits. Captured as:

- **`docs/RICH-GRAMMAR-SPEC.md`** — Q3a (inversions+Cad64), Q3b (`spice` +
  secondary dominants), Q3c (style presets); defaults agreed in-doc.
- Handoff refresh: `START-HERE.md`, `STATUS.md`, `AGENT-START-HERE.md`,
  this entry; LLM spec phases L1–L3 marked done.

**Do not start Q3 implementation in the same breath as reading this** —
next session should paste START-HERE, read RICH-GRAMMAR-SPEC if doing Q3,
stop, and wait for “implement Q3a only” (or another single chunk).

Open queue order (human still chooses): **Q3a recommended**, else L4, Q2
`/check`, Q4 analyzer.

## Entry 13 — Q3a–c richer rule grammar (2026-07-21)

Implemented the full Q3 offline grammar epic in three commits on
`claude/harmonic-analysis-api-loc82f` (push if still local-only):

| Chunk | What landed |
|-------|-------------|
| **Q3a** | Higher inversion traffic (`I6`/`ii6`/`IV6`/`V6`); Cad64 approaches → V\|V7. |
| **Q3b** | `spice` 0–3; free walk emits `V/V` family at ≥2, `V/vi`/`V/ii` at 3; default 0. |
| **Q3c** | `style` presets `student`/`hymnal`/`spicy` → spice 0/1/2 (style wins); docs §9b. |

Code: `app/generation/grammar.py`, `app/models.py`, `app/main.py`, grammar +
progression tests. Docs: `START-HERE`, `STATUS`, `PARTWRITING-RULES` §9b,
this spec marked implemented. **No** frontend dropdown (optional later).

Full suite after Q3c: **~150+ passed**. Open queue now: L4 LLM client, Q2
`POST /check`, Q4 analyzer, Q5 PR/push polish.

## Entry 14 — Frontend spice UI + handoff file (2026-07-21)

Added Generate-tab **spice slider (0–3)** and **Student / Hymnal / Spicy / Max**
pills; Propose sends `spice` (+ `style` for 0–2) and status-echoes result.
Commit `12b97fc` (pushed with Q3a–c).

Handoff for chat clear: `docs/NEXT-AGENT-PASTE.txt` (paste-ready next-agent
prompt). Refreshed `AGENT-START-HERE.md` / `START-HERE.md` so Q3 is marked done
and agents wait for a human-named chunk (L4 / Q2 / Q4 / Q5).

## Entry 15 — Classical × AI landscape research (2026-07-21)

Human asked for recent GitHub peers relevant to Harmonyx, then a **broader**
scan (arrangement, AI music theory, adjacent), with long-term interest in
owning classical music × AI.

Documented findings in **`docs/CLASSICAL-AI-LANDSCAPE.md`** (living map):

- **Tier S architecture peers:** Resonance (LLM → RN only → deterministic
  voice-leading), choral-counterpoint, choral-llm-workbench, thiri-mcp /
  music21-mcp.
- **Tier A classical:** PartWise (M4 check UX), chorale-optimizer,
  ChoraleHarmonizer, When-in-Rome, RNBERT / μMoE-RNBERT, etc.
- **Tier B arrange/reharm:** AccoMontage2, POP909, JJazzLab, D3EMO, bebop, …
- **Tier C:** CoComposer, DAW MCP/skills, ai-music-theory KB, MuTheoryEval,
  smg_metric, PDMX.
- **Tier D:** audio full-song / chatbot noise (explicitly deprioritized).
- Deep-dive order, refresh queries (§8), domain expansion backlog (§11).

Also linked from `START-HERE.md` optional reading. **No code changes.**
Not a build queue — study only unless human names a chunk.

## Entry 16 — Research deep-dives begun (2026-07-21)

Started Tier S deep-dives; notes under `docs/research/`:

1. **`01-resonance.md`** — Next.js + Groq; LLM emits RN JSON only; Zod;
   always-200 fallback templates; block voice-leading (not SATB). Steal for
   L4: `source`/`reason`, JSON+retry, force user key, never empty propose.
2. **`02-choral-counterpoint.md`** — Melody→SATB engine; hard/soft checker
   calibrated on Bach; outer-voice oracle; fermata phrase boundaries;
   false-alarm harness. Steal for M4: V vs W tiers, Bach validation culture.
   **Do not** loosen locked `test_partwriting.py` to match their warnings.

Next research chunk (when human says): PartWise.


## Entry 17 — Research docs committed + next-session paste (2026-07-21)

Committed landscape + deep-dives 01–02 on `claude/harmonic-analysis-api-loc82f`.
Added `docs/NEXT-RESEARCH-PASTE.txt` for a fresh agent to continue with **PartWise**
(#03) without re-explaining context. Research only; no product code.

## Entry 18 — Research deep-dive #03 PartWise (2026-07-21)

Read `cjohanson64-netizen/PartWise` (README + FastAPI evaluate path + TAT rule
graphs + React OSMD grader). Notes: `docs/research/03-partwise.md`.

**Product:** student writes SATB + RN in OSMD editor → evaluate → % score,
pass/warn/fail cards, green/orange/red notes, try-again loop.

**Stack:** React/Vite + OSMD; FastAPI; pitch primitives without music21;
TryAngleTree graphs for rule *contracts*, Python adapters for comparisons.

**Rules actually run (V1):** tiered ranges, voice order, soft upper spacing,
complete triads / NCT, harmonic-flow edges on I–ii–IV–V–vi, soft V–I cadence.
Parallels, LT, sevenths authored in TAT but **not wired** (roadmap V2–V3).

**For M4:** steal projection/issue shape + color mapping + optional weighted
score; **do not** adopt TAT runtime or soften locked `test_partwriting.py`.
Harmonyx `rules.py` already deeper than their V1 checker.

Updated landscape §13 + changelog. Next research chunk when asked:
**#04 chorale-optimizer**.

## Entry 19 — Research deep-dive #04 chorale-optimizer (2026-07-21)

Read `604korupt/chorale-optimizer` (README + `harmonizer.py` / `main.py` /
`score_svg.py` / `test_harmony.py`; 81 unittests OK). Notes:
`docs/research/04-chorale-optimizer.md`.

**Product:** soprano MIDI + chord symbols → ATB; Tkinter table + VexFlow
browser score with Web Audio play.

**Engine:** phrase-split beam search (width 40, soft costs) then ≤6 iterations
of 12 sequential fixup passes (coverage, parallels, doubling, 7th/LT, etc.).
Always returns voicings (best-effort); no fail-closed path.

**Vs Harmonyx:** they require fixed soprano and soft-search; we RN→SATB with
hard DP prune + `RealizationError`. Vocab table ~80 symbols including
secondaries, mixture, N6, Ger65 — useful checklist, not a reason to drop
music21 RN.

**Steal:** cadence chunking idea, residual `(!)` flags, optional best-effort
mode *concept*, property tests on generate→rules. **Don’t** replace default
`realize.py` or loosen locked fixtures.

Updated landscape §13 + changelog. Next research when asked:
**#05 choral-llm-workbench**.

## Entry 20 — Session wrap for Claude Code handoff (2026-07-21)

Human shifting from Grok session → fresh Claude Code. No product code this
session after #04 research.

**Committed this wrap:** research #04 + landscape/diary updates + refreshed
handoff pastes (`NEXT-AGENT-PASTE.txt`, `AGENT-START-HERE.md`, `START-HERE.md`,
`NEXT-RESEARCH-PASTE.txt`).

**Human north star (context):** wants to be wowed by classical music AI across
realms (analyze, check, generate, reharm, arrange, teach, explain) — multi-year
domain ambition; still one named chunk per session per AGENTS.md.

**Claude Code: read handoff, stop, wait.** Do not auto-start L4/M4/research #05.

## Entry 21 — Research deep-dive #05 choral-llm-workbench (2026-07-21)

Human reaffirmed the north star explicitly this session: building "the
ultimate classical music AI tool" — any peer findings not applicable now
should still be logged as future-useful, not discarded. Landscape doc §1
("king of classical × AI") and §11 (domain expansion backlog) already existed
for exactly this; added a new §11 row for note-level LLM interfaces instead of
starting a separate goals doc.

Read `asb-42/choral-llm-workbench` (README, `USER_MANUAL.md`,
`SYSTEM_PROMPTS.md`, `ARCHITECTURE-VUE.md`, `KNOWN_ISSUES.md`,
`docs/system/ROADMAP-v2.md`; full read of `ikr_light.py`, `tlr_converter.py`,
`transformation_validator.py`, `core/llm/adapter.py`, `core/llm/satb.py`,
`core/score/reharmonize.py`). Ran `pytest tests/test_functional.py` (4 passed)
and the full `tests/` dir (11 collection errors — syntax error, missing
`hypothesis` dep, broken constructor call). Notes:
`docs/research/05-choral-llm-workbench.md`.

**Product:** MusicXML → IKR-light (canonical dataclass model) → TLR
(line-per-event plaintext LLM interface) → local Ollama LLM → flag-gated
`TransformationValidator` → MusicXML back out. Same "LLM proposes, code
enforces" philosophy as Harmonyx's own L4 plan, arrived at independently.

**Steal (idea only, later):** TLR-style explicit line-per-event text
serialization + text-diff-as-score-diff, for if Harmonyx ever needs an LLM to
touch literal note-level score content (not just RN symbols) — e.g. a future
reharm-an-existing-chorale or explain-a-passage feature. Not needed for
current RN-based L4; logged in landscape §11, not scheduled.

**Don't steal:** any actual code. Repo is sprawling/self-contradictory — 20+
near-duplicate `gradio_app_satb_*.py` variants, a Gradio UI the repo's own
`KNOWN_ISSUES.md` says to "ABANDON" mid-project while also shipping a
parallel NestJS+Vue stack that hasn't replaced it; CI only runs one of 25
test files and the full suite doesn't even collect. Harmonization depth is
thin (one root+quality triad per measure, no voice leading) — Harmonyx's
`realize.py` is already ahead here.

Updated landscape §10 (marked #5 done) and §11 (new backlog row). Also added
**AGENTS.md Rule 2b**: suggest a chat reset at chunk boundaries (findings
written to file) — human-triggered only, never automatic.

Next research when asked: **#06 MarkGotham/When-in-Rome**.

## Entry 22 — Research deep-dive #06 When-in-Rome (2026-07-21)

Cloned `MarkGotham/When-in-Rome` (README, `syntax.md`, directory scan of
`Corpus/`/`Anthology/`, structure/docstrings of `Code/romanUmpire.py` and
`Code/anthology.py`). Not a tool/product — a **meta-corpus**: ~1,300
RomanText `analysis.txt` files + aligned `score.mxl` covering ~1,500 works
(DCML corpora, TAVERN, Haydn Op.20, BPS-FH, Tymoczko's TAOM incl. **371 Bach
chorales**, new WTC-I preludes and OpenScore-Lieder songs), plus thin
music21-based tooling (`romanUmpire.py` scores RN-analysis-vs-score
agreement; `anthology.py` mines chord/progression instances). Notes:
`docs/research/06-when-in-rome.md`.

**Validation, not new work:** `syntax.md`'s RomanText spec matches Harmonyx's
existing RN vocabulary closely — `Cad64`, secondary-dominant `/V` slashes,
key-then-continuation header style are all already how `grammar.py`/
`chords.py` work. Confirms current choices rather than requiring changes.
Two gaps *not* yet in Harmonyx: augmented-sixth shorthands (`It6`/`Fr43`/
`Ger65`) and suspension bracket syntax (`V[add4][no3]`) — logged as
ready-made syntax to adopt if either ever gets scoped, not scheduled now.

**Steal (idea, later):** (1) the 371 aligned Bach chorales as a candidate
real-corpus source for L1 few-shot expansion beyond today's 40 hand-written
entries — needs a segmentation/tagging pipeline first, not a file copy, and
correct CC BY-SA attribution if ever imported; (2) `romanUmpire`'s
slice-based RN-vs-score matching technique, relevant to analyzer **A7**
(RN-agreement eval, on the open queue) — reimplement the idea against
Harmonyx's own data shapes, don't vendor the module (CC BY-SA + coupled to
WiR's file layout).

**Don't steal:** no code port. Also clarified in the note: WiR's umpire
(analysis-vs-score matching) is a **different problem** from M4 `/check`
(part-writing violations in an SATB realization) — relevant to A7, not M4.

Updated landscape §10 (marked #6 done), §11 (new backlog row for A7 +
real-corpus eval), §13 index, and §14 changelog.

Research chunks #01–06 are now all done. Next default (#07 AccoMontage2 +
POP909) is arrangement-track-only — per `docs/NEXT-RESEARCH-PASTE.txt`, don't
continue there without an explicit "continue research" from the human.
Stopping for check-in as instructed.

## Entry 23 — Research deep-dive #07 AccoMontage2 + POP909 (2026-07-21)

Human asked to continue with the next research chunk. Read
`billyblu2000/AccoMontage2` (README, full repo tree via `gh api`,
`chorderator/core.py`, `chorderator/utils/models/DP.py` in full) and
`music-x-lab/POP909-Dataset` (README, tree). Notes:
`docs/research/07-accomontage2.md`.

**Product:** pop melody-in → two-stage pipeline: (1) per-phrase chord-template
DP retrieval (`DP.py`, micro/mid/macro scoring, chained via Viterbi) over a
5k+ progression library sourced from a commercial MIDI pack, then (2) full
piano-accompaniment **texture** arrangement via the original zhaojw1998
AccoMontage engine (PianoTree VAE + POP909-derived phrase embeddings,
PyTorch). Requires hand-provided phrase segmentation (`"A8B8A8B8"`) and
externally-hosted pretrained weights — not fully self-contained in-repo.
**Corrected the landscape doc's implied recency:** last real commits are
2023-05 (AccoMontage2) / 2020-08 (POP909) — the 2026 "updated" timestamps
were star/watch activity, not code changes.

**Vs Harmonyx:** Tier B (pop/arrangement), not classical — no overlap with
`rules.py`/`realize.py`. The DP harmonization stage's micro/mid/macro
template-scoring shape is the one structurally-adjacent idea to Harmonyx's L1
corpus retrieval, worth remembering only if arrangement is ever scoped. The
texture engine (heavy PyTorch/VAE, no theory gate, external weights) doesn't
fit Harmonyx's deterministic/locked-fixture philosophy at all — not a steal
target.

**Steal:** micro/mid/macro phrase-scoring pattern (idea only, future
arrangement scoping); honest mandatory-segmentation-as-input UX precedent.
**Don't steal:** any code, the PyTorch/VAE texture stack, or POP909/Niko-pack
as corpus content (pop, not RN-labeled, commercial-pack provenance).

Updated landscape §10 (marked #7 done), §13, §14. **This closes the
originally-planned research queue #01–#07** — remaining candidates (JJazzLab,
rnbert/μMoE-RNBERT, ai-music-theory/MuTheoryEval) need an explicit human ask,
not a default "next chunk." Per AGENTS.md Rule 2b: good point for a chat reset
before naming the next task (a build chunk, or a new research target).

## Entry 24 — Research deep-dive #08 Shimaoka-SATB-SkillSet (2026-07-21)

Resumed via `/resume`, human said "continue research." Noted
`docs/START-HERE.md`'s "#07 default next" line was stale — #07 was already
done (`edde19f`) — and switched to the live source of truth,
`docs/RESEARCH-QUEUE.md`, whose suggested order puts
`ShikiSuen/Shimaoka-SATB-SkillSet` first (Tier 1 #1, human-flagged, all
markdown). Cloned the repo; read `README_EN.md`, `SKILL.md` (full),
`references/voice-leading.md`, `d-chords.md`, `notation-syntax.md`,
`rules.md` (full each), the repo's own `AGENTS.md`, and one `VALUEADD/`
review. Notes: `docs/research/08-shimaoka-satb-skillset.md`.

**Product:** not a tool — a pure LLM-context knowledge base packaging Tokyo
University of the Arts' Shimaoka Yuzuru four-part-harmony textbook ("Swing
Theory": chords oscillate rest↔displacement) so an LLM can do SATB
part-writing directly from prompt context, with **no validator, no
enforcement code**. Explicit counter-example to Harmonyx's "LLM proposes,
code enforces" bet (already independently validated by research #05).

**Vs Harmonyx:** the T/D₁–D₆/S "functional distance" model is interesting but
internally inconsistent (Ⅳ is both S and D6, per an included Sonnet5 review)
— not adopted. The A–G rules compilation independently confirms Harmonyx's
existing hard-rule set (`PARTWRITING-RULES.md` §0–7) is complete and
standard; one narrow new item (`rⅤ7 → Ⅰ2` chordal-7th ascending exception)
noted for future M4 violation-report nuance. Biggest concrete finding: **a
second independent peer flags the augmented-sixth gap** (research #06
already did via When-in-Rome's `It6`/`Fr43`/`Ger65` notation) — this repo
adds the "when to use French vs Italian vs German 6th" theory side. Also
surfaces a checklist of named-but-unmodeled features (Neapolitan 6th,
borrowed/modal-mixture chords, Picardy third, pedal point) worth keeping as a
reference list if the grammar ever grows past Q3c.

**Steal:** augmented-sixth usage theory + the unmodeled-feature checklist
(ideas only). **Don't steal:** the functional-distance reframing (self-
inconsistent); the repo's own `AGENTS.md` working philosophy (directly
opposite of Harmonyx's small-chunks/ask-first discipline — noted, not
imported); "LLM enforces via context alone" as an alternative to L2/L3
(no validator here to even compare against).

Updated `docs/CLASSICAL-AI-LANDSCAPE.md` §11 (two new backlog rows) and §13/
§14, `docs/RESEARCH-QUEUE.md` (#1 marked done, suggested-order note), and
`docs/START-HERE.md`'s stale "#07 default" pointer (now points at
`RESEARCH-QUEUE.md`). Per AGENTS.md Rule 2b: good point for a chat reset
before naming the next task — next research default (human picks) is
`git-scarrow/music-arranger` (CP-SAT twin to the realizer) or the
thiri-mcp/music21-mcp MCP pair.

## Entry 25 — Research deep-dive #09 music-arranger (2026-07-21)

Human picked `git-scarrow/music-arranger` (Tier 1 #2) over the thiri-mcp/
music21-mcp pair for this chunk. Repo moved off GitHub to Codeberg
(`codeberg.org/scarrow/music-arranger`); no `README.md` found (404) so
architecture was reconstructed from source: `music_arranger.py`,
`solver_template.py`, `verify_solver.py`, `verify_barbershop.py`,
`theory_definitions.json`, read via raw file fetch (no local clone, no gh —
Codeberg not GitHub). No LICENSE file found — treated as all-rights-reserved,
ideas cited, no code vendored. Notes: `docs/research/09-music-arranger.md`.

**Product:** natural language → Claude tool-call extraction (`apply_arrangement`,
forced tool_choice) → structured arrangement params → **Google OR-Tools
CP-SAT constraint solver** → SATB (or barbershop 4-voice) voicing. The
closest peer yet to Harmonyx's own L4 plan — same "LLM proposes, code
enforces" bet — but the deterministic engine is a **declarative constraint
solver** (all voice/step variables + all hard/soft constraints declared at
once, `model.Maximize(sum(objective_terms))`) instead of Harmonyx's
sequential DP/Viterbi realizer.

**Vs Harmonyx:** not a case for replacing the DP realizer — CP-SAT is a
heavier dependency for a benefit (global joint constraint optimization)
Harmonyx's currently-scoped, checkably-local rule set (`PARTWRITING-RULES.md`
§0–7) doesn't need; the locked DP + `test_partwriting.py` fixtures stay as-is
per `AGENTS.md` Rule 4. Two things worth carrying forward as ideas (not
code): (1) `verify_solver.py`'s **pre-solve infeasibility diagnostics** —
named, specific failure reasons (melody-outside-scale, empty-domain
conflict, cadence truncation, cadence-vs-pinned-melody conflict) reported
*before* solving, relevant to M4 `POST /check` design or to
`POST /generate`/`POST /progression` error responses; (2) `verify_barbershop.py`'s
soft-vs-hard scale constraint duality independently confirms Harmonyx's
existing `spice`/`style` soft-preference design (Q3b/c) is the right shape —
no change needed, just validation. Also flagged as a **don't-steal**: this
repo's wide single-tool-call NL→full-arrangement schema is more expressive
but more tightly coupled to solver internals than Harmonyx's planned
"LLM emits RN only, deterministic stage handles voicing" L4 contract (also
independently validated by research #01 resonance) — the narrower contract
stays the plan.

**Steal:** pre-solve infeasibility diagnostic pattern (M4/error-response
idea); soft/hard scale duality as confirmation, not a new idea. **Don't
steal:** CP-SAT replacing the DP realizer; the wide NL→full-arrangement tool
schema; any literal code (no confirmed license).

Updated `docs/CLASSICAL-AI-LANDSCAPE.md` §3 (Tier S table — music-arranger
row), §11 (two new backlog rows: pre-solve diagnostics, CP-SAT-as-alternative),
§13/§14, `docs/RESEARCH-QUEUE.md` (#2 marked done, suggested-order + next-
default updated to thiri-mcp/music21-mcp), and `docs/NEXT-RESEARCH-PASTE.txt`.
Per AGENTS.md Rule 2b: good point for a chat reset before naming the next
task — next research default is the **thiri-mcp + music21-mcp** MCP pair
(Tier 1 #3–4).
