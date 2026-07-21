# Spec: Richer rule grammar (Q3)

**Status:** design / not implemented.  
**Date:** 2026-07-21.  
**Do not implement this entire doc in one session.** Work one named chunk
(Q3a / Q3b / Q3c) only, after the user approves.

Related:

- Current grammar: `app/generation/grammar.py` (PARTWRITING-RULES §9)
- Validator / fixer (already shippable for non-grammar RNs):  
  `app/generation/validate.py`, `app/generation/fix.py`  
  (LLM path L1–L3 — see `docs/LLM-PROGRESSION-SPEC.md`)
- Open queue ID: **Q3** in `docs/START-HERE.md`

---

## 1. Goals

- Make **default offline** `POST /progression` / `generate_progression` feel
  less Theory-I vanilla **when the user opts in**.
- Keep a **student-safe default** (no surprise secondary dominants).
- Stay **rule-based** — no LLM, no training.
- Emit only figures the realizer can typically voice (parseable + usually
  `validate_progression(..., check_engine=True)`).

## 2. Non-goals (v1)

- Modulation / multi-key regions.
- Full seventh-stack soup (`ii65`, `V43`, …) as a first pass.
- Replacing or weakening locked `tests/test_partwriting.py`.
- LLM proposer (L4+) — parallel track; grammar remains its fallback.
- Silent overwrite of user `locked` slots.
- Analyzer improvements (Q4) or `POST /check` (Q2).

---

## 3. Current state (why it feels bland)

Weighted Markov walk over a small table:

| Present | Sparse / missing |
|---------|------------------|
| I / IV / V / vi / ii / iii (+ minor analogues) | Few *paths into* inversions |
| Some inversions: I6, ii6, IV6, V6 | Cad64 rarely entered |
| V7, viio6, mid-phrase deceptive | **No** secondary dominants (`V/V`, …) |
| PAC / HC hard cadence end | No API spice / style knob |

**API today:** `{ key, length, locked?, cadence?, seed? }` only.

L1–L3 already **accept** spicier RNs for validation/fix; the **generator**
still cannot emit them.

---

## 4. Design principles

1. **Default stays safe.** Omitting new fields → student-safe, near-current
   behavior (see Q3a note on mild inversions).
2. **Opt-in spice.** Explicit `spice` and/or `style` for richer output.
3. **One house law.** Reuse `FORBIDDEN_TRANSITIONS` / L2; extend tables, do not
   invent a second rule system.
4. **Realizable first.** New figures must parse in music21; smoke-test realize.
5. **Determinism.** Same
   `(key, length, cadence, seed, spice, style, locked)` → same progression.

---

## 5. Recommended API (when Q3b lands)

```text
spice: int = 0   # 0..3
# optional alias later:
style: "student" | "hymnal" | "spicy"   # maps to spice; style wins if both set
```

| Value | Intent | Grammar behavior |
|-------|--------|------------------|
| `spice=0` / `student` | Homework-safe | Near current table; **no** secondary dominants. Q3a may add *mild* inversion weight only if tests stay green. |
| `spice=1` / `hymnal` | Church / chorale color | More I6/ii6/IV6/V6; Cad64 → V before PAC when length allows. |
| `spice=2` / `spicy` | Noticeably less vanilla | Occasional `V/V`, `V7/V`, `V6/V` (low weight). |
| `spice=3` | Max offline color | Also rare `V/vi`, `V/ii` (major) + careful minor analogues. |

**Response:** echo `spice` / `style` on `ProgressionResponse` when accepted.

**Default:** `spice=0` so existing clients and tests do not suddenly get applied chords.

---

## 6. Chunk boundaries (implement one per session)

### Q3a — More inversions + Cad64

**What**

- Raise weights / add edges so phrases use **I6, ii6, IV6, V6** more often.
- Add approach edges into **Cad64 → V|V7** before PAC when length allows and
  cadence slots are free.
- Figure set stays ⊆ today’s major/minor pools (**no** applied chords).

**API:** none required. Optional internal weight pack only.

**Done when**

- Seeded tests: for length ≥ 6 PAC, a modest share of seeds contain an
  inversion and/or Cad64 (e.g. ≥ ~30% over 20 seeds — tune in tests).
- Zero forbidden edges; PAC/HC still hard.
- Existing grammar + `/progression` tests green (prefer **new** tests over
  rewriting old determinism cases; update golden sequences only if unavoidable).

**Risk:** low.

---

### Q3b — Secondary dominants + `spice` API

**What**

- Add at least `V/V`, `V7/V`; prefer also `V6/V`. Optional later in same epic:
  `V/vi`, `V/ii` behind `spice=3`.
- House transition shapes:
  - … → `V/V` | `V7/V` | `V6/V` → `V` | `V7` (not → IV/ii).
  - … → `V/vi` → `vi` → … (if enabled).
  - Never final chord; never break PAC penultimate (`V`|`V7` only).
- Low Markov weights unless `spice >= 2`.
- Wire `spice` (and optional `style`) through `generate_progression`,
  `ProgressionRequest` / `ProgressionResponse`, `POST /progression`.

**Done when**

- `spice=2`, length 8: **some** seeds emit `V/V` or `V7/V` (e.g. ≥ 1 of 20).
- `spice=0`: **zero** secondary dominants (hard regression test).
- Sample spicy outputs pass L2 theory gate; smoke realize path.
- Endpoint accepts and echoes `spice`.

**Risk:** medium (applied chords stress voicing). Keep weights modest; rely on
existing `_MAX_ATTEMPTS` retries.

---

### Q3c — Style presets + polish

**What**

- Named presets as weight packs (not new engines): `student` / `hymnal` /
  `spicy` → spice mapping above.
- Docs: STATUS / START-HERE; PARTWRITING-RULES §9 appendix or “§9b extended
  figures” note so agents do not thrash code vs doc.
- Frontend dropdown **optional** — only after Q3b API is stable; skip in first
  Q3c if user wants backend-only.

**Done when**

- One integration test per preset (or spice level).
- Manual smoke: Propose → Realize for each preset (if UI touched).

**Risk:** low if Q3a/b done.

---

## 7. Seams (where bugs hide)

| Seam | Care |
|------|------|
| Grammar ↔ L2 `validate_progression` | New edges must not be house-forbidden; applied chords already allowed by theory gate. |
| Grammar ↔ realizer | After Q3b: generate N spicy → realize smoke test. |
| Grammar ↔ L3 fixer | Optional later: add `V/V` to fixer pools; not blocking Q3. |
| API ↔ frontend | Old clients omit `spice` → 0. |
| Determinism | Include spice/style in seed identity. |
| §9 doc vs code | Document extended figures so PARTWRITING-RULES does not fight the table. |

---

## 8. Explicit product defaults (agreed for implementation unless user overrides)

1. **First implement:** Q3a, then Q3b, then Q3c (separate sessions / check-ins).
2. **API knob:** integer `spice` 0–3; optional `style` alias in Q3c.
3. **Default spice = 0** (no secondary dominants).
4. **Q3b applied set v1:** `V/V`, `V7/V`, `V6/V`; `V/vi` / `V/ii` only at spice 3.
5. **Frontend:** not required for Q3a/b; optional in Q3c.

---

## 9. Success criteria (Q3 feature-complete through Q3c)

1. Default path: PAC/HC legal, no forbidden edges, full pytest green.
2. Opt-in spice: more inversions; occasional secondary dominants at spice ≥ 2.
3. Propose → Generate does not 500 on typical spicy outputs.
4. No regression: generation eval fixtures, locked partwriting tests untouched.
5. LLM track still valid: grammar remains L4/L5 fallback and offline default.

---

## 10. Out of scope reminders

| Item | Track |
|------|--------|
| Corpus / validator / fixer | L1–L3 **done** (code); do not re-do |
| LLM client | L4+ |
| `POST /check` | Q2 |
| Analyzer NCT / key | Q4 |

---

## 11. New-chat paste (Q3 work)

> Read `docs/START-HERE.md`, `AGENTS.md`, and `docs/RICH-GRAMMAR-SPEC.md`.
> Then **stop and wait** for my instructions — do not start implementing
> anything yet. When I say go, implement **only** the named chunk (Q3a, Q3b,
> or Q3c).
