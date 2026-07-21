# Chorale generation: Roman numerals → four-part MusicXML

**Status:** planning / discussion.
**Decision so far:** OCR is deferred (see ROADMAP). The near-term focus is
generating a four-part hymn from a Roman-numeral progression. We will build our
**own** part-writing engine — a clean-room reimplementation of the standard
rules — rather than copying partwriter.com's code.

## The idea (confirmed: yes, this makes sense)

This is the clean inverse of the analyzer, and it has **two layers**:

```
(optional) generate an idiomatic progression   ← Layer 1: functional-harmony grammar
        │        └─ user can edit / lock individual Roman numerals
        ▼
key + Roman-numeral progression (+ optional soprano)
        │
        ▼
  part-writing engine     ← Layer 2: our clean-room realizer
        │  (assign chord tones to S/A/T/B under the rules)
        ▼
  four-part SATB voicing
        │
        ▼
   MusicXML four-part hymn   ← round-trips straight back into /analyze
```

The analyzer already goes **score → Roman numerals**. This adds
**Roman numerals → score**, so the two directions round-trip: generate a
hymn from a progression, then analyze it back and confirm it reproduces the
input RNs (a built-in correctness check + eval signal).

## Layer 1 — idiomatic progression generation (not random RNs)

Random generation should be **governed by tonal harmony, not uniform chance** —
not every Roman-numeral combination sounds good, so the generator emits
*functional* progressions rather than arbitrary sequences.

- **Chords have functions:** Tonic (I, vi, iii) · Predominant/Subdominant
  (IV, ii, ii⁶) · Dominant (V, V7, viio). Idiomatic flow is **T → PD → D → T**.
- **Encode the conventions as a weighted transition grammar** (Markov-style
  transition table seeded from the norms): `ii → V`, `V → I` (or `V → vi`
  deceptive), cadential ⁶⁴ → V, IV → V or I; down-weight/forbid retrogressions
  like `V → IV`. Seeded randomness gives variety while staying musical.
- **Cadence-aware:** aim phrase ends at real cadences (PAC/HC), not wherever
  the chain lands.
- The **default generator is this rule-based functional grammar.** An LLM
  proposer stays an *optional* alternative later (style/modulation), not the
  core.

### Manual editing / locking
The generated progression is an **editable list of Roman numerals**:
- Change any chord by hand, or **lock** specific chords and regenerate the rest
  around them (constrained generation honoring the locked slots).
- After an edit, re-realize the voicing (and re-run the soprano compatibility
  check if a soprano is set).

## Layer 2 — the realizer (build our own engine, clean-room)

Part-writing (voicing an RN progression under SATB rules — no parallel
5ths/8ves, resolve the leading tone and chordal 7th, correct doubling, keep
common tones, respect vocal ranges, no crossing/overlap, proper spacing) is the
hard, fiddly core — but the rules themselves are **standard music theory, not
anyone's intellectual property.** partwriter.com implements them in JS; we will
**not** copy its code. Instead:

- **Clean-room reimplementation:** implement the rules from first principles
  (any harmony textbook), in Python, in our own service.
- **Don't copy** partwriter.com's source, code structure, or distinctive
  implementation details. Studying observable behavior to understand the rules
  is fine; the rules are public knowledge. (If poking at the site
  programmatically, check its Terms of Service — but we don't need to; the
  rules are well documented.)
- **Build on music21:** its `voiceLeading` module already detects
  parallels/hidden intervals, so the checker half is partly done for us.

This removes the earlier license and port-vs-sidecar questions — it's a
single-language Python engine, no extra runtime.

### The engine, concretely
Generate candidate voicings per chord, then choose a path with dynamic
programming / search that minimizes a cost function:
voice-leading distance + rule penalties (parallels, unresolved LT/7th, bad
doubling, spacing, crossing). This is a well-trodden approach and stays
deterministic and explainable.

### Input surface (decided)
- **key, RN list, time signature** — required.
- **Soprano: optional.**
  - *Not provided* → the engine chooses all four voices freely, soprano
    included.
  - *Provided* → the engine voices alto/tenor/bass beneath the given soprano,
    but only after a **compatibility check** (below).

### Soprano compatibility check (when a soprano is provided)
Before voicing, verify each soprano note is a legal tone of the chord its
Roman numeral implies (root / third / fifth / seventh). Reuses the same
chord-membership logic the analyzer already relies on.
- On mismatch, **reject with a clear message** — e.g. `beat 3: soprano G4 is
  not a chord tone of V (chord tones: B, D, F)` — rather than forcing a bad
  voicing. (Later we could optionally allow flagged non-chord tones like
  passing/neighbor notes, but v1 requires chord tones.)
- Return the check result in the response so the frontend can highlight the
  offending beat.

### Open questions
- **Output:** one "textbook" realization, or offer a few alternates?

## Proposed shape in this project

- **`POST /progression`** (Layer 1, optional): request =
  `{ key, length?, locked?: {index: "V", ...}, cadence?: "PAC" }` → response =
  an idiomatic Roman-numeral list. Locked slots are honored; the rest is
  generated around them.
- **`POST /generate`** (Layer 2): request =
  `{ key, progression: ["I", "V6", "vi", ...], time_signature?, soprano? }`
  (soprano optional) → response = MusicXML (four parts) + optionally the same
  structured chord list the analyzer returns. If a soprano is given and fails
  the compatibility check, return a 422 with the offending beat(s).
- A caller can chain them (generate a progression, edit it, then realize) or go
  straight to `/generate` with a hand-written progression.
- **Reuse the part-writing engine** (ported or sidecar) to produce the SATB
  voicing.
- **Emit MusicXML** via music21 (build a 4-voice `Score`, write to MusicXML) —
  we already depend on music21, and it round-trips cleanly into `/analyze`.
- **Frontend:** a second panel on the existing page — type/pick a progression,
  get back a rendered hymn + downloadable MusicXML.

## Correctness / eval tie-in
- **Round-trip check:** generate → analyze → compare the recovered Roman
  numerals to the input. High agreement = the generator and analyzer agree.
- **Rule-violation count:** run the generated hymn through a part-writing
  checker (Track B1 in ROADMAP; music21's `voiceLeading` module) and report
  violations — an objective quality number, same pattern as the analysis eval.

## Phasing
1. **Layer 2 first** (it's the reusable core). Write the rule set + cost
   function, build the Python voicing engine (candidate voicings + DP/search)
   with music21's `voiceLeading` for parallel/hidden checks. Support free- and
   given-soprano modes; add the soprano compatibility check. Wire
   `POST /generate`.
2. **Layer 1**: the functional-harmony progression grammar (weighted transition
   table, cadence-aware) + locking/constrained regeneration. Wire
   `POST /progression`.
3. Round-trip and rule-violation checks as the eval.
4. Frontend panel: generate progression → edit/lock chords → realize → render +
   download.
5. (Later, optional) LLM progression proposer as an alternative to the grammar.
