# Research queue — repos still to deep-dive

Working list of what's left to study before doing more build work. Not a
build queue — research only, per `AGENTS.md`. Pulls together the remaining
rows from `docs/CLASSICAL-AI-LANDSCAPE.md` §10, new candidates found in the
2026-07-21 follow-up GitHub scans (SATB/arrangement/AI-tools/score-DB sweep +
a focused OMR sweep), and a directly-linked repo the human pointed at
(`Shimaoka-SATB-SkillSet`). One peer per research chunk, same convention as
`docs/research/01`–`07`.

Format per entry: **repo** — why it's worth a full read, and what to actually
read (not just "clone it").

---

## Tier 1 — closest architecture/product overlap (read first)

1. **`ShikiSuen/Shimaoka-SATB-SkillSet`** — **Done**, see
   `docs/research/08-shimaoka-satb-skillset.md`.
   (github.com/ShikiSuen/Shimaoka-SATB-SkillSet) — Pure knowledge-base-as-
   LLM-context repo (no code engine): packages the Tokyo University of the
   Arts' Shimaoka Yuzuru four-part-harmony textbook ("Swing Theory" —
   rest/displacement oscillation) into structured markdown meant to be
   handed to an LLM as system-prompt context so it can do SATB part-writing
   directly, with **no validator, no enforcement code** — the opposite of
   Harmonyx's "LLM proposes, code enforces" philosophy, and worth citing as
   the explicit counter-example. Already skimmed `README_EN.md`: an 8-step
   writing procedure (key/cadence layout → cadential-unit skeleton → cadence
   formula → bass fill → soprano → inner voices → rules check →
   ornamentation), a compact prefix-degree-suffix chord notation richer than
   current Harmonyx RN grammar (rootless/quasi-borrowed/Neapolitan/forced-
   major-minor/tonicizing-to/sustained-bass markers), and full **augmented
   sixth chord** (French/Italian/German) coverage — a second independent
   source for the same gap research #06 (When-in-Rome) already flagged,
   raising its priority if augmented sixths ever get scoped. All markdown
   (`SKILL.md` + 14 `references/*.md` + amalgamated file), no code to trace
   — should be a fast chunk relative to the codebase deep-dives. Read the
   full `SKILL.md`/`_SKILL-Amalgamated.md`, `references/voice-leading.md`,
   `references/d-chords.md` (augmented 6ths), and `references/notation-
   syntax.md`; skim the `VALUEADD/` LLM reviews for outside critique.

2. **`git-scarrow/music-arranger`** — **Done**, see
   `docs/research/09-music-arranger.md`. (moved to Codeberg:
   `codeberg.org/scarrow/music-arranger`) — Natural-language → SATB via
   Claude tool-call extraction + **Google OR-Tools CP-SAT constraint solver**.
   Already skimmed `music_arranger.py` (Claude tool schema) and
   `solver_template.py` (constraint methods: harmonic membership, no-crossing,
   max leap, cadence, diatonic scale, doubling, spacing, chord completeness,
   parallel-octave penalty, 7th resolution) — this maps almost 1:1 onto
   `PARTWRITING-RULES.md` §0–7, but solved via **declarative constraint
   programming instead of DP/Viterbi search**. Small (0★, single author,
   already moved off GitHub) but the *technique* is the point: worth a real
   read of the full solver + `verify_solver.py`/`verify_barbershop.py` tests
   to see whether CP-SAT handles cases DP struggles with (e.g. simultaneous
   global constraints vs. sequential DP scoring). Closest thing yet to an
   "L4 + realizer, one architecture" twin.

3. **`BluesPrince/thiri-mcp`** — **Done**, see
   `docs/research/10-thiri-mcp-and-music21-mcp.md`. Deterministic
   music-theory MCP server (RN analysis, voicing, reharmonization) for
   Claude/Cursor, hosted at `mcp.thiri.ai`.

4. **`SimonsonM/music21-mcp`** — **Done**, see
   `docs/research/10-thiri-mcp-and-music21-mcp.md` (read together with
   thiri-mcp as one chunk). music21 exposed as 7 MCP tools (key detection,
   RNA, cadence/counterpoint generation, melody harmonization, MIDI/MusicXML
   parsing).

---

## Tier 2 — carried over from `CLASSICAL-AI-LANDSCAPE.md` §10 (not yet started)

5. **JJazzLab** (`jjazzboss/JJazzLab`, ~574★) — **Done**, see
   `docs/research/12-jjazzlab.md`. Mature, actively developed open-source
   **jazz backing-track arranger app** (Java/NetBeans RCP, 65-module Maven
   tree). Not classical, but the most complete *product* in the whole
   landscape map. Studied for product-completeness lessons: strict
   model/engine/UI separation behind a public `Rhythm`/`MusicGenerator` SPI,
   plus a third distinct chords-in/music-out technique (JJSwing's
   concatenative retrieval from a hand-curated MIDI phrase bank, scored
   against chord sequence + tags — no ML, no solver) alongside AccoMontage2's
   (#07) VAE-embedding retrieval and music-arranger's (#09) CP-SAT solving.

6. **rnbert** (`malcolmsailor/rnbert`) + **muMoE-RNBERT**
   (`TomusD/muMoE-RNBERT`) — **Done**, see
   `docs/research/13-rnbert-and-mumoe-rnbert.md`. Neural Roman-numeral-
   analysis baselines (ISMIR 2024 / ICASSP 2026): RNBert fine-tunes
   MusicBERT via per-note token classification, ~57-62% full-RN composite
   accuracy on a 1,404-score corpus (beats AugmentedNet #11 and ChordGNN);
   muMoE-RNBERT swaps in Multilinear-Mixture-of-Experts FFN layers for
   per-note expert-activation interpretability (heatmaps/bar charts), not
   higher accuracy. No neural path is scoped for Harmonyx's analyzer.

7. **`music-comp/ai-music-theory`** + **`thevertexlab/MuTheoryEval`** —
   **Done**, see `docs/research/14-ai-music-theory-and-mutheoryeval.md`.
   Machine-readable music-theory knowledge base (14-textbook concept graph,
   53 MCP tools incl. a self-describing `mt_directory` registry; its
   `analyze_roman_numerals` tool is single-chord, not score-sequence — no
   overlap with Harmonyx's analyzer) and an LLM music-theory-knowledge eval
   hub (aggregates 6 existing benchmarks into a weighted leaderboard,
   ~42-72% range across current frontier models on MusicTheoryBench).
   Relevant only if/when Harmonyx adds an explainer/tutor chat surface or
   needs a competence pre-check for L4's LLM — not urgent, no such surface
   is scoped today.

---

## Tier 3 — new candidates from the 2026-07-21 follow-up scans

8. **`owenbush/diatone`** — **Done**, see
   `docs/research/15-tier3-remainder.md`. Dependency-free C++17 music-theory
   library (notes/scales/chords/RN analysis/voice-leading), explicitly
   designed to be **safe to call from a real-time audio thread**. Different
   deployment target than Harmonyx (embedded/real-time vs. web API); read for
   the data-driven registry + strategy-interface design pattern rather than
   any usable code.

9. **`tskovlund/mcp-score`** — **Done**, see
   `docs/research/15-tier3-remainder.md`. MCP server for AI-driven score
   generation: natural language → notation via MusicXML + **live MuseScore/
   Dorico/Sibelius integration** (14★, very fresh). Compared the "live app
   integration" pattern (with its documented per-app capability ceiling) vs.
   Harmonyx's own OSMD-in-browser approach — no live-app bridge is scoped for
   Harmonyx.

10. **Humdrum/**kern** corpus tooling** — **Done**, see
   `docs/research/15-tier3-remainder.md`. `craigsapp/humdrum2musicxml`
   (Humdrum-to-MusicXML web service) and `leihua-dev/KernScores-downloader`
   (bulk `.krn` downloader for KernScores.org). Confirmed KernScores.org is a
   viable *additional* real-corpus source in principle (parallel to
   When-in-Rome, research #06) — but flagged that the downloader's target
   data is **CC BY-NC 4.0** (non-commercial), a real gate if it's ever used.

11. **`napulen/AugmentedNet`** — **Done**, see
    `docs/research/11-augmentednet.md`. (50★, MIT; last push actually
    2024-02-11 — the "pushed 2026-07-21" note above was a stale GitHub-scan
    artifact, corrected here) — the actual neural RNA model that produced the
    `analysis_automatic.rntxt` files inside When-in-Rome's corpus (research
    #06 referenced its output without covering the tool itself). CRNN,
    11-14-task multitask learning (key/degree/quality/inversion/voice
    pitches), reconciled at inference via pcset-cosine matching rather than
    a single argmax. Best full-RN accuracy ~45-52% even with synthetic-data
    augmentation — useful ceiling reference for Harmonyx's own analyzer eval.

---

## Tier 4 — parked, OMR/adjacent (deferred by product decision, log only)

Not recommended for a full deep-dive chunk — OMR was explicitly deferred
back in `docs/AI-DIARY.md` Entry 4 and stays in Tier D
(`CLASSICAL-AI-LANDSCAPE.md`) as "adjacent, not core moat." Logged here only
so the candidates aren't lost if that decision ever gets revisited:

- **`Audiveris/audiveris`** (2,637★, active) — the standard OSS OMR engine.
  AGPL-3.0 (viral license — relevant if OMR is ever wrapped rather than
  called out to).
- **`liebharc/homr`** (329★, active, pushed 2026-07-17) — camera photo →
  MusicXML; two-stage UNet segmentation + transformer symbol recognition.
  Also AGPL-3.0. More modern than Audiveris, same licensing caveat.

---

## Not on this list on purpose

- **PDMX** (`pnlong/PDMX`) and **smg_metric** (`OlyMarco/smg_metric`) — both
  already logged in landscape §6.4 as corpora/metrics resources, not
  architecture peers. Read opportunistically if a corpus or eval-metric need
  comes up; don't spend a dedicated chunk on them unless one does.
- Everything already covered in `docs/research/01`–`07` and anything in
  `CLASSICAL-AI-LANDSCAPE.md` Tier D (full-song audio models, generic theory
  chatbots, DAW/producer tools not listed above) — no new signal since the
  original compile.

---

## Suggested order

~~Shimaoka-SATB-SkillSet first~~ **Done** (`docs/research/
08-shimaoka-satb-skillset.md`) → ~~music-arranger~~ **Done** (`docs/research/
09-music-arranger.md`) → ~~thiri-mcp + music21-mcp~~ **Done** (`docs/research/
10-thiri-mcp-and-music21-mcp.md`) — **Tier 1 fully closed** → ~~Tier 3 #11
AugmentedNet~~ **Done** (`docs/research/11-augmentednet.md`) → ~~Tier 2 #5
JJazzLab~~ **Done** (`docs/research/12-jjazzlab.md`) → Tier 2 remainder →
Tier 3 remainder as time allows.

~~Tier 2 #6 rnbert / muMoE-RNBERT~~ **Done** (`docs/research/
13-rnbert-and-mumoe-rnbert.md`). ~~Tier 2 #7 ai-music-theory + MuTheoryEval~~
**Done** (`docs/research/14-ai-music-theory-and-mutheoryeval.md`) — **Tier 2
fully closed**. ~~Tier 3 #8 diatone, #9 mcp-score, #10 Humdrum tooling~~
**Done**, all three as one chunk (`docs/research/15-tier3-remainder.md`) —
**Tier 3 fully closed**.

**Queue status: Tier 1, 2, and 3 are all closed.** Only Tier 4 (OMR:
Audiveris, homr) remains, and it stays parked per `docs/AI-DIARY.md` Entry
4's product decision — not recommended for a dedicated chunk unless that
decision is revisited. No further default research chunk is queued; next
research work needs a new candidate or a re-opened Tier 4 decision from the
human.

As always: one peer (or one small related cluster, like the two MCP servers)
per chunk, notes written to `docs/research/0N-*.md`, landscape doc + AI-DIARY
updated at the end, human names the next chunk.
