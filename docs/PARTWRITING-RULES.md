# Part-writing rules — the source of truth

These are the **authoritative rules** the SATB realizer and the part-writing
checker implement *against*. They are ground truth for the project, independent
of whatever agent writes the code: an implementation is correct when it
satisfies the **hard invariants** (encoded as checker functions + fixtures) and
uses the **soft-preference weights** documented here. Do not re-derive these
from a model's latent knowledge — implement *these*.

Two categories:
- **Hard invariants** — objective, testable, non-negotiable. Each becomes a
  checker function and at least one golden fixture (a hand-built voicing pair
  with the expected result). These are pass/fail.
- **Soft preferences** — stylistic, expressed as weights/conventions with
  rationale. These shape the cost function; they are tuned, not asserted.

Notation: pitches as note+octave (`C4` = middle C). A **voicing** is
`(S, A, T, B)` with `S ≥ A ≥ T ≥ B` in pitch. A **transition** is an ordered
pair of voicings `(prev, cur)`.

---

## 0. Voice ranges (hard)
A voicing is invalid if any voice is outside its range.

| Voice | Min | Max |
|---|---|---|
| Soprano | C4 | G5 |
| Alto | G3 | D5 |
| Tenor | C3 | G4 |
| Bass | E2 | C4 |

**Fixtures:** `S=A6` → out-of-range (soprano). `B=D2` → out-of-range (bass).
A voicing with all four voices inside → valid.

## 1. Spacing (hard)
Adjacent **upper** voices must be ≤ one octave apart. Tenor–Bass may exceed an
octave.
- `S − A ≤ 12` semitones, `A − T ≤ 12`. No limit on `T − B`.

**Fixtures:** `S=C5, A=A3` (15 semitones) → spacing violation (S–A).
`S=C5, A=E4, T=C4, B=C2` → valid (T–B > octave is allowed).

## 2. Voice crossing & overlap (hard)
- **Crossing:** within a single voicing, order must hold `S ≥ A ≥ T ≥ B`.
- **Overlap:** across a transition, a voice must not move above the *previous*
  note of the voice above it, nor below the *previous* note of the voice below
  it. Formally, for adjacent voices `upper`, `lower`:
  `cur.lower ≤ prev.upper` and `cur.upper ≥ prev.lower`.

**Fixtures:** `A=E4, T=G4` in one voicing → crossing (T above A).
prev `T=E4`, cur `A=D4` → overlap (alto dips below tenor's prior note).

## 3. Parallel perfect 5ths and octaves (hard)
For any pair of voices, if both notes form a perfect 5th (7 semitones mod 12) or
perfect octave/unison (0 mod 12) in `prev`, **and** the same pair again forms a
P5 or P8 in `cur`, **and** both voices moved (same direction), it is a parallel.
- Applies to all six voice pairs. Unisons→unisons and 5th→5th and 8ve→8ve all
  count. (A P5 moving to a P8 between the same voices — "unequal 5ths/consecutive
  by contrary motion — is a separate, softer case; see §7.)

**Fixtures:**
- prev `S=G4,B=C4` (P5), cur `S=A4,B=D4` (P5) → parallel 5ths.
- prev `S=C5,B=C4` (P8), cur `S=D5,B=D4` (P8) → parallel octaves.
- prev `S=G4,B=C4` (P5), cur `S=G4,B=C4` (same, no motion) → **not** a parallel
  (a repeated chord; voices didn't move).

## 4. Direct (hidden) 5ths and octaves (hard, outer voices)
The **outer** voices (S & B) moving by **similar motion** into a perfect 5th or
octave, **with the soprano moving by leap** (> 2 semitones), is forbidden.
- If the soprano arrives by step, it is allowed.

**Fixtures:** prev `S=C5,B=C3`, cur `S=G5,B=C4` (both up, arrive at P5/P8,
soprano leaps a 5th) → direct 5th/8ve. Same arrival but `S` steps `F5→G5` →
allowed.

## 5. Leading-tone resolution (hard at cadence)
The leading tone (scale-degree 7) in an **outer voice** at a `V(7) → I` motion
must resolve **up by semitone to the tonic**.
- Inner-voice leading tones *may* fall to scale-degree 5 to complete the triad
  ("frustrated leading tone") — that is a **soft** allowance (§8), not a
  violation.

**Fixture:** key C, prev `V` with `B4` in soprano, cur `I` with soprano `A4`
→ violation (LT should go to C5). Soprano `B4 → C5` → satisfied.

## 6. Chordal-seventh resolution (hard)
The 7th of any seventh chord must resolve **down by step** into the next chord.

**Fixture:** key C, `V7` with `F` (the 7th) in tenor, next chord's tenor is
`A` → violation (7th must fall to `E`). Tenor `F→E` → satisfied.

---

## 7. Doubling conventions (soft — weighted, with a hard carve-out)
- **Hard carve-out:** never double the **leading tone**, and never double the
  **chordal 7th**. (These two are invariants — add them to the checker.)
- Soft preferences (penalize deviations, don't forbid):
  - Root-position triad → **double the root**.
  - First inversion → double the soprano note or the root; avoid doubling the
    bass (the 3rd) unless it smooths voice leading.
  - Cadential ⁶⁴ (second-inversion tonic over dominant bass) → **double the
    bass** (scale-degree 5).
  - Diminished triads (e.g. viio6) → **double the 3rd** (the bass), not the root.

## 8. Voice-leading cost (soft — the search objective)
`transition_cost(prev, cur)` = weighted sum. Defaults (tune later; documented so
they're not invented per session):

| Term | Weight | Meaning |
|---|---|---|
| Total voice motion | 1.0 × semitones | Sum of |Δ| over the four voices; prefer minimal motion / common tones. |
| Large leap | +3 per voice | Any single voice leaping > a 4th (5 semitones). |
| Bass leap | +1 per | Slightly discourage bass leaps beyond a 5th. |
| Doubling deviation (§7 soft) | +4 | Wrong double for the chord type/inversion. |
| Frustrated LT (inner) | +2 | Inner-voice LT falling to 5 (allowed but not preferred). |
| Similar motion in all voices | +2 | Prefer some contrary/oblique motion. |

Hard-invariant violations (§0–§6) are **not** costs — they prune the candidate
outright (infinite cost / excluded from the search).

---

## 9. Functional-harmony transition table (soft — Layer 1 grammar)
Chords grouped by function; generation walks a weighted transition table.
Weights are relative frequencies (higher = more idiomatic); **0 = forbidden**.

**Functions (major key):**
- **T** (tonic): `I`, `vi`, `iii`, `I6`
- **PD** (predominant): `ii`, `ii6`, `IV`, `IV6`
- **D** (dominant): `V`, `V7`, `viio6`, `V6`

**Transitions (major key; minor key is analogous with `i`, `iv`/`ii°6`, `V`/`viio`):**

| From | To (weight) |
|---|---|
| `I` | `V`:4, `V7`:3, `IV`:3, `ii`:3, `vi`:2, `I6`:2, `iii`:1 |
| `I6` | `ii`:3, `IV`:3, `V`:2, `ii6`:2 |
| `ii` | `V`:5, `V7`:4, `viio6`:1 |
| `ii6` | `V`:5, `V7`:4 |
| `IV` | `V`:5, `V7`:4, `I`:2 (plagal), `ii`:1 |
| `IV6` | `V`:3, `I`:2 |
| `V` | `I`:5, `vi`:2 (deceptive), `V7`:2 |
| `V7` | `I`:6, `vi`:2 (deceptive) |
| `V6` | `I`:5 |
| `vi` | `ii`:3, `IV`:3, `V`:2, `ii6`:1 |
| `iii` | `vi`:3, `IV`:2 |
| `viio6` | `I`:6 |
| `Cad64` | `V`:1 (special: cadential ⁶⁴ only resolves to V) |

**Forbidden (weight 0), enforced:** `V→IV`, `V→ii`, `V7→IV`, `viio6→` anything
but `I`, `V→I6` at a cadence (want root position for a PAC).

**Cadence rule (hard for the grammar):** the final 1–2 chords are forced to a
real cadence — PAC = `V(7)→I` both root position with soprano on scale-degree 1;
HC = `…→V`. Deceptive = `V(7)→vi` only mid-phrase, never as the final cadence.

---

## 10. Roman-numeral normalization (for the round-trip eval)
To compare a *generated* progression against the *analyzed* result, normalize
each RN to a tuple and define agreement:

```
normalize_rn(figure) -> (degree:int 1-7, quality:str, inversion:int, seventh:bool)
```
- `degree`: scale degree of the root (1–7), accidental-insensitive
  (`bVII` and `VII` → degree 7; record the accidental separately if needed).
- `quality`: `major | minor | diminished | augmented`.
- `inversion`: 0/1/2/3 from the figure.
- `seventh`: whether a 7th is present.

**Agreement (primary metric):** `degree` **and** `quality` match. Inversion and
seventh are a **secondary**, stricter metric reported alongside. Rationale: a
round-tripped `V` vs. `V7` (added/dropped 7th by voicing) or a `V` vs. `V6`
(inversion from the bass) is a near-miss, not a wrong chord — track it, but
don't fail the primary number on it.

---

## 11. music21 gotchas (so the plumbing doesn't stumble)
- **Already-parsed Streams:** `converter.parse()` chokes on a `stream.Stream`.
  Short-circuit when the input is already a Stream (the analyzer already does).
- **Writing files needs a path:** `score.write('musicxml', fp=path)` /
  `write('midi', fp=path)` — write to a temp file, don't hand it a buffer.
- **RomanNumeral construction:** `roman.RomanNumeral('V7', key.Key('C'))`.
  Cadential ⁶⁴ is `'Cad64'` in music21. Inversions are expressed in the figure
  (`'V6'`, `'ii65'`). Build a `Key` object rather than passing a bare string
  where the API expects `Key`.
- **`romanNumeralFromChord` is noisy** on incomplete/NCT-laden slices (we saw
  `quartal trichord`, `incomplete dominant-seventh`); the generator side spells
  from clean RNs so it's unaffected, but the round-trip eval must tolerate it
  (see §10).
- **Pitch classes are 0–11**; compare mod 12 for interval/parallel checks.
- **Leading-tone / degree lookups:** derive scale degrees from `Key`, not from
  absolute pitch, so minor keys and accidentals behave.

---

## How this maps to code (for the implementer)
- §0–§6 + the §7 carve-out → `rules.py::rule_violations(prev, cur, ctx)`
  returning a list; each rule has a matching golden fixture in
  `tests/test_partwriting.py` (already written — see below).
- §7 (soft) + §8 → `rules.py::transition_cost(prev, cur, ctx)`.
- §9 → `grammar.py` transition table + cadence forcing.
- §10 → `chords.py::normalize_rn` + the round-trip eval.
- §11 → applied throughout; keep the realizer free of FastAPI imports.

### Fixed contract (the pre-written fixtures depend on this — do not diverge)
- `voicing.Voicing(s, a, t, b)` — dataclass of four MIDI ints, stored in S/A/T/B
  order **verbatim** (not reordered; a crossing must be representable).
- `rules.rule_violations(prev, cur, ctx) -> list[RuleViolation]`:
  - `prev` is a `Voicing` or **`None`** for the first chord (then run only the
    static rules on `cur`).
  - `ctx` is a dict `{"key": str, "prev_roman": str|None, "cur_roman": str}`.
  - Each `RuleViolation` exposes a `.rule` attribute set to one of the
    **canonical slugs**:
    `range`, `spacing`, `crossing`, `overlap`, `parallel_fifths`,
    `parallel_octaves`, `direct`, `leading_tone`, `seventh`,
    `doubled_leading_tone`, `doubled_seventh`.
  - Static rules (apply when `prev is None`): `range`, `spacing`, `crossing`,
    `doubled_leading_tone`, `doubled_seventh`. Transition rules (need `prev`):
    `overlap`, `parallel_fifths`, `parallel_octaves`, `direct`, `leading_tone`,
    `seventh`.

**The fixtures are the spec, and they are already written.**
`tests/test_partwriting.py` encodes the §0–§7 hard invariants and is
**pre-committed and locked** — implement the engine to make it pass; do **not**
edit the fixtures to match an implementation. Today the module `importorskip`s
(so CI is green) and activates automatically once `app/generation/voicing.py`
and `app/generation/rules.py` exist. An implementation is "correct" when
`tests/test_partwriting.py` passes and the realized test progressions produce
**zero** hard-invariant violations. Weights (§8, §9) are tunable but must be
*present and documented*, not invented.
