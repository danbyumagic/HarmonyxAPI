# Research note: choral-counterpoint (DashWieland)

**Date:** 2026-07-21  
**Repo:** https://github.com/DashWieland/choral-counterpoint  
**Live instrument:** https://apophenia.blog/work/choral-hurdy-gurdy  
**Status:** Tier S deep-dive #2 — SATB rules engine + Bach oracle peer  
**Source:** README, `check_chorale.py` (full), `compose.py` (pipeline + structure),
`serve.py`, `validate_checker.py`, `cleanroom_eval.py`, SKILL.md chorale sections.

---

## 1. What it is

A **fully automatic, deterministic SATB chorale composer** (plus Fux species-1):

- No LLM at runtime (origin story: Claude *skill* with checkers → pure search).
- Hard voice-leading checker + **Bach corpus outer-voice oracle** + beam search.
- Three deliverables: Python skill/scripts, `engine/` composer + HTTP server,
  dependency-free JS “Choral Hurdy-Gurdy” music box.

**Vs Harmonyx:** they compose **notes from a melody/soprano** (or invent one).
Harmonyx composes **notes from a Roman-numeral progression**. Same classical
voice-leading problem; **different control surface** (melody-first vs RN-first).

---

## 2. Architecture layers

```
.claude/skills/choral-counterpoint/   # “musical knowledge” authored here
  SKILL.md                            # workflows + veto loop for LLM users
  scripts/check_chorale.py            # SATB hard/soft checker
  scripts/check_species1.py           # Fux first species
  scripts/oracle_outer.py             # Bach outer-voice lookup
  scripts/ornament.py                 # corpus-rate figuration after skeleton
  data/outer_voice_table.json         # ~16,852 S-transitions → bass responses
  data/melody_table.json              # cadence formulas + melodic transitions
  data/ornament_table.json

engine/
  compose.py   # melody → bass beam → AT beam → check → ornament (~30 ms)
  serve.py     # /compose, /compose.mid, /next, POST /harmonize
  chords.py

tools/
  mine_oracle.py, mine_ornaments.py, mine_melody.py   # need music21
  validate_checker.py   # false-alarm rate of checker ON Bach
  cleanroom_eval.py     # leave-one-out: harmonize Bach soprano, score vs Bach

instrument/web/   # JS port + WebAudio
```

**Key product claim:** piece *N* for fixed params+seed is **identical forever**
(reproducible infinite composition).

---

## 3. Composition pipeline (`engine/compose.py`)

| Stage | Role | Constraint style |
|-------|------|------------------|
| 1. `melody()` | Phrase-planned soprano (or fixed given melody) | Corpus-weighted steps; cadence formulas from Bach; fermatas at phrase ends |
| 2. `bass_line()` | Beam search over **oracle** moves | Zero-support moves **hard-excluded**; dyad must be harmonizable; line-shape scoring vs “root-position seesaw” |
| 3. `harmonize()` | Alto/tenor + chord beam | VL laws hard; LT up, 7ths down, never double LT; chromatic targets; false-relation penalty |
| 4. `check_chorale` | Final gate | Failures discarded → recompose with annealed temperature |
| 5. `ornament()` | Optional figuration | Corpus rates; reject if new rule break |

Also: **POST `/harmonize`** — user supplies soprano + fermatas; 422 if cannot
harmonize cleanly.

This is closer to a **melody harmonizer** than to Harmonyx’s RN realizer, but
the **checker + calibration culture** is directly portable to M4 `/check`.

---

## 4. Checker design (`check_chorale.py`) — most important for us

### Input

JSON: `tonic`, `mode`, parallel arrays `soprano/alto/tenor/bass` (note names or
MIDI after conversion), optional **1-indexed `fermatas`**.

### Hard VIOLATIONS (exit 1)

| Rule | Notes |
|------|--------|
| Parallel 5ths / 8ves | All 6 pairs; both voices move same direction into same perfect IC; **within phrase only** |
| Leap > octave | Melodic |
| Leap of 7th | Melodic |
| Augmented 2nd | Minor mode, between relative pcs 8 and 11 (♯6–♯7 type) |

### WARNINGS (never fail alone)

| Rule | Calibration rationale |
|------|----------------------|
| Voice crossing | Bach trips often enough → warning |
| Spacing S–A / A–T > octave | Same |
| Out of range | Warning not hard |
| Antiparallel perfects | Soft |
| Direct 5ths/8ves (outer, soprano leap) | Soft |
| Overlap | Soft |
| Melodic tritone | Soft |
| Doubled leading tone | Soft — **no local-key tracking**; V-of-tonic pc-identical to I-of-dom |
| Unresolved cadential LT (outer) | Soft |
| **Anything across fermata boundary** | Parallels etc. demoted to warning |

### Ranges used (MIDI)

| Voice | Low | High |
|-------|-----|------|
| S | 60 | 81 |
| A | 53 | 74 |
| T | 48 | 69 |
| B | 36 | 62 |

Harmonyx (`PARTWRITING-RULES` §0) is slightly different (e.g. S C4–G5 = 60–79,
B E2–C4 = 40–60). Worth a deliberate comparison table later — not automatic
merge.

### Calibration culture (steal this)

`tools/validate_checker.py` runs the checker on **music21 Bach chorales** and
counts residual violations. Design rule:

> Rules Bach trips at material rates → **warnings**.  
> Parallel perfects / big leaps → **hard**.  
> Target residual ~0.24 violations/chorale; every residual category explained.

This is how they avoid textbook-only over-strictness. Harmonyx currently uses
**locked hand fixtures** (correct for pedagogy product) but has **no Bach
false-alarm suite**. Adding something like `validate_checker` would be gold for
M4 credibility.

---

## 5. Oracle philosophy

**Claim:** chord symbols are the wrong representation for “what Bach would do”;
the signal is in **outer-voice transitions** (soprano move → bass responses).

- Table: ~16,852 transitions from ~345 chorales.
- Compose-time: zero-support bass moves **excluded** (corpus veto).
- Skill workflow: greedy top-of-oracle collapses to root-position seesaw —
  human/beam **vetoes for line shape**.

Harmonyx does **not** have an outer-voice oracle; we have RN grammar +
transition costs. Possible future research: mine Bach (or When-in-Rome) for
**RN transition frequencies** as soft weights — different representation,
same “corpus taste” idea.

---

## 6. Eval they already built

| Tool | What it measures |
|------|------------------|
| `validate_checker.py` | False alarms of VL rules on real Bach |
| `cleanroom_eval.py` | Leave-one-out: remove test chorale from oracle, harmonize soprano, score bass-pc / chord-pc-set / “harmony” vs Bach |
| Engine batch claim | 24/24 clean across 6 keys × both modes; JS 200/200 clean |

Cleanroom metrics (documented in script comments): earlier round ~60% exact
chord / 73% same-harmony on simple melody; “Ein’ feste Burg” harder.

Harmonyx eval today: RN round-trip + hard violations on fixtures
(`eval/run_generation_eval.py`). No leave-one-out Bach harmonization (different
task).

---

## 7. HTTP API surface

| Endpoint | Role |
|----------|------|
| `GET /compose?tonic&mode&phrases&seed…` | Full piece JSON |
| `GET /compose.mid` | MIDI |
| `GET /next` | Stateful next piece + compose-ahead buffer (~40s play vs 30ms compose) |
| `POST /harmonize` | Given soprano (+ fermatas) → SATB or 422 |

Instrument-friendly design (buffer so crank never waits). Different product
than Harmonyx FastAPI, but **compose-ahead** is a nice pattern if we ever stream
generate/play.

---

## 8. Rule comparison: choral-counterpoint vs Harmonyx

| Rule | Harmonyx (`rules.py` / PARTWRITING-RULES) | choral-counterpoint |
|------|-------------------------------------------|---------------------|
| Range | **Hard** | Warning |
| Spacing S–A, A–T ≤ 8ve | **Hard** | Warning |
| Crossing | **Hard** | Warning |
| Overlap | **Hard** | Warning |
| Parallel 5/8 | **Hard** | **Hard** (within phrase) |
| Direct 5/8 outer | **Hard** | Warning |
| Leading tone resolve | **Hard** on V→I outer | Warning at cadence/fermata |
| Doubled LT | **Hard** | Warning (modulation caveat) |
| Doubled 7th | **Hard** | Handled in harmonize search more than checker |
| Fermata / phrase break | Not modeled in realizer | **First-class** — softens rules across boundary |
| Ornamentation | None (skeleton only) | Post-process with re-check |
| RN / inversions / Cad64 | Core product | Implicit via outer dyads + chord vocabulary |
| Soft doubling preferences | Cost function §7 | “Double root, never LT” in search |

**Interpretation:** Harmonyx is **stricter and more textbook / Theory-I** —
appropriate for student-safe defaults. choral-counterpoint is **Bach-calibrated
and phrase-aware** — better for “sounds like Bach” infinite generation.

Neither is wrong; a king-of-domain stack might eventually support
`strictness: student | bach` profiles.

---

## 9. Concrete takeaways for Harmonyx

### High value (esp. M4 `/check`)

1. **Violation vs warning split** with documented calibration story.
2. **False-alarm suite on Bach** (`validate_checker` pattern) — prove checker
   doesn’t spam real music.
3. **Fermata / phrase-boundary awareness** — analyzer + check both care; our
   cadence detection already wants fermatas (ROADMAP A2).
4. **JSON SATB score shape** for checker input — portable API for `/check`.
5. **Exit codes / structured VIOLATION vs warning lists** for UI color-coding
   (PartWise-style).

### Medium value (generate path)

6. Outer-voice oracle ≠ RN realizer, but **corpus soft weights** for transitions
   could enrich `transition_cost` beyond hand weights.
7. Ornamentation layer **after** verified skeleton — future “spicy surface”
   without breaking hard rules.
8. Deterministic seed + “piece N forever” branding.

### Low / different product

9. Melody-first compose loop — only if we add “harmonize this tune.”
10. JS full-engine port — nice demo, not needed for API-first Harmonyx.

### Philosophical alignment (keep)

Both projects agree: **checkable rules + corpus taste + never trust unchecked
notes**. choral-counterpoint’s origin (LLM skill → pure engine) is the same
story as Resonance / Harmonyx L path.

---

## 10. Risks / caveats

- Young repo (mid-2026), 0★ — design quality high; community unproven.
- Doubled-LT and local key are explicitly under-modeled (warnings only).
- Oracle is global-key degrees — modulation blurs counts (documented).
- Not MusicXML-native (JSON + MIDI); Harmonyx already owns MusicXML/OSMD path.
- Ranges/rule hardness differ — **do not copy rules into locked fixtures**
  without human review (fixtures are the law per AGENTS.md).

---

## 11. Links

| Our asset | Connection |
|-----------|------------|
| `docs/PARTWRITING-RULES.md` | Compare §0–§5 to their V/W split |
| `app/generation/rules.py` | Implementation twin of `check_chorale.py` |
| `tests/test_partwriting.py` | **Locked** — never edit to match their looser ranges |
| M4 `POST /check` | Product direction closest to their checker + UI peers |
| Q4 analyzer fermatas | Phrase-boundary idea shared |
| `docs/research/01-resonance.md` | LLM side of the same “governed generation” thesis |

---

## 12. Open questions (for human)

1. For M4, prefer **student-hard** (current rules) or **Bach-calibrated**
   warning tiers?
2. Worth investing a session in a Bach false-alarm script (read-only eval,
   no fixture edits)?
3. Ever want **soprano-in harmonize** as a second generate mode, or stay RN-first?
4. Should landscape “king” roadmap include species counterpoint pedagogy, or
   stay hymn/RNA focused?
