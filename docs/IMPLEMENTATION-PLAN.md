# Implementation plan

Concrete build plan for the next phase (the chorale **generator**) plus the
parallel **analyzer improvements**. Design rationale lives in
[`chorale-generation.md`](chorale-generation.md) and [`ROADMAP.md`](ROADMAP.md);
this file is the step-by-step *how*, with modules, signatures, tests, and
acceptance criteria.

Guiding constraints (carry over from the existing code):
- Deterministic core; any LLM stays optional/gated (like `explainer.py`).
- Don't regress the 13 tests or the eval gate.
- New voicing/grammar logic is **clean-room** — implement rules from theory, do
  not copy third-party code.

---

## Milestone 0 — scaffolding
**Goal:** module layout + Pydantic models in place, no logic yet.

- New package `app/generation/` with:
  - `chords.py` — RN ↔ pitch-class helpers.
  - `voicing.py` — SATB voicing candidates + constraints.
  - `rules.py` — part-writing rules / cost function (shared with the checker).
  - `realize.py` — the DP/search that turns a progression into an SATB score.
  - `grammar.py` — Layer 1 functional-harmony progression generator.
- Extend `app/models.py`: `GenerateRequest`, `GenerateResponse`,
  `ProgressionRequest`, `ProgressionResponse`, `RuleViolation`.
- **Acceptance:** package imports; models validate; `pytest` still green.

---

## Milestone 1 — Layer 2 realizer core (the reusable heart; build first)

### 1a. Chord spelling — `app/generation/chords.py`
```python
def chord_pitch_classes(roman: str, key: str) -> list[int]      # e.g. "V7","C major" -> [7,11,2,5]
def chord_members(roman: str, key: str) -> dict                 # {root, third, fifth, seventh?} as pitches
def is_chord_tone(pitch, roman: str, key: str) -> bool          # soprano compatibility check
```
- Built on `music21.roman.RomanNumeral(roman, key)`.
- **Tests:** I/V/V7/ii6/vii°6 spell correctly in C major and A minor;
  `is_chord_tone` accepts chord tones, rejects non-members.

### 1b. Voicing candidates — `app/generation/voicing.py`
```python
@dataclass
class Voicing: s:int; a:int; t:int; b:int   # MIDI numbers, S≥A≥T≥B
def candidate_voicings(roman, key, *, soprano:int|None=None) -> list[Voicing]
```
- Enumerate SATB assignments of the chord's tones subject to **static rules**:
  vocal ranges (S ~C4–G5, A ~G3–D5, T ~C3–G4, B ~E2–C4), spacing ≤ an octave
  between adjacent upper voices, no voice crossing, bass = chord's bass note for
  the given inversion, doubling conventions (double the root in root position;
  don't double the leading tone or the 7th).
- If `soprano` given, fix S and enumerate A/T/B beneath it.
- **Tests:** every returned voicing satisfies ranges/spacing/crossing; root
  position doubles the root; a given soprano is respected.

### 1c. Transition cost + rules — `app/generation/rules.py`
```python
def transition_cost(prev: Voicing, cur: Voicing, ctx) -> float          # smoothness + penalties
def rule_violations(prev: Voicing, cur: Voicing, ctx) -> list[RuleViolation]
```
- Penalties/violations: parallel 5ths & 8ves, direct/hidden 5ths & 8ves into a
  perfect interval by leap in outer voices, unresolved leading tone (deg 7 → 1
  in an outer voice at cadence), unresolved chordal 7th (must step down),
  large leaps, voice overlap.
- Smoothness = summed absolute semitone motion of the four voices (prefer common
  tones / stepwise).
- Reuse `music21.voiceLeading.VoiceLeadingQuartet` for parallel/hidden detection
  where it fits; implement the rest.
- **Tests:** a hand-built parallel-fifths pair is flagged; a smooth I→V→I scores
  lower than a leapy alternative; LT/7th resolution enforced.

### 1d. Realize (search) — `app/generation/realize.py`
```python
def realize(progression: list[str], key: str, *,
            soprano: list[int|None]|None = None,
            time_signature: str = "4/4") -> Score   # music21 Score, 4 voices
```
- **Viterbi / DP** over chords: states = `candidate_voicings` per chord, edge
  weight = `transition_cost`, pick the min-cost path. Optional beam width to cap
  blowup.
- Given-soprano mode: run the 1e compatibility check first; pass fixed sopranos
  into `candidate_voicings`.
- Emit a `music21` `Score` with four `Part`s (S/A/T/B) → `.write('musicxml')`.
- **Tests:** realizing `["I","IV","V","I"]` in C major yields a 4-voice score
  with zero parallel 5ths/8ves and correct outer-voice cadential resolution.

### 1e. Soprano compatibility check
```python
def check_soprano(progression, key, soprano) -> list[dict]   # [] if OK, else per-index mismatches
```
- Each provided soprano note must be a chord tone (1a). On mismatch, collect
  `{index, roman, soprano, chord_tones}`.
- **Tests:** a bad soprano note is reported with the right index and chord tones.

### 1f. Endpoint — `POST /generate` in `app/main.py`
- Request: `{key, progression[], time_signature?, soprano?}`.
- If `soprano` fails `check_soprano` → **422** with the offending beats.
- Success → MusicXML (as a download/string) + the structured chord list.
- **Tests:** happy path returns 200 + valid MusicXML; bad soprano returns 422.

### Milestone 1 acceptance
`POST /generate` turns a hand-written progression into a downloadable four-part
MusicXML hymn with no parallel 5ths/8ves on the test progressions, both
soprano-free and soprano-given.

---

## Milestone 2 — round-trip + rule eval (makes quality measurable)
- **Round-trip:** generate → feed the MusicXML back through `analyze_score` →
  compare recovered Roman numerals to the input. Report agreement %.
- **Rule violations:** run `rule_violations` across the realized score; report
  count (target: 0 on the curated test progressions).
- Add `eval/run_generation_eval.py` printing both numbers; wire into CI as a
  gate (e.g. round-trip ≥ threshold, violations == 0 on the fixtures).
- **Acceptance:** both metrics printed and gated in CI.

---

## Milestone 3 — Layer 1 progression grammar — `app/generation/grammar.py`
```python
FUNCTION = {"T": {"I","vi","iii"}, "PD": {"IV","ii","ii6"}, "D": {"V","V7","viio6"}}
TRANSITIONS: dict[str, list[tuple[str,float]]]     # weighted, encodes the norms
def generate_progression(key, *, length=8, locked: dict[int,str]|None=None,
                         cadence: str="PAC", seed:int|None=None) -> list[str]
```
- Weighted Markov walk over the transition table: T→PD→D→T flow, `ii→V`,
  `V→I`/`V→vi`, cadential ⁶⁴→V; forbid retrogressions like `V→IV`.
- **Cadence-aware:** force the final 1–2 chords to a real cadence (PAC = V→I
  root position; HC = …→V).
- **Locking:** honor `locked[index]` and generate around them (constrained walk;
  fall back / re-roll segments that can't connect).
- `POST /progression`: `{key, length?, locked?, cadence?}` → RN list.
- **Tests:** output respects locked slots; ends on the requested cadence; never
  emits a forbidden retrogression; deterministic under a fixed seed.
- **Acceptance:** `/progression` → `/generate` chains end-to-end to MusicXML.

---

## Milestone 4 — part-writing checker as a standalone feature (B1)
- Expose `rule_violations` over an **uploaded** SATB score:
  `POST /check` (MusicXML/MIDI in → list of violations with measure/beat).
- Reuses `rules.py`; pairs with the analyzer (analyze + critique in one tool).
- **Tests:** a chorale with a deliberate parallel fifth is flagged at the right
  spot; a clean chorale returns none.

---

## Milestone 5 — frontend generation panel
- Second panel on the existing page: pick key + length (or type a progression),
  **generate → edit/lock individual RNs → realize**, then render the result and
  offer a MusicXML download. Optionally render notation (Verovio/OSMD) later.
- **Acceptance:** full loop works in the browser; matches the analyzer panel's
  visual style.

---

## Parallel track — analyzer improvements (independent of the generator)
Order by value (see ROADMAP A1/A2/A7):
1. **NCT filtering (A1)** — classify chord tone vs. passing/neighbor/suspension
   from melodic + metric context (`note.beatStrength`, per-voice steps) and drop
   NCTs before labeling. Guard with before/after tests on BWV 140/7.
2. **Fermata-based cadence segmentation (A2)** — segment on fermatas/rests, test
   cadences only at phrase ends; then PAC vs. IAC refinement.
3. **RN-agreement eval (A7)** — chord-by-chord vs. a labelled RomanText corpus,
   replacing key-only agreement as the headline metric.

---

## Suggested overall order
M0 → M1 (realizer + `/generate`) → M2 (eval) → M3 (grammar + `/progression`) →
M4 (checker) → M5 (frontend). Analyzer A1/A2 can slot in any time in parallel.

## Dependencies / notes
- No new runtime deps for the generator — music21 covers RN spelling,
  `voiceLeading`, and MusicXML output. `numpy` (already present) if the DP wants
  arrays.
- Keep each module independently testable; the realizer must not import FastAPI.
