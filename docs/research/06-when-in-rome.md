# Research note: When-in-Rome (MarkGotham)

**Date:** 2026-07-21
**Repo:** https://github.com/MarkGotham/When-in-Rome
**Author:** Mark Gotham, Gianluca Micchi, Néstor Nápoles López, Malcolm Sailor
(and contributors)
**Status:** Tier peer #6 — meta-corpus of functional harmonic analyses (not a
tool/product; a data + light-tooling repo)
**Source:** README, `syntax.md`, directory scan of `Corpus/` and `Anthology/`,
`Code/romanUmpire.py` (1261 lines, read structure/docstrings), `Code/anthology.py`
(716 lines, skimmed). Cited paper: Gotham et al., "When in Rome: A Meta-corpus
of Functional Harmony", TISMIR 6(1), 2023.
**Meta:** 85★, actively maintained (last push 2026-07-08), CC BY-SA 4.0 for
new content; converted sub-corpora keep their original licences (noted per
folder). ~2,000 analyses of ~1,500 distinct works.

---

## 1. What it is

Not an app or a model — a **meta-corpus**: ~1,300 `analysis.txt` files (plain
RomanText) plus, for most, a `score.mxl` (or `remote.json` pointer) and an
`analysis_automatic.rntxt` (AugmentedNet's ML output on the same score), laid
out as `<genre>/<composer>/<set>/<movement>/<files>`. It aggregates and
normalizes several external corpora (DCML's ABC/Mozart-sonatas/romantic-piano
corpora, TAVERN, Haydn Op.20, BPS-FH, Tymoczko's TAOM Monteverdi + **371 Bach
chorales**) into one consistent RomanText encoding, plus new analyses
(Well-Tempered Clavier I preludes, ground basses, OpenScore-Lieder songs
including complete *Winterreise*/*Schwanengesang*/*Dichterliebe*).

`Code/` provides thin tooling on top, built on **music21** (which Harmonyx
already depends on): `romanUmpire.py` (an analysis-vs-score "spell checker"
producing feedback + a match-quality score), `anthology.py` (mine the corpus
for instances of specific chords/progressions, e.g. the augmented-sixth and
fifth-progression histograms in the README), and `Pitch_profiles/` (pitch-class
distribution/feature extraction per chord or key segment).

**Vs Harmonyx:** no overlap in product surface (this ships no API, no
generation, no realizer) — the overlap is entirely as a **data source** and
as a **reference implementation of the RomanText format** that Harmonyx's own
RN vocabulary already descends from via music21's `roman` module.

---

## 2. RomanText syntax — direct validation of Harmonyx's RN vocabulary

`syntax.md` is the clearest single spec of RomanText I've read, and it maps
almost 1:1 onto what `app/generation/grammar.py` / `chords.py` already emit,
which is worth stating explicitly since it's independent confirmation rather
than something to copy:

- `key: RN` header syntax (`G: V42`), continuation without repeating key,
  tonicization via `/` (`viio/V`) — matches Harmonyx's secondary-dominant
  syntax from Q3b.
- `Cad64` / `I64` for the cadential six-four — Harmonyx already uses `Cad64`
  (Q3a). Confirms the choice rather than suggesting a change.
- Augmented sixths as named shorthands: `It6`, `Fr43`, `Ger65` (no bare `Gr`).
  Harmonyx doesn't have augmented-sixth chords yet (not in Q3a–c or
  `PARTWRITING-RULES.md` §9b) — this is a concrete, already-battle-tested
  syntax to adopt if/when that's scoped, rather than inventing one.
- `[add9]` / `[no3]` bracket syntax for altered/added tones, and the
  explicit guidance to prefer `V[add4][no3]` over `V54` for suspensions
  (both accepted, but the bracket form is "more tested, more flexible").
  Harmonyx doesn't do suspension notation yet either — same story.
- Pivot-chord notation `I || f: III` (prevailing-key RN, then `||`, then new
  key:RN) — a clean precedent if Harmonyx ever needs modulating progressions
  (currently postponed per `LLM-PROGRESSION-SPEC.md` open question #4).
- The minor-mode 6^/7^ "quality vs cautionary vs sharp/raised vs
  flat/lowered" table is the single best explanation I've seen of a subtle
  RN ambiguity that any analyzer/generator eventually has to pick a
  convention for. Harmonyx should note which convention `music21`'s
  `roman.RomanNumeral` (and thus Harmonyx) actually implements by default —
  worth a one-line doc note in `PARTWRITING-RULES.md` if this ever causes a
  reported disagreement, not urgent now.

Net: no syntax changes needed for current scope; this is a ready-made spec to
point to if augmented sixths, suspensions, or modulating progressions ever
get scoped.

---

## 3. Corpus as L1 few-shot expansion (`data/progression_corpus.json`)

Today's L1 corpus is **40 hand-written entries** (`data/progression_corpus.json`,
per `docs/LLM-PROGRESSION-SPEC.md` L1 status). When-in-Rome's **371 Bach
chorales** (`Corpus/Early_Choral/Bach,_Johann_Sebastian/Chorales/`, one
`analysis.txt` + `score.mxl` per chorale) are the obvious real-corpus
complement:

- **Format is close but not identical** to Harmonyx's corpus schema. WiR
  entries are whole-piece RomanText transcriptions (`m1 D: I b3 IV b4
  viio6`, spanning dozens of measures with modulations, cross-references
  like `m5-6 = m3-4`, editorial `Note:` lines); Harmonyx's corpus entries are
  short curated phrases (`["I", "ii6", "V", "I"]`) tagged with `spice` /
  `cadence` / `student_safe` metadata for retrieval. **Any import would need
  a segmentation + tagging step** (extract short phrase windows around
  cadences, classify cadence type, estimate a spice level) — not a drop-in
  file swap. This is new pipeline work, not a corpus-file copy.
- **Licence note:** the Bach chorale analyses here derive from Tymoczko's
  TAOM supplementary materials (see README §"Corpora originating elsewhere"),
  distributed under this repo's CC BY-SA 4.0 for the *converted* form. If
  entries are ever imported into `data/progression_corpus.json`, the
  `source` field convention already used there (`{"type", "ref", "license"}`)
  needs a real `type` (e.g. `"when_in_rome_bach_chorale"`) and the correct
  licence/attribution instead of `"hand_template"` / `"original"` — flag
  this if L1 expansion is ever scoped so entries aren't mis-labeled as
  original work.
- **Not required for L4.** `LLM-PROGRESSION-SPEC.md` L1 is marked done;
  this is a *quality/diversity* upgrade to few-shot retrieval, useful whenever
  L1 gets revisited, not a blocker for L4 (next build chunk per the open
  queue).

---

## 4. `romanUmpire.py` — relevant to both M4 and analyzer eval (A7), not a port target

`ScoreAndAnalysis` (the umpire's core class) pairs each RN's time-span with
the score's "vertical slices" in that span and scores agreement on: (a)
proportion of notes matching the asserted chord (length-weighted), (b) metrical
position plausibility of chord changes, (c) whether the asserted bass/inversion
note is actually present. It emits a feedback text file and can also render
the score with problems flagged in notation.

Two different, non-overlapping relevances already on Harmonyx's open queue:

- **M4 `POST /check`** (Q2): this is analysis-vs-*score* matching (does this
  RN correctly describe this passage of a score a human already analyzed),
  which is a different problem from M4's part-writing violation check (does
  this SATB realization obey voice-leading rules) — **not the same thing as
  PartWise (#03)**, which M4 is actually blueprinted on. Don't conflate them.
- **Analyzer A7 (RN-agreement eval)**, per `docs/START-HERE.md` Q4: this
  *is* directly relevant — `romanUmpire`'s slice-matching approach is a
  ready-made technique for scoring Harmonyx's own analyzer output against a
  human ground truth (e.g. run the umpire's matching logic, or something
  architecturally similar, over Harmonyx analyzer RNs vs. WiR's
  `analysis.txt` ground truth on the same scores) — useful the next time A7
  is the named chunk, not before.

No code here is proposed for vendoring; it's CC BY-SA (share-alike) and
tightly coupled to WiR's own file layout — reimplement the *matching idea*
independently if/when A7 is scoped, don't import the module.

---

## 5. Steal / don't-steal

**Steal (ideas, not code):**
- RomanText syntax precedents for augmented sixths, suspension brackets,
  and pivot-chord notation, if those features are ever scoped (§2).
- Slice-based RN-vs-score agreement scoring as a technique for analyzer eval
  A7 (§4) — reimplement independently, don't vendor (CC BY-SA + coupled to
  WiR's layout).
- The 371 Bach chorales + their aligned scores as a candidate real-corpus
  source for L1 few-shot expansion, if/when L1 is revisited (§3).

**Don't steal:**
- Don't vendor `romanUmpire.py` or `anthology.py` directly — CC BY-SA
  share-alike licensing and tight coupling to WiR's corpus directory
  structure make a clean reuse impractical; the underlying techniques are
  simple enough to reimplement against Harmonyx's own data shapes.
- Don't treat this as a corpus to bulk-import wholesale — segmentation,
  spice/cadence tagging, and correct per-entry licence attribution are all
  required first (§3); it's a source to mine, not a drop-in file.

## 6. Open questions

- If augmented sixths get scoped as a grammar feature, should Harmonyx match
  WiR's `It6`/`Fr43`/`Ger65` shorthand exactly (interop with any future
  RomanText import/export), or does the existing `spice`/`style` system want
  a different surface?
- Is A7 (RN-agreement eval) or Q1 (LLM L4) the better next priority — WiR
  makes A7 more tractable than before (real ground-truth analyses + a scoring
  technique to reimplement) but doesn't change L4's status as already-spec'd
  and shovel-ready.
