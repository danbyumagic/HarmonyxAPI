# Chorale generation: Roman numerals → four-part MusicXML

**Status:** planning / discussion.
**Decision so far:** OCR is deferred (see ROADMAP). The near-term focus is
generating a four-part hymn from a Roman-numeral progression. We will build our
**own** part-writing engine — a clean-room reimplementation of the standard
rules — rather than copying partwriter.com's code.

## The idea (confirmed: yes, this makes sense)

This is the clean inverse of the analyzer:

```
key + Roman-numeral progression
        │
        ▼
  part-writing engine  ← our own clean-room implementation of the rules
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

## Build our own engine (clean-room)

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

### Open questions
- **Input surface:** key, RN list, time signature — soprano given or free?
  (A given soprano constrains the search and matches how hymns are often set.)
- **Output:** one "textbook" realization, or offer a few alternates?

## Proposed shape in this project

- **New endpoint** `POST /generate` (or `/harmonize`):
  request = `{ key, progression: ["I", "V6", "vi", ...], time_signature?,
  soprano? }` → response = MusicXML (four parts) + optionally the same
  structured chord list the analyzer returns.
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
1. Write down the rule set + cost function (from theory sources), and decide
   soprano-given vs. free.
2. Build the Python voicing engine (candidate voicings + DP/search), with
   music21's `voiceLeading` for parallel/hidden-interval checks.
3. Wire `POST /generate`: progression → engine → SATB → MusicXML.
4. Round-trip and rule-violation checks as the eval.
5. Frontend panel + download.
