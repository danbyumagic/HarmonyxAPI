# Research note: chorale-optimizer (604korupt)

**Date:** 2026-07-21  
**Repo:** https://github.com/604korupt/chorale-optimizer  
**Author:** 604korupt  
**Status:** Tier A deep-dive #4 — beam search + iterative rule fixups vs DP realizer  
**Source:** README; full read of `harmonizer.py`, `main.py`, `score_svg.py`,
`test_harmony.py`; ran `python -m unittest test_harmony` (81 tests, OK, ~0.14s).  
**Meta:** 0★, last push ~2026-06-30, language Python, **no SPDX license** in
repo metadata. Zero third-party deps (stdlib + Tkinter + browser for score).

---

## 1. What it is

An **interactive four-part chorale harmonizer**:

1. User supplies **soprano MIDI** + **chord-symbol progression** + key.
2. Engine fills **alto / tenor / bass** via beam search, then up to six rounds
   of sequential rule-fix passes.
3. Tkinter shows a text table (flags out-of-chord tones with `(!)`).
4. **Show Score** opens a local browser page: VexFlow grand staff + Web Audio
   Play/Stop + tempo slider.

Philosophy (README, honest):

> The optimizer makes a best effort but does not guarantee perfect voice
> leading in all cases.

**Vs Harmonyx:** same classical SATB problem surface (RN-ish symbols → four
voices), but **control surface differs**: they **require a fixed soprano** and
optimize ATB; Harmonyx **realizes all four voices** from Roman numerals
(optional soprano constraint). Search style also differs: **soft beam +
post-hoc fixups** vs our **hard-pruning Viterbi/DP**.

---

## 2. Stack

| Layer | Choice |
|-------|--------|
| Core | Pure Python, one fat module `harmonizer.py` (~1350 lines) |
| GUI | Tkinter (`main.py`) — desktop only |
| Score + audio | `score_svg.py`: self-contained HTML, VexFlow 4.2.2 CDN, Web Audio |
| Theory lib | **None** — hand tables of pitch classes, MIDI ints |
| Tests | `unittest` (`test_harmony.py`), 81 tests |
| Deps | Zero pip packages |

No FastAPI, no music21, no MusicXML export, no LLM.

---

## 3. Architecture

```
main.py (Tkinter)
  beat table: chord combobox + soprano MIDI entry
  key combobox (30 major/minor)
  ▶ Harmonize  ──thread──►  optimize(soprano, chords, key_offset)
  🎼 Show Score  ─────────►  open_score(...) → local HTTP + webbrowser

harmonizer.py
  CHORDS[name] → {pcs, bass, root, third, fifth, seventh}  # in C, then transpose
  KEYS[name]   → (semitone_offset, vexflow_key_string)
  EXAMPLES[]   → 22 named progressions

  optimize()
    ├─ _find_phrase_boundaries(chord_names)   # split on CADENCE_PATTERNS
    ├─ per segment: _beam_search_chunk(width=40)
    │     enumerate A/T/B in ranges; soft cost _score_candidate
    │     dead-end → chord_targets() heuristic seed
    ├─ snap A/T to chord pcs; snap B to bass pc
    ├─ _resolve_unisons
    └─ up to 6× sequential fixup loop until A/T stable:
         coverage → common tones → aug2 → parallels → hidden 5ths
         → consec unisons → crossing/spacing → third doubling → doubling
         → 7th resolution → chromatic resolution → ordering

score_svg.py
  MIDI → VexFlow keys/accidentals (key-sig aware)
  embed beats JSON in HTML; grand staff; play all four voices
```

**API surface:** none. Library entrypoint is `optimize(soprano, chord_names,
progress_cb=None, key_offset=0) → (alto, tenor, bass, loss_history)`.

---

## 4. Chord vocabulary

~**80** pre-baked symbols defined in C major pitch classes, transposed by
`key_offset`. Includes:

| Family | Examples |
|--------|----------|
| Diatonic triads / 7ths + inversions | `I`, `I6`, `I64`, `ii7`, `V7`, `V65`, `V43`, `V42`, `viio6`, `viiø7` |
| Minor / mixture | `i`, `iv`, `bVI`, `bVII`, `bIII`, `iio`, `bII` |
| Secondaries | `V/ii`…`V/vi` and 7th/inversion variants; `viio7/V`, etc. |
| Color chords | `N6`, `It6`, `Ger65`, enharmonic `viiodim7{,a,b}` |

**Not dynamic RN parsing** — unknown symbols fail in the GUI. Spelling is
absolute MIDI + table, not music21 Roman-numeral objects.

Harmonyx builds chord tones from music21 RN in key context (`chords.py`);
richer for open-ended figures, thinner for exotic symbols unless we add them.

---

## 5. Search: beam vs our DP

### 5.1 Their beam (`_beam_search_chunk`)

- **Soprano fixed** at every beat.
- Candidates: all MIDI pitches in voice ranges that match chord PCs
  (A 55–74, T 48–67, B 43–60; bass forced to bass-PC).
- Soft filters during expansion: ordering, spacing (S–A/A–T ≤12, T–B ≤24),
  melodic leap A/T ≤7, allow at most **one** missing chord tone.
- Cost (`_score_candidate`): motion smoothness, parallel 5/8 (+50), consec
  unisons (+30), outer similar motion (+5), spacing overages, common-tone
  retention, soft 7th/LT resolution, root-doubling bonus.
- **Beam width 40**; keep best partial paths only.
- Phrase split on `CADENCE_PATTERNS` (`V–I`, `V7–I`, `viio–I`, `IV–I`, …);
  next segment seeds from previous A/T/B.
- If beam empties: inject `chord_targets()` heuristic (not fail).

### 5.2 Their fixup loop

Up to **six** full passes of **twelve** local mutators. Each mutator walks
beats and snaps inner voices (sometimes bass) to repair one rule class.
Order matters; later passes can re-break earlier ones → iteration until
alto/tenor lists stop changing (or 6 hits).

**Always returns a complete ATB** — never raises “no legal path.”

### 5.3 Harmonyx DP (`realize._best_path`)

```
for each RN: candidate_voicings()  # only hard-legal static voicings
Viterbi: prune any transition with rule_violations (hard)
         minimize sum transition_cost (soft)
else RealizationError
```

Optional soprano: filter candidates; no soprano → free S as well as ATB.

### 5.4 Comparison

| Dimension | chorale-optimizer | Harmonyx |
|-----------|-------------------|----------|
| Primary input | Soprano MIDI **+** chord symbols | RN list (+ optional soprano) |
| Search | Beam width 40, **soft** costs | Full DP over discrete candidates |
| Hard constraints in search | Partial (ordering/spacing/leap); many rules only in fixups | **All hard rules prune** paths |
| Completeness | Best-effort; may residual-violate | Fail closed if no hard-clean path |
| Phrase structure | Cadence-pattern segmenting | Whole progression one path |
| T–B spacing | Hard ≤24 in beam | Unlimited (per PARTWRITING-RULES) |
| Bass range | G2–C4 (43–60) | E2–C4 (broader low) |
| Output | MIDI lists | music21 Score / MusicXML / playback events |
| Guarantees | Test suite on *optimizer outputs* | Locked fixtures + `path_violations` |

**Design lesson:** beam+fix is good for **melody-first** tools and
exploratory UIs that must always show *something*. Harmonyx product contract
is closer to **homework-grade correctness** — DP + fail-closed matches locked
`test_partwriting.py` better. Stealing their beam as a *replacement* for DP
would weaken that contract unless fixups become hard-checked and rejection
is restored.

---

## 6. Rules inventory (what they enforce)

Documented / implemented themes (README + fixups + `_check_all_rules` in tests):

| Rule | Where |
|------|--------|
| Voice ranges (S GUI 48–84; A/T/B as above) | beam + tests |
| No crossing / S≥A≥T≥B | beam + `_enforce_ordering` |
| Chord-tone coverage | beam soft + `_ensure_coverage` + tests |
| Correct inversion bass PC | `_snap_bass` + tests |
| Doubling conventions (root / 1st-inv sop / 2nd-inv / no LT or 7th double) | `_fix_doubling`, `_fix_third_doubling` |
| Parallel 5ths/8ves (all pairs; motion same direction) | soft cost + `_fix_parallels` + tests |
| Hidden/direct 5ths outer | `_fix_hidden_fifths` |
| Consecutive unisons | cost + `_fix_consec_unisons` / `_resolve_unisons` |
| 7th down by step; LT up | soft cost + `_fix_seventh_resolution` / chromatic |
| Augmented 2nd melodic | `_fix_aug2` |
| Secondary / mixture chromatic resolution | `_fix_chromatic_resolution` |

**Parallel detection quirk:** `_has_parallel` uses interval class in `{0,7}` and
**same-direction** motion only — similar to a soft classroom definition; does
not distinguish true parallel octaves from unisons the same way every textbook
does, and does not treat contrary motion into P5/P8 (not required for “parallel”
label).

**Hidden fifths:** outer voices only (typical textbook scope).

Harmonyx locked set: ranges, spacing, crossing, overlap, parallels, direct,
LT, 7ths — with **fixtures that must not be edited**. Their suite is rich but
is **coupled to the live optimizer** (module-level `optimize(...)` at import
for several classes), not an agent-independent oracle of isolated voicings.

---

## 7. Frontend / score / playback

### Tkinter GUI

- Catppuccin-ish dark theme.
- Load any of 22 examples; add/remove beats; key selector.
- Result table flags ATB pitches not in chord PCs (or wrong bass PC).
- Harmonize runs on a background thread so UI stays responsive.

### VexFlow score (`score_svg.py`)

- Builds one HTML document with embedded `beats` JSON.
- Spins ephemeral `HTTPServer` on localhost, opens default browser.
- Grand staff, chord labels above, key signature from `KEYS` Vex string.
- **Web Audio** oscillators (not SoundFont): Play / Stop / tempo slider.
- Accidental logic suppresses redundant accidentals already in the key sig.

**Vs Harmonyx UI:** we already have OSMD + Play/Stop @ 75 BPM in the browser
app. Their VexFlow path is a fine **desktop POC** pattern, not a reason to
swap OSMD. Steal ideas only if we ever ship a zero-dep local demo.

---

## 8. Tests

```bash
python -m unittest test_harmony -v
# Ran 81 tests in ~0.14s — OK (verified 2026-07-21)
```

Coverage classes: coverage, ranges, ordering, spacing, bass PC, doubling,
parallels, consec unisons, hidden fifths, resolution, melodic intervals,
common tones, cadences, fifth doubling, named progressions, secondaries,
secondary LT, dim7, modal mixture.

End-to-end progression tests call `optimize` then `_check_all_rules` — a
**property harness on generated output**, similar in spirit to Harmonyx M2
eval / `path_violations`, weaker than our locked *fixture* style (they do not
assert a golden MIDI answer per RN).

Leftover smell: module-level `WEIGHTS = (...)` unused — suggests an earlier
weighted-loss / gradient design before beam+fix settled.

---

## 9. Comparison matrix vs Harmonyx

| Dimension | chorale-optimizer | Harmonyx |
|-----------|-------------------|----------|
| Product | Desktop chorale filler | Web analyze + generate API |
| Input | Soprano + chord symbols | RN list; optional soprano |
| Engine | Beam + iterative fixups | Enumerate + Viterbi/DP |
| Failure mode | Always emit ATB | `RealizationError` if unclean |
| Chord model | Static PC table (~80) | music21 RN + house chords |
| Keys | 30 maj/min offsets | music21 keys |
| Check path | Implicit (tests / flags) | Planned M4 `/check` (PartWise UX) |
| Propose grammar | No | Yes (`/progression`, spice/style) |
| Score format | VexFlow HTML | MusicXML + OSMD |
| Playback | Web Audio in score page | Browser note list @ 75 BPM |
| License | Unclear / none | Project’s own |
| Maturity | Solid personal tool + tests | Productizing, locked fixtures |

**Closest peer axis:** `realize.py` search strategy and `rules.py` inventory —  
not L4 LLM, not M4 student UX (those were Resonance / PartWise).

---

## 10. Steal / don’t-steal

### High value (ideas)

1. **Two-stage search narrative** — global soft path then local repair — as a
   *mental model* for optional “best effort mode” behind a flag, never as
   default for locked correctness.
2. **Phrase segmentation on cadence patterns** — if long RN lists get slow or
   myopic, segment at `V–I` / `V7–I` / Cad64→V for independent DP chunks with
   boundary state handoff (they already pass last A/T/B into next beam).
3. **Rich secondary / mixture / N6 / Ger+ vocabulary** as a **checklist** when
   expanding Harmonyx chord symbols (Q3 spice path already has secondaries;
   Neapolitan / Ger6 not first-class yet).
4. **Always-show residual flags** in UI (`(!)` on illegal tones) — useful for
   M4 check and for Generate debug when soft preferences remain.
5. **Property-based progression suite** pattern (generate → assert rule set)
   already mirrored by our M2 eval; keep both fixture and property styles.

### Medium value

6. Soft cost weights for parallels / LT / 7th as reference numbers when
   tuning `transition_cost` (their scale is arbitrary; ratios are interesting).
7. Explicit “consecutive unisons” as its own soft/hard class (we may fold into
   spacing/doubling).
8. Desktop zero-dep demo for classroom offline — low priority vs web API.

### Low value / do not steal

9. **Replace DP with beam+fix as default** — conflicts with fail-closed
   locked fixtures and M2 “zero hard violations.”
10. **Tkinter + VexFlow CDN** stack — we already ship OSMD + MusicXML.
11. **Static CHORDS dict only** — too rigid for free RN strings; keep music21.
12. **Copy their parallel interval math blindly** — re-verify against
    `PARTWRITING-RULES.md` fixtures.
13. **Always-return-a-voicing** for `/generate` — would hide illegal
    progressions; L3 `fix` already handles *RN* repair separately.

### Do not

- Edit `tests/test_partwriting.py` to match their softer outcomes.
- Port fixup passes as untested side mutations into `realize.py` without a
  hard `path_violations` gate after mutation.

---

## 11. Open questions

1. Would a **optional** `mode=best_effort` (beam or DP + fixups, then report
   residual violations) help demo spicy progressions that currently 422?
2. Is cadence-based **chunked DP** worth it for long L4 progressions, or is
   current full-path DP fast enough at hymn lengths?
3. Should Neapolitan / Ger6 enter Q3 spice only after corpus+fixtures exist?
4. Their bass floor G2 vs our E2 — any hymnal repertoire impact?
5. License unknown — treat as study-only; do not vendor code.

---

## 12. One-screen summary

**chorale-optimizer** = melody+RN → ATB with **beam (w=40) + 6× rule fixup
loop**, Tkinter + VexFlow play, 81 tests, ~80 chord symbols including
secondaries/mixture/N6/Ger. **Best-effort, always emits.**  

**Harmonyx** = RN → full SATB with **hard DP**, MusicXML, locked fixtures,
fail-closed.  

**Steal:** phrase splits, residual flags, vocab checklist, best-effort *mode*
ideas. **Don’t steal:** default search replacement, static chord table, desktop
stack, silent residual violations.

---

*End of deep-dive #04. Next research default when asked: #05 choral-llm-workbench.*
