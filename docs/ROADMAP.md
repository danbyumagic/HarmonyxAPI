# Roadmap / discussion notes

Ideas under consideration. Nothing here is committed to yet — this is the
"things to discuss" list. Grouped into two tracks: sharpening the existing
analyzer, and adding chorale Roman-numeral realization + part-writing.

> **External classical × AI landscape (2026-07-21):** see
> [`CLASSICAL-AI-LANDSCAPE.md`](CLASSICAL-AI-LANDSCAPE.md) for GitHub peers
> (analysis, SATB, arrangement, LLM-theory patterns). Research bookmark only —
> not a committed build queue.

> **OCR / optical music recognition is deferred** (decided). Not a near-term
> goal; notes kept at the bottom for later.
>
> **Near-term direction:** generate a four-part MusicXML hymn from a
> Roman-numeral progression, reusing partwriter.com's part-writing logic.
> Detailed plan in [`chorale-generation.md`](chorale-generation.md).

---

## Track A — Harmonic analysis improvements

These target the concrete weak spots we saw on BWV 140/7 and "Nearer, My God,
to Thee."

### A1. Non-chord-tone (NCT) filtering — highest value
The single biggest source of junk. `chordify()` verticalizes passing tones,
neighbors, and suspensions into fake chords (`V42`, `quartal trichord`, `i5`,
`v7 "incomplete dominant-seventh"`). Fix by classifying each pitch in a slice
as chord tone vs. NCT from melodic + metric context (approached/left by step,
falls on a weak beat) and removing NCTs *before* labeling.
- Levers already in music21: `note.beatStrength`, voice-by-voice melodic
  context (keep SATB voices instead of only the chordified reduction).
- Bigger version: beat-synchronous segmentation + a small reduction step
  (Pardo–Birmingham / Temperley-style), or a Viterbi pass over chord
  candidates that trades off consonance against voice-leading smoothness.

### A2. Cadence detection via phrase segmentation
Today the heuristic fires "half" on every →V, mid-phrase included. Fix by
segmenting into phrases first, then only testing cadences at phrase ends.
- Chorales hand us the segmentation for free: **fermatas** mark phrase ends.
  Also usable: rests, phrase/slur marks, long-note + metric-downbeat cues.
- Then refine the label: PAC vs. IAC (soprano scale degree + root position),
  confirm leading-tone resolution, require a strong-beat arrival.

### A3. Modulation / tonicization tracking
V1 forces everything into one global key, so tonicizations show up as
chromatic chords (we saw `II` = V/V, `#ivø7`). Options:
- **Local/windowed key analysis** (sliding window) to surface key *regions*
  and report a sequence of local keys with confidence.
- **Secondary-dominant detection**: a major triad/dom7 a fifth above a
  diatonic chord, carrying the expected chromatic tone → label `V/x`, `V7/x`,
  `viio/x`. music21's `RomanNumeral` can express these directly.

### A4. Better key detection (eval is at 65%)
Most misses are relative major/minor confusion.
- Weight the Krumhansl profile with **cadential + first/last-chord evidence**
  (the tonic almost always opens and closes).
- **Ensemble the algorithms** music21 ships (Krumhansl, Aarden–Essen,
  Bellman–Budge, Temperley) and vote.
- Minor vs. relative major: check for a raised leading tone and the final
  chord's root/quality.

### A5. Cleaner chord labels & per-chord confidence
- Map ugly names (`quartal trichord`, `Perfect Fifth with octave doublings`)
  to clean labels; infer the intended harmony for incomplete chords from
  context (a bare fifth inside a I prolongation is `I`, not `i5`).
- Expose a **per-chord fit confidence** (how well the pitches match the
  assigned Roman numeral), and flag ambiguous slices for review.

### A6. The LLM *disambiguator* (the other AI angle from the brief)
We built the explainer; the disambiguator is the more interesting story. Feed
genuinely ambiguous slices (secondary dominants, modal mixture, chromatic
passing chords) with surrounding context to the model, and return **both** the
rule-based and the model answer so the user sees the disagreement. This pairs
naturally with A3 and A5 (only escalate the low-confidence slices).

### A7. Eval upgrade: Roman-numeral agreement, not just key
The brief's real target — "20 chorales with published analyses, report
agreement %." Move from key-only agreement to **chord-by-chord RN agreement**
against a labelled corpus (e.g. RomanText `.rntxt` sets such as *When-in-Rome*
/ BPS-FH), with alignment. That single number becomes the headline metric and
the regression gate.

---

## Track B — Chorale Roman numerals + part-writing

Expands the project from *analysis* to *analysis + generation*. Three
increasingly ambitious pieces; B1 is the natural first step and reuses the
SATB parsing we already have.

### B1. Part-writing rule checker (analysis) — most tractable
Given an SATB chorale, flag voice-leading violations:
parallel 5ths/8ves, direct/hidden 5ths & 8ves, voice crossing/overlap,
spacing > an octave between adjacent upper voices, unresolved leading tone,
unresolved chordal 7th, doubling errors.
- music21's `voiceLeading` module (`VoiceLeadingQuartet`) already detects
  parallels/hidden intervals — we build the rest on top.
- High pedagogical value, deterministic, explainable, and it gives another
  **objective metric** (violations per chorale) for the eval story.

### B2. Roman numerals → SATB realization (generation)
The inverse of the analyzer: given a key + RN progression, voice it as a
four-part chorale that obeys the rules.
- **Rule-based / search**: generate candidate voicings per chord, then pick a
  path with dynamic programming / CSP minimizing a cost function
  (voice-leading distance + rule penalties: no parallels, resolve LT and 7th,
  correct doubling, keep common tones, respect vocal ranges, no crossing).
  Deterministic, explainable, portfolio-friendly.
- Reuses B1's checker as the scoring/repair oracle.

### B3. Generate new chorales that follow the rules
- **Hybrid architecture (recommended):** an LLM proposes a Roman-numeral
  progression (style-aware, handles modulation), the B2 realizer voices it,
  and the B1 checker validates + repairs. Clean separation: the model handles
  taste, the deterministic layer guarantees correctness.
- **Pure ML alternative:** DeepBach / Coconet-style model. Stronger stylistic
  output, much heavier to train/host; better as a later "BachModel" tie-in
  than a v1.

> Naming note: "output choral Roman numerals" — confirm whether this means
> (a) *realize* a given RN progression into SATB (B2), (b) *analyze* an SATB
> chorale and output its RNs (already the analyzer, + B1 for rule-checking),
> or (c) both directions round-tripping. Likely both.

---

## Track C — Optical Music Recognition (OMR) — DEFERRED

> Deferred by decision — not a near-term goal. Kept for later reference.

Let users upload a **photo or PDF of sheet music** instead of MusicXML/MIDI.
Cleanly layered: OMR is a preprocessor that produces MusicXML, which then
feeds the existing `/analyze` pipeline unchanged.

### Engine options
- **oemer** — Python, pip-installable, deep-learning end-to-end, outputs
  MusicXML. Easiest to drop into the FastAPI service. Pulls in TF/torch +
  model weights (bigger image).
- **Audiveris** — mature open-source OMR (Java), best quality on printed
  scores, outputs MusicXML. Heavier to deploy (JVM), likely its own container.
- **Multimodal LLM vision** — flexible (and the only realistic path for
  handwritten), but OMR is a specialized task and accuracy on real scores is
  limited; better as a fallback than the primary engine.

### Shape
- New `POST /recognize` (image/PDF → MusicXML), then chain into `/analyze`;
  or let `/analyze` accept images and auto-run OMR first.
- **Human-in-the-loop is essential:** OMR errors cascade into garbage
  analysis, so render the recognized notes back (e.g. Verovio) for the user to
  confirm/correct before analyzing.
- Deployment: probably a **separate service/container** (heavy deps), talking
  to the analyzer over HTTP.

### Scope discipline
Start with **clean, printed, single-system** scores; defer handwritten and
dense orchestral scores. State it explicitly, same as the v1 harmony scope.

---

## Suggested phasing

1. **A1 (NCT filtering) + A2 (phrase-based cadences)** — biggest quality jump
   for the current analyzer, no new infra.
2. **A7 (RN-agreement eval)** — turns quality work into a measurable number.
3. **B1 (part-writing checker)** — high value, reuses SATB parsing, adds a
   second objective metric.
4. **A3/A4/A5** — modulation, key ensemble, clean labels + per-chord
   confidence — then **A6 (LLM disambiguator)** on the low-confidence slices.
5. **B2 → B3** — realization, then hybrid generation. Near-term, B2 is
   fast-tracked by reusing partwriter.com (see `chorale-generation.md`).
6. ~~Track C (OMR)~~ — deferred.

## Open questions to decide together
_Direction settled._ See the resolved notes below.

> Resolved: reuse question is settled — we build our own clean-room Python
> part-writing engine (the rules are standard theory, not IP). No license gate,
> no Node sidecar. See [`chorale-generation.md`](chorale-generation.md).
>
> Resolved: the **soprano is optional**. Free-soprano mode voices all four
> parts; given-soprano mode voices A/T/B beneath it after a chord-membership
> compatibility check that rejects incompatible notes with a clear message.
>
> Resolved: generation is **two layers** — (1) an idiomatic progression from a
> **functional-harmony grammar** (weighted transitions, cadence-aware; not
> random RNs), with per-chord **manual edit / lock + constrained regenerate**;
> (2) the clean-room realizer. Rule-based grammar is the default; an LLM
> proposer is an optional later alternative.
>
> Resolved: Harmonyx is a **multi-utility tool that does both directions** —
> analyze (score → RNs) *and* generate (RNs → score) — designed as inverses
> that round-trip and validate each other.
