# Research note: Resonance (will825/resonance)

**Date:** 2026-07-21  
**Repo:** https://github.com/will825/resonance  
**Live:** https://resonance-beige-omega.vercel.app  
**Status:** Tier S deep-dive #1 — architecture peer for Harmonyx L4+  
**Source:** README + full read of `lib/ai/*`, `lib/theory/*` core, API route, tests.

---

## 1. What it is

Producer-facing **AI chord-progression generator**:

- User: vibe text + key + mode (+ optional bar count).
- Output: JSON **progression of Roman numerals** + tempo/feel/voicing/arpeggio.
- Client: realizes to voice-led MIDI notes, Tone.js playback, MIDI export.

**Product framing differs from Harmonyx:** pop/jazz/lofi/cinematic for DAWs, not
SATB hymn / classical part-writing. **Architecture framing matches:** LLM never
emits notes; theory engine is source of truth.

---

## 2. Stack

| Layer | Choice |
|-------|--------|
| App | Next.js 14 App Router, React, Tailwind, TypeScript strict |
| LLM | Groq OpenAI-compatible API (`llama-3.3-70b-versatile`, fallback `llama-3.1-8b-instant`) |
| Schema | Zod on request + model output |
| Theory | Hand-written formulas + `tonal` (cross-checked in tests) |
| Audio | Tone.js + `@tonejs/midi` |
| Tests | Vitest (`__tests__/theory.test.ts` is substantial) |

No music21, no MusicXML, no SATB, no parallel-fifths rules.

---

## 3. End-to-end pipeline

```
POST /api/generate  { vibe, key, mode, bars? }
        │
        ├─ zod generateRequestSchema
        ├─ per-IP rate limit (20 AI calls / hour → fallback)
        │
        ▼
  generateSpec (Groq)
    system: "ONLY JSON, romans only, no note names"
    response_format: json_object
    temperature 0.8
    zod progressionSpecSchema
    force user's key (model may drift mode/tempo)
    1 retry on invalid JSON
        │
   ┌────┴──── on MissingKey | 429 | error | bad request
   ▼
  deterministicFallback(key, mode, vibe, bars)
    pickTemplate by tag match on vibe text
        │
        ▼
  Response always HTTP 200:
  { spec: ProgressionSpec, source: "ai" | "fallback", reason? }
        │
        ▼ (client)
  realizeProgression(spec)
    resolveRoman each chord → optimizeVoiceLeading → MIDI
```

**Always return a usable progression** — even invalid request falls back to a
default template rather than 4xx. UI badge shows AI vs fallback.

---

## 4. LLM contract (steal-worthy for L4)

### 4.1 Output schema (Zod)

```ts
// Chord
{ roman: string, bars: 1..8 }

// Spec
{
  key, mode, tempo: 40..220,
  feel: string,
  voicingStyle: "close" | "open" | "drop2",
  arpeggio: "none" | "up" | "down" | "updown",
  progression: Chord[],  // 2..16
  notes?: string
}
```

Request is thinner: `{ vibe, key, mode, bars? }` — LLM invents tempo/voicing/feel.

### 4.2 System prompt rules (summary)

- Chords as **Roman numerals with explicit extensions** (`ii7`, `V9`, `Imaj7`,
  `bVII`, `V/vi`).
- Case = quality convention; `°` dim, `+` aug, `ø7` half-dim.
- Mostly diatonic; borrowed / secondary when vibe fits.
- Minor: prefer major/dominant V for cadences.
- **No note names, prose, or markdown** — JSON only.
- Few-shot: 2 JSON examples (lofi major-7 turnaround; cinematic minor).

### 4.3 Failure handling

| Condition | Behavior |
|-----------|----------|
| No `GROQ_API_KEY` | Fallback, `reason: no-api-key` |
| Groq 429 | Fallback, `rate-limited` |
| Invalid JSON / schema (after 1 retry) | Fallback |
| IP over AI quota | Fallback (still 200) |
| Invalid request body | Fallback with defaults |

No separate **theory validator** on the RN *sequence* (no forbidden
transitions, cadence contract). Validity = “each roman parses + realizes.”
Harmonyx L2 is stricter and classical-specific.

---

## 5. Deterministic fallback ≈ Harmonyx L1 corpus

`lib/theory/progressions.ts` — ~16 curated templates:

- Pop (axis, sensitive, 50s)
- Jazz (ii–V–I, rhythm, 1–6–2–5)
- Blues (12-bar)
- Lofi / neo-soul
- Cinematic minor / Andalusian
- Modal (dorian, mixolydian, lydian)

**Selection:** score vibe text against `tags[]` (+ mode tie-break). Not
embedding search — simple `includes(tag)`.

Harmonyx analogue: `data/progression_corpus.json` + `corpus.py` (few-shot for
LLM) and `grammar.py` (default offline propose). Resonance folds “offline
propose” into **template pick by vibe**, not a weighted functional grammar.

---

## 6. Theory engine (what they realize)

| Module | Role |
|--------|------|
| `scales.ts` | Modes/scales → pitch classes |
| `chords.ts` | Interval formulas (triads through 13ths, sus, etc.) |
| `romanNumerals.ts` | Parse RN, case, alterations, secondary `V/x`, resolve root+quality |
| `voicing.ts` | close / open / drop2; greedy voice-leading optimizer |
| `realize.ts` | Spec → `RealizedChord[]` (MIDI note lists) |
| `complexity.ts` | Dial: simple (triads) / rich (7ths) / lush (9ths) |
| `analyze.ts` | Teaching labels: tonic/subdom/dom, borrowed, secondary |
| `suggest.ts` | Next-chord suggestions (diatonic / borrowed / secondary) |
| `melody.ts` | Deterministic chord-tone melody over realized chords |
| `rhythm.ts` | Comping patterns (block, charleston, …) |

### Roman parser highlights

- Supports `bVII`, `#…`, extensions, half-dim spellings.
- Secondary: bare `V/vi` → default **dom7** of target (applied in target’s
  major key).
- Case overrides diatonic quality when needed (uppercase `V` in minor → major).

### Voice-leading optimizer

- **Not SATB.** Block voicings (close/open/drop2) across octaves 2–5.
- Greedy: each chord picks candidate minimizing nearest-note distance to
  previous (symmetric score).
- Tests assert optimized movement **&lt;** naive root position; pitch-class set
  preserved.

**Vs Harmonyx:** Harmonyx DP over SATB with hard part-writing violations;
Resonance soft-minimizes motion with no parallel-5th / range / doubling rules.

---

## 7. Tests worth emulating

`__tests__/theory.test.ts` covers:

- Chord formula ↔ symbols
- RN resolution: diatonic, harmonic-minor V, borrowed `bVII`, secondaries, modes
- Complexity dial round-trips through resolver
- Functional analysis tags
- Suggest-chords groups + “every suggestion resolves”
- Voice-leading reduces movement
- Melody: deterministic, chord-tone downbeats, limited leaps
- Full realize integration (lofi turnaround → Cmaj7 Am7 … G7)

**Gap vs Harmonyx:** no locked “must never parallel fifths” fixtures; no corpus
round-trip through a realizer that can fail.

---

## 8. Side-by-side with Harmonyx L4 plan

| Concern | Resonance | Harmonyx (spec / code) |
|---------|-----------|-------------------------|
| LLM emits | RN + bars + performance metadata | RN list only (planned) |
| Schema validation | Zod on full spec | Planned structured JSON |
| Theory validation | Parse/realize only | **L2** forbidden transitions, cadence, realizability |
| Fixer | None (fallback template replaces whole result) | **L3** minimal-edit suggestions |
| Offline default | Tagged template library | Weighted **grammar** (+ corpus for few-shot) |
| Realizer | Jazz/pop block voicing + VL optimizer | SATB DP + hard rules + MusicXML |
| Source flag | `source: "ai" \| "fallback"` | Planned `source: "llm" \| "grammar"` (L5) |
| Rate limit | Per-IP → fallback | Not designed yet |
| Always-200 UX | Yes | Can learn: degrade to grammar, don’t hard-fail propose |
| Few-shot | 2 static examples in system prompt | Corpus retrieval 2–5 examples (L1 done) |
| Model | Groq Llama 3.3 70B | Spec: Anthropic-class API (same as explainer) |
| Pedagogy extras | analyze + suggest + complexity dial | Explainer on analyze; generate UI locks |

---

## 9. Concrete takeaways for Harmonyx (do not implement until tasked)

### Steal for L4 client

1. **`source` + `reason` on every propose response** — UI badge, debug, eval.
2. **JSON mode + schema parse + one correction retry**, then offline path.
3. **Force user key** (and key/mode/cadence constraints) after model returns.
4. **Never 5xx empty propose** — grammar fallback is the product, not an error.
5. **System prompt shape:** schema text + short house rules + 2–3 few-shot
   JSON examples (ours should be classical cadences from corpus).
6. **Separate modules:** `schema` / `client` / `fallback` / route — easy to test
   without network.

### Do *not* copy blindly

1. Their fallback is **genre templates**, not functional grammar — weaker for
   classical homework.
2. No **transition validator** — insufficient for Theory-I / hymn rules.
3. Voice-leading optimizer ≠ part-writing; don’t replace `realize.py`.
4. Pop RN dialect (`Imaj7`, bars as duration) ≠ our inversion/Cad64 figures.
5. “Always 200 on bad request” is producer-UX; API purity may prefer 422 +
   optional fallback flag.

### Ideas to park for later product surface

- **Complexity dial** (triad / 7th / 9th) parallels `spice` / style.
- **Functional analysis layer** on propose (`analyze.ts`) for teaching UI.
- **suggest next chord** for locked-RN editing in Generate tab.
- **Melody-from-harmony** deterministic layer (opposite of melody harmonize).

---

## 10. Risk / quality notes

- Repo is young (created 2026-06, 0★ at scan) — quality is in the design, not
  community validation.
- In-memory IP rate limit is coarse on serverless (per-instance).
- LLM can still invent nonsense romans; they only fail if **parse** throws —
  fallback is whole-spec replacement, not surgical fix (L3 is stronger).
- Secondary / borrowed coverage is solid for producer use; classical figures
  (`I64`, `V65`, `vii°6`) not the focus.

---

## 11. Links back into our docs

| Our doc | Connection |
|---------|------------|
| `docs/LLM-PROGRESSION-SPEC.md` | L4–L5 design; use §9 takeaways when implementing |
| `docs/CLASSICAL-AI-LANDSCAPE.md` | Tier S entry |
| `app/generation/validate.py` | Stricter than Resonance |
| `app/generation/fix.py` | Surgical alternative to full template swap |
| `app/generation/grammar.py` | Better offline default than vibe-tags alone |
| `data/progression_corpus.json` | Better few-shot than 2 static examples |

---

## 12. Open questions (for human)

1. For L4, prefer Groq-style cheap JSON models or stick to Anthropic like
   explainer?
2. Should propose UI show **AI vs grammar** badge like Resonance?
3. On LLM schema fail: full grammar replace (Resonance) or L3 minimal fix
   first?
4. Worth a `complexity` dial separate from `spice`, or keep one knob?
