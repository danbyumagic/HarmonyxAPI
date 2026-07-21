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

2. **`git-scarrow/music-arranger`** (moved to Codeberg:
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

3. **`BluesPrince/thiri-mcp`** — Deterministic music-theory MCP server (RN
   analysis, voicing, reharmonization) for Claude/Cursor, hosted at
   `mcp.thiri.ai`. Already flagged Tier S in the landscape doc but **never
   actually deep-dived** — confirmed still active (pushed 2026-07-19). Read:
   how it exposes RN/voicing operations as MCP tool calls, and whether its
   "computed not hallucinated" tool contract has ideas for how Harmonyx would
   expose `/analyze` + `/generate` + (future) `/check` as agent-facing tools.

4. **`SimonsonM/music21-mcp`** — music21 exposed as 7 MCP tools (key
   detection, RNA, cadence/counterpoint generation, melody harmonization,
   MIDI/MusicXML parsing). Same "agent-native theory" question as thiri-mcp,
   different design choice (wrap music21 directly vs. a custom deterministic
   engine). Worth comparing the two side by side in one chunk.

---

## Tier 2 — carried over from `CLASSICAL-AI-LANDSCAPE.md` §10 (not yet started)

5. **JJazzLab** (`jjazzboss/JJazzLab`, ~574★) — mature, actively developed
   open-source **jazz backing-track arranger app** (Java/NetBeans RCP). Not
   classical, but the most complete *product* in the whole landscape map —
   worth studying purely for "what does a finished, polished desktop music
   app look like feature-complete" product-completeness lessons, independent
   of the jazz domain.

6. **rnbert** (`malcolmsailor/rnbert`) + **muMoE-RNBERT**
   (`TomusD/muMoE-RNBERT`) — neural Roman-numeral-analysis baselines
   (ISMIR 2024 / ICASSP 2026). Only worth reading in depth if/when investing
   in a neural RNA path for the analyzer (current analyzer is fully
   rule-based via music21). Read together as one chunk: what's the accuracy
   delta vs. rule-based, and what would integration even look like
   (replace vs. ensemble vs. eval-only baseline).

7. **`music-comp/ai-music-theory`** + **`thevertexlab/MuTheoryEval`** —
   machine-readable music-theory knowledge base (MCP) and an LLM
   music-theory-knowledge eval hub, respectively. Relevant only if/when
   Harmonyx adds an explainer/tutor chat surface that needs grounding or
   needs to be benchmarked for theory correctness — not urgent, but worth
   knowing what already exists before building a bespoke eval.

---

## Tier 3 — new candidates from the 2026-07-21 follow-up scans

8. **`owenbush/diatone`** — dependency-free C++17 music-theory library
   (notes/scales/chords/RN analysis/voice-leading), explicitly designed to be
   **safe to call from a real-time audio thread**. Different deployment
   target than Harmonyx (embedded/real-time vs. web API) but worth a read for
   how they structure a theory engine for a completely different performance
   envelope — could surface API-design ideas even if the tech stack is
   irrelevant.

9. **`tskovlund/mcp-score`** — MCP server for AI-driven score generation:
   natural language → notation via MusicXML + **live MuseScore integration**
   (14★, very fresh). Different from thiri-mcp/music21-mcp in that it
   targets *notation editing* via a live MuseScore connection rather than
   pure analysis — worth comparing the "live app integration" pattern vs.
   Harmonyx's own OSMD-in-browser approach.

10. **Humdrum/**kern** corpus tooling** — `craigsapp/humdrum2musicxml`
   (Humdrum-to-MusicXML web service) and `leihua-dev/KernScores-downloader`
   (bulk `.krn` downloader for KernScores.org). Humdrum/**kern is a major
   classical-score corpus format alongside MusicXML/RomanText that hadn't
   surfaced before this scan — worth a short read purely to scope whether
   KernScores.org is a viable *additional* real-corpus source (parallel to
   When-in-Rome, research #06) if L1/analyzer-eval corpus expansion is ever
   revisited.

11. **`napulen/AugmentedNet`** (50★, pushed 2026-07-21 — actively maintained)
    — the actual neural RNA model that produced the `analysis_automatic.rntxt`
    files inside When-in-Rome's corpus (research #06 referenced its output
    without covering the tool itself). Worth reading alongside rnbert/μMoE
    (#6 above) as the third neural-RNA baseline, and specifically because
    it's the one already embedded in a corpus Harmonyx has already studied.

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
08-shimaoka-satb-skillset.md`) → rest of Tier 1 (thiri-mcp + music21-mcp
together — short and closely related, MCP theory exposure pattern) →
Tier 3 #11 AugmentedNet (quick, ties directly to already-read #06) →
Tier 2 in listed order → Tier 3 remainder as time allows.

Next default: **`git-scarrow/music-arranger`** (Tier 1 #2 — CP-SAT
constraint-solver twin to the realizer) or the **thiri-mcp + music21-mcp**
pair (Tier 1 #3–4 — short, closely related). Human picks.

As always: one peer (or one small related cluster, like the two MCP servers)
per chunk, notes written to `docs/research/0N-*.md`, landscape doc + AI-DIARY
updated at the end, human names the next chunk.
