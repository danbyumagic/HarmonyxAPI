# Chorale generation: Roman numerals → four-part MusicXML

**Status:** planning / discussion.
**Decision so far:** OCR is deferred (see ROADMAP). The near-term focus is
generating a four-part hymn from a Roman-numeral progression, reusing existing
part-writing logic rather than building a voicing engine from scratch.

## The idea (confirmed: yes, this makes sense)

This is the clean inverse of the analyzer:

```
key + Roman-numeral progression
        │
        ▼
  part-writing engine  ← reuse partwriter.com's voice-leading logic
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

## Why reuse partwriter.com

Part-writing (voicing an RN progression under SATB rules — no parallel
5ths/8ves, resolve the leading tone and chordal 7th, correct doubling, keep
common tones, respect vocal ranges, no crossing/overlap, proper spacing) is
the hard, fiddly core. partwriter.com already implements this in JavaScript,
so reusing it expedites the whole feature versus writing a constraint
solver/search from scratch.

### Reuse options (to decide)
1. **Port the JS logic to Python** — keeps the service single-language
   (FastAPI/Python), no extra runtime; cost is the porting effort and keeping
   it in sync with any upstream changes.
2. **Run the JS as-is via a Node sidecar** — call it over a small subprocess
   or HTTP boundary; keeps the original logic verbatim, adds a Node dependency
   to the deploy.

### Prerequisites / open questions
- **License & permission:** confirm partwriter.com's code is licensed for
  reuse (or get the author's permission) before porting or vendoring it.
- **Input surface:** what exactly does its engine expect (key, RN list,
  figured-bass details, soprano given or free)? That shapes our request model.
- **Determinism:** does it return one voicing or several? Do we want the
  "textbook" realization, or offer alternates?

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
1. Confirm license + inspect partwriter.com's input/output contract.
2. Decide port-to-Python vs. Node sidecar.
3. Wire `POST /generate`: progression → engine → SATB → MusicXML.
4. Round-trip and rule-violation checks as the eval.
5. Frontend panel + download.
