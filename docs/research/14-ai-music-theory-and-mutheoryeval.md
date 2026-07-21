# Research #14 — ai-music-theory + MuTheoryEval

- **ai-music-theory**: `music-comp/ai-music-theory` — a Rust MCP server
  serving a machine-readable music-theory knowledge graph. 1★, CC0-1.0.
- **music-comp-mt** (`music-comp/mt-rs`, published as the `music-comp-mt`
  crate): the underlying computation library ai-music-theory's MCP tools
  call into for notes/scales/chords/intervals — read alongside it since it's
  a direct dependency, not an independent peer.
- **MuTheoryEval**: `thevertexlab/MuTheoryEval` — an LLM music-theory-
  knowledge eval *runner* (aggregates existing benchmarks + a live
  leaderboard), not a benchmark itself. 0★, MIT.

Read: both READMEs in full; `ai-music-theory`'s repo tree (`INDEX.md`,
`SCOPE.md`, `SOURCES.md` file listing, `mcp-server/crates` layout);
`mt-rs`'s README (confirmed it's the fork of `ozankasikci/rust-music-theory`
that backs the MCP compute tools) and its `Cargo.toml` dependency link;
MuTheoryEval's live leaderboard `docs/data.json` (60 result cells across 15
models × up to 6 benchmarks) computed into a per-model summary. Did not
clone/build the Rust MCP server or run any eval locally — both are
config/data-heavy rather than architecture-heavy, so a read of the docs and
data was the efficient chunk here, same call as research #06/#11's data-only
treatment.

## 1. ai-music-theory: what it is

Not a competing analyzer — a **grounding knowledge base**, built by
converting 14 canonical music-theory textbooks (Tymoczko, Lewin, Cohn,
Caplin, Straus, Schoenberg, Persichetti, Laitz, and others — spanning
fundamentals through neo-Riemannian/transformational/post-tonal theory) into
4,315 atomic "concept cards," synthesized into a typed graph (3,742 nodes,
18,618 typed edges: `prerequisite`/`relates_to`/`extends`/`contrasts_with`),
served over MCP with three retrieval modes (Tantivy full-text BM25, a
memory-mapped rkyv-cached graph for traversal/prerequisites/bridge-detection,
and LanceDB+fastembed semantic/hybrid search) — 53 MCP tools total, including
a `mt_directory` tool that returns a self-describing "call this first"
manifest.

Nine of the 53 tools (`get_scale_notes`, `get_chord_notes`, `get_interval`,
`transpose`, `get_diatonic_chords`, `identify_chord`, `identify_scale`,
`check_enharmonic`, `analyze_roman_numerals`) are **computation**, not
retrieval — delegated to a separate crate, `music-comp-mt`, which turns out
to be the same author's fork of `ozankasikci/rust-music-theory`, now grown
into a standalone library+CLI (96% test coverage, published on crates.io,
"every fact verified against the 4,315 concept cards"). Its
`analyze_roman_numerals` tool is a **single-chord, given-a-key lookup**
(same shape as `Chord::identify` — take a set of pitches, or a chord symbol,
and a key, return the RN) — there is no score ingestion, no sequential
context-tracking, no key-finding, no salami-slicing. This is a materially
different problem than what Harmonyx's `/analyze` does (MusicXML/MIDI → key
+ RN progression + cadences over a whole piece) — it's closer to a
calculator than an analyzer.

There's also a 12-tool **Open Tone Harmony (OTH)** module — a mathematical
voice-leading-geometry system (228 quintal/quartal chords in a [6,8] metric
space, 52 modes, fiber-bundle geometry) that appears to be original research
by this project's author rather than textbook-sourced, exposed with the same
tool-per-operation pattern as the rest. Not classical-tradition RN theory,
and out of scope for Harmonyx, but notable as an example of a from-scratch
music-theory *system* built with the same graph+MCP infrastructure as the
textbook content.

## 2. MuTheoryEval: what it is

A **benchmark aggregator + leaderboard runner**, not a novel benchmark: it
wraps six existing published benchmarks (MusicTheoryBench/ChatMusician —
text, knowledge+reasoning over ABC notation; ZIQI-Eval — text, 10
categories/56 subcategories; SSMR-Bench — symbolic ABC, 9 task types
incl. rhythm/chord/interval/scale; WildScore — VLM score-image reasoning;
MuChoMusic and CMI-Bench — audio-LM), runs a configurable roster of ~20
current commercial models (GPT-5.4 family, Claude Opus/Sonnet/Haiku 4.x,
Gemini 3.1 family, DeepSeek, GLM-5, Qwen3, Llama-4) against each in a
reproducible fixed-seed "lite" mode, and publishes a weighted aggregate
score to a static leaderboard site. No Roman-numeral-analysis-specific
benchmark is included — theory coverage is general (scales, intervals,
chords, ABC-notation reasoning), not RN/functional-harmony specific.

Pulling the live `docs/data.json` (60 result cells) and aggregating by model
for the two weighted text benchmarks (MusicTheoryBench + ZIQI-Eval):

| Model | MusicTheoryBench | ZIQI-Eval |
|---|---|---|
| gemini-3.1-flash | **.722** | .884 |
| gemini-3.1-flash-minimal | .722 | .886 |
| claude-sonnet-4-6 (thinking 8k) | .711 | .866 |
| claude-opus-4-6 | .676 | .868 |
| gpt-5.4 | .632 | .820 |
| claude-sonnet-4-6 | .624 | .850 |
| claude-haiku-4-5 | .589 | .754 |
| deepseek-reasoner | .417 (lowest) | .808 |

Range is roughly **42-72%** on MusicTheoryBench's knowledge+reasoning MCQ
task across current frontier/mid-tier models — a useful, if indirect,
sanity-check number for "how good are today's general LLMs at music theory
out of the box, with no grounding." Every model scored well below 100% and
there's a wide spread (deepseek-reasoner is a clear outlier low, thinking
variants of the same base model don't consistently help — `claude-sonnet-
4-6-xt8k` roughly matches or beats plain `claude-sonnet-4-6` but the gap
isn't dramatic).

## 3. Comparison to Harmonyx

Neither repo overlaps with Harmonyx's current code:

- **ai-music-theory** is a knowledge/grounding layer for an LLM to *consult*,
  not an analyzer or generator — directly relevant only if/when Harmonyx
  ever adds an **LLM-facing explainer/tutor surface** (mentioned as the
  gating condition in `docs/RESEARCH-QUEUE.md` item 7) that needs to ground
  claims about music theory, trace prerequisites for a concept, or answer
  "why is this chord X" with citations back to a textbook. That's not on the
  open queue today (Q1 LLM progression L4+ is about RN *generation*
  proposals, not theory Q&A).
- **MuTheoryEval** is relevant only as a **pre-built eval methodology** if
  Harmonyx's own L4 LLM client (not yet started) is ever benchmarked for
  general theory competence before being trusted to propose RN progressions
  — i.e. it answers "is this model good at music theory at all" as a
  prerequisite check, distinct from Harmonyx's own domain-specific L2
  validator (`app/generation/validate.py`) which checks whether a specific
  *proposed progression* is valid, not whether the model that proposed it
  understands theory in general.
- Neither touches Roman-numeral-sequence analysis over a real score the way
  Harmonyx's analyzer, When-in-Rome (#06), AugmentedNet (#11), or RNBert
  (#13) do — `analyze_roman_numerals` here is chord-level, not corpus/score-
  level, so it doesn't add a third accuracy-ceiling data point the way #11
  and #13 did.

## Steal / don't-steal

**Steal (ideas only):**
- The **`mt_directory`/self-describing-tool-registry pattern** (a single
  MCP tool that returns a live manifest of every other tool with "use-when"
  guidance) — a clean answer to "how does an LLM client discover which of
  N tools to call," worth remembering alongside research #10's MCP
  architecture notes if Harmonyx ever exposes its own tools over MCP.
- MuTheoryEval's **weighted-aggregate-of-existing-benchmarks** design (don't
  build a new benchmark, wrap several with a fixed-seed reproducible "lite"
  mode and cost estimation before running) — a reusable pattern *if* L4's
  chosen LLM ever needs a documented "is this model competent enough"
  pre-check, cheaper than inventing a bespoke Harmonyx eval from scratch.
- The concept-card + typed-graph-edges (`prerequisite`/`relates_to`/
  `extends`/`contrasts_with`) structuring idea, if Harmonyx's own docs
  (`PARTWRITING-RULES.md`, `RICH-GRAMMAR-SPEC.md`) ever need to become
  queryable rather than just readable markdown — speculative, not needed
  today.

**Don't steal:**
- The Rust/Fabryk MCP server stack itself, the 14-textbook content corpus,
  or the OTH mathematical system — no product need for a general theory
  knowledge base; Harmonyx's rule depth (`rules.py`, `PARTWRITING-RULES.md`)
  is deliberately narrower and already locked to specific textbook
  conventions (Aldwell/Schachter-style SATB), not a broad multi-tradition
  graph.
- MuTheoryEval's specific benchmark roster/model list as a hard dependency —
  useful as a template, not something to vendor; if a pre-check is ever
  built it should target Harmonyx's own L4 use case (RN-progression
  proposal quality) rather than general theory trivia.

## Open questions (not investigated further)

- Whether `music-comp-mt`'s enharmonic-aware chord/scale identification
  (letter-name-correct, not just pitch-class) has any reusable ideas for
  Harmonyx's own MusicXML pitch-spelling handling — not compared line-by-
  line; flagged only as a "look here if pitch-spelling bugs ever come up,"
  not urgent.
- Whether any of MuTheoryEval's six wrapped benchmarks (especially SSMR-
  Bench, which tests rhythm/chord/interval/scale identification over ABC
  notation) could be repurposed wholesale as an analyzer-adjacent eval set —
  not evaluated for licensing/relevance; would need its own chunk if ever
  pursued.

This closes Tier 2 of `docs/RESEARCH-QUEUE.md` in full (#5 JJazzLab, #6
rnbert/muMoE-RNBERT, #7 ai-music-theory+MuTheoryEval all done). Remaining
queue is Tier 3 only: #8 diatone, #9 mcp-score, #10 Humdrum/**kern tooling.
