# Research note: PartWise (cjohanson64-netizen)

**Date:** 2026-07-21  
**Repo:** https://github.com/cjohanson64-netizen/PartWise  
**Author:** Carl Biggers-Johanson  
**Status:** Tier A deep-dive #3 — M4 `/check` UX + evaluate API peer  
**Source:** README; backend FastAPI (`main`, models, evaluator, projection,
TAT adapter/graphs); frontend SATB grader (OSMD editor, score/validation UI).  
**Meta:** 0★, created/updated 2026-05-20, language Python, **no SPDX license**
in GitHub metadata. Young classroom POC.

---

## 1. What it is

An **interactive student SATB part-writing evaluator**:

1. Student picks major key + RN progression (`I ii IV V vi` only).
2. Writes four voice notes in an **OSMD** notation editor (click + diatonic
   step up/down; RN labels under bass).
3. Clicks **Evaluate** → backend returns:
   - pass / warn / fail **checks** with per-note issues
   - **issue-weighted percentage score** + human label
   - **color-coded notes** (green / orange / red)
4. Button becomes **Try Again** → clear evaluation and revise.

Philosophy slogan (README + TAT projection contract):

```txt
React renders.
Python calculates.
TAT interprets.
```

**Vs Harmonyx:** PartWise is **check-first pedagogy** (student supplies notes).
Harmonyx today is **analyze + generate**; planned **M4 `POST /check`** is the
same product surface as PartWise’s evaluate path. PartWise does **not** ship a
serious realizer (raw random-ish chord-tone pick + optional generate endpoint).

---

## 2. Stack

| Layer | Choice |
|-------|--------|
| Frontend | React 19 + Vite; feature folder `features/satb-grader/` |
| Notation | OSMD via client-built MusicXML (`buildMusicXml.js`) + DOM overlays for selection/colors |
| Backend | FastAPI + Pydantic; **no music21** |
| Semantics | **TryAngleTree (TAT)** DSL graphs under `backend/app/tat/` |
| TAT runtime | TypeScript package in `tat-library/`; Python shells out: `npx tsx run-module-json.ts` |
| Pitch | Hand-rolled string pitches (`C4`, `F#5`) → MIDI; key-aware spellings |

**Dependency note:** frontend `package.json` lists only React; code imports
`opensheetmusicdisplay` — install path may be incomplete in the published
snapshot (POC smell). Backend `requirements.txt` is FastAPI/Pydantic/Uvicorn only.

---

## 3. Architecture

```
frontend (Vite :5173)
  SatbGraderPage
    SetupBar (key, chord count, evaluate/try-again)
    SatbOsmdPreview (MusicXML → OSMD + click overlays + note status CSS)
    SelectedNoteControls (diatonic ↑↓, free pitch string)
    ScoreCard + ValidationPanel (from projection)

        POST /api/satb/evaluate
                │
backend FastAPI
  validate_satb_evaluate_request   # keys, functions, lengths, parseable pitches
  build_candidate_from_submission  # normalize → candidate dict
  evaluate_candidate_semantics
        ├─ load TAT graphs (subprocess → JSON graph export)
        └─ tat_rule_adapter.evaluate_candidate_with_tat_rule_graphs
              Python primitive evaluators keyed by ruleType
  build_projection                 # exercise + voices + validation + score
```

Also:

| Endpoint | Role |
|----------|------|
| `GET /health` | Liveness |
| `GET /api/satb/semantic-backbone` | TAT module load readiness |
| `POST /api/satb/generate` | Raw mechanical voicing + same semantic path (demo, not pedagogy core) |
| `POST /api/satb/evaluate` | **Student submit path** (M4 analogue) |

---

## 4. Request / response shape (evaluate)

### Request

```json
{
  "key": "C",
  "mode": "major",
  "progression": ["I", "IV", "V", "I"],
  "difficulty": "ap_music_theory",
  "voices": {
    "soprano": ["E4", "F4", "G4", "E4"],
    "alto":    ["C4", "C4", "D4", "C4"],
    "tenor":   ["G3", "A3", "B3", "G3"],
    "bass":    ["C3", "F3", "G3", "C3"]
  }
}
```

- One chord per “measure”; whole notes; all major-key root-position functions
  from a fixed table.
- Supported functions: **`I`, `ii`, `IV`, `V`, `vi`** only.
- Major keys with full tables (sharps through C#, flats through Cb).

### Response: `projection` (UI contract)

| Section | Contents |
|---------|----------|
| `exercise` | key, mode, meter, progression, difficulty, title |
| `voices` | per-voice id/label/clef/range + notes |
| `chords` | RN + root + figured_bass always `"5/3"` |
| `validation` | status `valid` \| `valid_with_warnings` \| `invalid`; counts; `checks[]` |
| `score` | percent 0–100, label, earned/possible, pass/warn/fail counts |
| `evaluation` | strategy string + explanation (submitted path) |

Each **check**:

```txt
id, label, status (pass|warn|fail), detail, category, issues[]
```

Each **issue** (location-aware feedback):

```txt
type, title, message, chord_index, chord_label, voice, note, expected[], actual
```

Frontend maps issues → `noteStatuses[voice:chordIndex]` taking **worst** of
pass/warn/fail for color overlays.

This is an excellent **M4 API sketch**: structured violations with voice +
chord index, not just a flat string list.

---

## 5. Rules actually enforced today

TAT authors many concepts; **only two graphs are executed** on evaluate:

1. `satb-rules.graph.tat` — vertical / chord-tone basics  
2. `satb-harmony.graph.tat` — progression flow + V–I cadence  

### Implemented Python adapters (`RULE_EVALUATORS`)

| ruleType | Category | Enforcement | Behavior |
|----------|----------|-------------|----------|
| `voice_range_tiered` | Range | hard | Normal range → pass; extended only → **warn**; outside extended → **fail** |
| `voice_order` | Spacing | hard | `S ≥ A ≥ T ≥ B` or fail (crossing) |
| `upper_voice_spacing` | Spacing | soft | S–A or A–T > 12 st → **warn** (not fail) |
| `complete_triads` | Harmony | soft | missing root/3rd/5th → warn; non-chord tone → **fail** |
| `harmonic_progression_flow` | Harmony | soft | movement must match graph edges (`commonlyMovesTo`, `predominantMovesTo`, …); weak `mayReturnTo` → warn |
| `cadence_dominant_to_tonic` | Cadence | soft | last two RNs should be V then I; else warn |

### Authored but **not wired** into evaluate (V2/V3 roadmap)

`satb-voice-leading.graph.tat` + tendency network define:

- parallel P5/P8 (hard contract in graph state)
- leading-tone / chordal-seventh **contextual** resolution
- large leaps, soprano stepwise preference  

If a `ruleType` has no adapter, evaluate returns a **warn** check saying the
adapter is missing — honest incomplete flag.

### PartWise ranges (tiered)

| Voice | Normal (classroom) | Extended |
|-------|--------------------|----------|
| S | C4–F#5 | A3–A5 |
| A | G3–D5 | E3–F5 |
| T | C3–G4 | A2–Bb4 |
| B | E2–C4 | C2–Eb4 |

Harmonyx locked (`PARTWRITING-RULES` §0): single hard band S C4–G5, A G3–D5,
T C3–G4, B E2–C4. **Closer to PartWise “normal” than “extended.”** PartWise
softens extremes as warnings — useful UX; **do not change fixtures** to match.

Spacing: PartWise **warns** on upper-voice > octave; Harmonyx treats as
**hard** fail. Crossing: both hard.

---

## 6. Issue-weighted scoring

```txt
start at 100
− sum(ISSUE_DEDUCTIONS[issue.type]) for every structured issue
− fallback: warn-without-issues −4, fail-without-issues −8
clamp to [0, 100]
```

Sample deductions:

| Issue type | Points |
|------------|--------|
| `voice_crossing` | 10 |
| `outside_extended_voice_range` | 8 |
| `non_chord_tone` | 6 |
| `undefined_harmonic_movement` | 5 |
| `cadence_mismatch` / `cadence_too_short` | 4 |
| `missing_chord_tone` / `upper_voice_spacing` | 3 |
| `outside_normal_voice_range` | 2 |

Labels: Excellent (≥90 and fully valid) → Strong → Needs revision → Developing
→ Needs significant revision.

**Pedagogy win:** one small issue doesn’t zero the exercise; repeated/severe
issues still hurt. Good pattern for M4 teacher/student mode (optional).

---

## 7. Frontend UX details (steal-worthy)

| Pattern | Detail |
|---------|--------|
| OSMD + **client MusicXML** | Rebuild score on every edit; no server round-trip for notation |
| Four separate parts | S/A treble, T/B bass — not grand staff (Harmonyx uses braced grand staff) |
| Measure-click selection | Hit areas per staff×measure; RN dropdowns anchored under bass |
| Diatonic motion | Step up/down respects key accidentals (e.g. D major E→F#) |
| Evaluate ↔ Try Again | Same button toggles evaluation state; clear colors on try-again |
| Note coloring | Default all pass after eval; overlay worst issue status per note |
| Issue cards | Title + message + expected/actual + chord context |

**Not present:** MusicXML upload of an existing chorale; MIDI import; playback;
minor mode; inversions; sevenths; parallel detection UI.

---

## 8. TryAngleTree (TAT) — what to learn vs skip

### What TAT is doing here

- Graph modules declare **rule identity**: id, label, category, enforcement,
  thresholds, status copy, allowed harmonic edges.
- Python **does not invent** “what a pass means”; it implements **primitive
  comparisons** (`pitch_to_midi`, set membership, edge lookup).
- Projection/boundary modules define the **UI data contract** so React must not
  invent musical validity.

### Honest assessment for Harmonyx

| Steal idea | Copy TAT engine? |
|------------|------------------|
| Separate **rule contracts** (labels, severity, thresholds) from execution | **No** — we already have `PARTWRITING-RULES.md` + locked fixtures + `rules.py` |
| Graph-authored progression map | Optional later; we have grammar + L2 validate |
| Subprocess TS runtime per request | **Avoid** — latency, dual-language ops, fragile |

PartWise’s real insight is **architectural separation of meaning vs pixels**,
not the TAT language itself. Harmonyx’s cleaner analogue:

```txt
PARTWRITING-RULES + fixtures  =  semantic law
rules.py / validate.py        =  primitives + gates
projection/API models         =  UI contract
React/static                  =  render only
```

---

## 9. Comparison matrix vs Harmonyx

| Dimension | PartWise | Harmonyx |
|-----------|----------|----------|
| Primary verb | **Evaluate student notes** | Analyze score; generate SATB from RN |
| M4 `/check` | **Yes (core product)** | Planned, not built |
| Rules depth V1 | Range, crossing, spacing, complete triad, RN flow, V–I | Full VL: range, spacing, crossing/overlap, parallels, direct, LT, 7th |
| Parallels / LT / 7ths | Authored in TAT; **not executed** | **Locked fixtures + engine** |
| RN vocabulary | I, ii, IV, V, vi major root | Full RN + Q3 inversions/Cad64/secondaries |
| Score in | Note arrays + client MusicXML | MusicXML/MIDI (analyze); RN list (generate) |
| Score out | Projection + OSMD colors | MusicXML grand staff + playback |
| Theory engine | Hand pitch + TAT graphs | music21 + clean-room DP realizer |
| Scoring % | Issue-weighted 0–100 | Eval harness rates, not student grade |
| License / maturity | Unlicensed POC, 0★ | Productizing on PR branch |

**Overlap:** OSMD, RN under bass, pass/warn/fail language, pedagogy feedback.  
**Harmonyx advantage on check quality today:** our `rules.py` already covers
what PartWise lists as V2–V3.  
**PartWise advantage on product UX today:** end-to-end **write → grade →
color → revise** loop we do not have.

---

## 10. Concrete takeaways for Harmonyx M4

### High value (steal patterns, not code)

1. **API shape for `POST /check`:**
   - Input: either MusicXML upload *or* structured SATB + RN (PartWise style).
   - Output: `validation.status` + `checks[]` + location-rich `issues[]`.
2. **pass / warn / fail** tiers mapped to our hard vs soft rules
   (hard → fail; soft preferences → warn). Aligns with choral-counterpoint V/W
   research (#02).
3. **Issue-weighted score** as *optional* pedagogy mode — not required for
   engine correctness; never replace locked binary fixtures.
4. **Note-level color mapping** from issues with voice + chord/measure index —
   reuse OSMD already on Generate tab.
5. **Evaluate → clear → revise** loop on Check UI.
6. **Projection contract:** frontend never decides musical correctness.

### Medium value

7. Tiered ranges (classroom vs extended) as **warn vs fail** — if we add a
   `strictness` flag later; default stays locked hard ranges.
8. Harmonic-flow check on submitted RN labels (reuse L2 `validate_progression`
   language for “unexpected motion”).
9. Cadence expectation soft check when exercise claims a closing phrase.

### Low value / do not steal

10. **TryAngleTree runtime** as dependency.
11. Limiting RN set to five functions.
12. Soft-only spacing (conflicts with locked hard spacing fixtures).
13. Raw `generate` candidate (we already have a real realizer).
14. Separate four-staff OSMD layout if grand staff already works for check.

### Implementation sketch (not a build commitment)

```txt
POST /check
  body: MusicXML file  OR  { key, progression, voices: {S,A,T,B: pitches[]} }
  → parse to beat-aligned SATB voicings
  → for each chord / transition: rules.rule_violations(...)
  → project to PartWise-like checks + issues
  → optional score: map slug → deduction table (config, not fixtures)
  → frontend: OSMD colors + ValidationPanel twin
```

Reuse: `app/generation/rules.py`, `voicing` shape, grand-staff MusicXML builder,
existing OSMD. New: upload/path parse, issue projection, check UI tab.

---

## 11. Risks / caveats

- **No license** → study patterns only; do not copy substantial code.
- Incomplete frontend deps (OSMD missing from package.json) — treat as demo.
- V1 rule set **weaker** than our locked realizer; their roadmap is catching up
  to what we already enforce.
- TAT shell-out + dual stack is operationally heavy.
- `difficulty` field exists but does not appear to change rule set (label only).
- Figured bass always `5/3` — inversions not real yet (roadmap V4).
- Repo frozen ~May 2026 in scan metadata — may not track AP rubric evolution.

---

## 12. Links to our docs / code

| Our asset | Connection |
|-----------|------------|
| M4 `POST /check` | Direct product twin of `/api/satb/evaluate` |
| `app/generation/rules.py` | Already stronger VL checker than PartWise V1 |
| `tests/test_partwriting.py` | **Locked** — severity differences must not rewrite fixtures |
| `docs/PARTWRITING-RULES.md` | Source of hard vs soft meaning |
| `app/generation/validate.py` | Peer of their harmonic-flow + cadence soft checks |
| `app/static/index.html` OSMD | Front half of PartWise UI already exists for Generate |
| `docs/research/02-choral-counterpoint.md` | Checker calibration culture + V/W tiers |
| `docs/CLASSICAL-AI-LANDSCAPE.md` | PartWise Tier A entry |

---

## 13. Open questions (for human)

1. M4 primary input: **MusicXML upload of existing exercises**, or **in-browser
   note editor** like PartWise, or both?
2. Should `/check` return a **percentage grade**, or only violation lists
   (engine-honest) with optional pedagogy scoring behind a flag?
3. Map hard rules → `fail` and soft costs → `warn` 1:1 with PartWise language?
4. Check UI: new **Check** tab vs reuse Generate OSMD after analyze/generate?
5. Worth a later “AP rubric mode” (PartWise V5) or stay theory-absolute?

---

## 14. One-liner

PartWise is the **UX and API blueprint for Harmonyx M4**: student/teacher
evaluate loop, structured issues, colors, weighted score — while Harmonyx
already owns the **deeper voice-leading law**; do not adopt TAT or weaken
locked rules to match their softer V1 checker.
