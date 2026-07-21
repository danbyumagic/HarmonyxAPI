# Research note: music-arranger (scarrow)

**Date:** 2026-07-21
**Repo:** https://codeberg.org/scarrow/music-arranger (moved off GitHub; formerly
`git-scarrow/music-arranger`)
**Author:** scarrow (single author)
**Status:** Tier 1 peer #2 (per `docs/RESEARCH-QUEUE.md`) — "L4 + realizer, one
architecture" twin: Claude tool-call NL extraction feeding a **Google OR-Tools
CP-SAT constraint solver** instead of Harmonyx's grammar+DP pipeline
**Source:** repo file listing, `music_arranger.py`, `solver_template.py`,
`verify_solver.py`, `verify_barbershop.py`, `theory_definitions.json` (all
read via raw file fetch, no local clone). No `README.md` found in the repo
(404) — architecture reconstructed from source + inline docstrings only.
**Meta:** 0★, single author, 12 commits, actively maintained (latest commit
June 2026), moved from GitHub to Codeberg. 100% Python. No LICENSE file found
in the listing — **treat as all-rights-reserved by default; cite ideas, do
not vendor code** until a license is confirmed.

---

## 1. What it is

A two-stage pipeline: **Claude extracts structured arrangement parameters
from natural language** (forced tool-call, not free-text parsing), then a
**CP-SAT constraint solver** (Google OR-Tools) finds a feasible/optimal SATB
(or barbershop 4-voice) voicing satisfying those parameters. This is the
closest peer yet to Harmonyx's own L4 plan (LLM → structured RN/parameters →
deterministic engine → MusicXML) — same "LLM proposes, code enforces"
philosophy — but the deterministic engine is a **declarative constraint
solver** instead of Harmonyx's **DP/Viterbi-style realizer** (`app/generation/
realize.py`). This is the one concrete architectural fork worth studying: two
different solutions to the same "find a valid four-voice assignment"
problem.

**Vs Harmonyx:** `RequestMapper` (NL → `apply_arrangement` tool call) is a
direct analogue of the not-yet-built L4 LLM client in
`docs/LLM-PROGRESSION-SPEC.md` — except this repo's Claude call extracts
**explicit chord/voicing parameters** (key, scale, cadence, chord_sequence
with per-chord quality/inversion, voice-leading limits) in one shot, closer
to Harmonyx's `POST /generate` input than to `POST /progression`'s
RN-list-only contract. `ArrangerSolver` is the peer to `realize.py` +
`rules.py` combined: the CP-SAT model encodes hard constraints (harmonic
membership, no-crossing, leap limits, scale membership, chord completeness,
bass restriction) exactly as `AddAllowedAssignments`/`AddAbsEquality`/
`AddBoolOr` calls, and soft constraints (doubling, spacing, parallel-octave
avoidance, resolution, common-tone retention, tessitura, stepwise motion,
contrary motion) as `model.Maximize(sum(objective_terms))` — i.e. **one
combined optimization pass** rather than Harmonyx's DP scoring function.

---

## 2. CP-SAT constraint solving vs. Harmonyx's DP realizer

This is the actionable comparison research #04 (chorale-optimizer, beam
search) already opened and this repo extends on a different axis:

| Approach | How it searches | Where it's used |
|---|---|---|
| Harmonyx `realize.py` | Sequential DP/Viterbi: score each step's chord-tone assignment against the previous step, backtrack for best path | Product default, fail-closed, locked by `tests/test_partwriting.py` |
| chorale-optimizer (#04) | Beam search (w=40) + ≤6 iterative rule-based fixup passes | Best-effort, always-emits |
| music-arranger (this repo) | **CP-SAT**: declare all voice/step variables + all constraints at once, let the solver search the full combinatorial space for a feasible (or objective-maximizing) global assignment | This repo's only path |

The genuinely new idea here (not present in #04 or Harmonyx today):
**global constraint satisfaction instead of sequential/local scoring.** DP is
inherently sequential — a step's cost only "sees" the immediately adjacent
step(s), so cross-cutting constraints spanning the whole phrase (e.g.
"exactly one voice must carry the 7th across all four steps of this
progression," global spacing envelopes, contrary-motion preferences that span
non-adjacent steps) require CP-SAT's ability to reason about the whole
variable set jointly. `verify_solver.py`'s **diagnostic layer** is the other
concrete idea worth naming: `validate()` runs *pre-solve* checks (empty
domain detection, melody-scale conflicts, cadence-length truncation,
perfect-authentic-cadence-vs-pinned-melody conflicts) and reports *which*
constraint made the problem infeasible, rather than just returning
"no solution." Harmonyx's realizer currently just fails or returns its best
path — there's no equivalent "here's specifically why this failed" diagnostic
surfaced to the API or UI.

**Not a case for replacing the DP realizer.** CP-SAT is a heavier dependency
(Google OR-Tools, C++ backend) for a benefit (global joint optimization) that
Harmonyx's currently-scoped rule set doesn't obviously need — the DP
approach's local-adjacency assumption holds fine for the rules already in
`PARTWRITING-RULES.md` §0–7 (all of which are checkable one-or-two-steps-back:
parallel 5ths/8ves, leap resolution, doubling, spacing). The locked DP +
`test_partwriting.py` fixtures stay as-is per `AGENTS.md` Rule 4. File this as
a **"if Harmonyx's rule set ever grows a genuinely non-local constraint"**
signal, not a near-term rewrite case.

---

## 3. Diagnostics: the concretely stealable idea

`verify_solver.py`'s failure-mode reporting is the single most directly
applicable finding, independent of DP-vs-CP-SAT:

- **"Melody outside scale"** — pinned melody note conflicts with harmonic
  constraint → empty domain, reported *before* attempting to solve.
- **"Voice leading too tight"** — a mandatory pitch jump between two pinned
  or heavily-constrained steps exceeds the max-interval limit.
- **"Empty domain conflict"** — two harmonic constraints at the same step are
  mutually exclusive (e.g. C major + D major).
- **"Cadence truncation"** — a multi-step cadence formula doesn't fit in the
  remaining problem length.
- **"Perfect authentic vs. melody"** — soprano-on-root cadence requirement
  contradicts a pinned non-tonic melody note.

Each of these is a **named, specific reason a request is infeasible**,
surfaced before the solver even runs. Harmonyx's M4 `POST /check` (not yet
built; blueprint is research #03 PartWise) and the existing L2 validator
(`app/generation/validate.py`) are the two places this pattern is most
relevant: `validate_progression` already returns violations, but a similarly
**named, pre-flight, "why would this fail" check** (as opposed to
post-hoc violation listing) could be a useful shape for M4's evaluate
endpoint, or for `POST /generate`/`POST /progression` error responses when a
user-supplied RN sequence is unrealizable given other constraints (e.g. a
locked soprano note that's not a chord tone of an adjacent locked RN).

---

## 4. Chromatic/barbershop soft-vs-hard scale handling

`verify_barbershop.py` confirms a pattern already present in Harmonyx's own
`spice`/`style` design (Q3b/Q3c) but validates it from an independent
direction: **hard scale constraint rejects chromatic secondary dominants;
soft scale constraint (diatonic-preference-as-objective-term, not
prohibition) allows them.** This is architecturally the same idea as
Harmonyx's `scale_constraint_hard` toggle maps to `spice` level — useful as
independent confirmation that "soft preference + explicit chromatic
allowance" is the right shape for opt-in richer harmony, not a new idea to
adopt.

---

## 5. Tool schema — NL-to-parameters, not NL-to-RN-list

Worth flagging as a **design contrast**, not a steal: this repo's Claude tool
schema (`apply_arrangement`) extracts a *fully specified* arrangement
(key, scale, cadence, per-step chord root/quality/inversion,
voice-leading limits, completeness/doubling toggles) in a single tool call.
Harmonyx's L4 plan (`docs/LLM-PROGRESSION-SPEC.md`) and research #01
(resonance) both converge on **LLM emits Roman numerals only**, with
everything else (voicing, doubling, spacing) left to the deterministic
realizer downstream. This repo's wider single-call schema is more expressive
but couples the LLM's output more tightly to solver internals (explicit
`voice_leading_max_interval`, `enable_chord_completeness` flags in the tool
schema) — a tighter, harder-to-validate contract than Harmonyx's
RN-list-plus-separate-realizer split. **Don't steal the wide-schema
approach** — Harmonyx's existing "LLM emits RN only, everything else is a
separate deterministic stage" design (validated independently by resonance,
#01) is the better-separated contract and should stay the L4 plan.

---

## 6. Steal / don't-steal

**Steal (ideas, not code — no confirmed license):**
- The **pre-solve diagnostic pattern** (§3): named, specific infeasibility
  reasons surfaced before/instead of a bare failure — relevant to M4
  `POST /check` design and to improving `POST /generate`/`POST /progression`
  error responses when a request is unrealizable.
- The **soft-vs-hard scale constraint duality** (§4) as independent
  confirmation that Harmonyx's `spice`/`style` soft-preference design (Q3b/c)
  is the right shape — no change needed, just validates the existing choice.
- Filing "global constraint solving (CP-SAT)" as the answer *if* Harmonyx's
  rule set ever needs genuinely non-local constraints the DP realizer's
  adjacency assumption can't express (§2) — not needed today.

**Don't steal:**
- Replacing the DP realizer with CP-SAT/OR-Tools — heavier dependency,
  no evidence the currently-scoped rule set needs global constraint solving;
  locked `test_partwriting.py` fixtures already prove the DP path is correct
  for the scoped rules (`AGENTS.md` Rule 4).
- The wide single-tool-call NL→full-arrangement schema (§5) — Harmonyx's
  narrower "LLM emits RN only" L4 contract (also validated by resonance, #01)
  is better-separated and should stay the plan.
- Any literal code — no LICENSE file found in the repo; treat this as
  all-rights-reserved and cite architecture only, don't vendor.

## 7. Open questions

- Does M4 `POST /check` want a pre-solve-style "named infeasibility reason"
  response shape (§3), or is post-hoc violation listing (PartWise's model,
  research #03) sufficient? Worth deciding when M4 is actually scoped, not
  now.
- If a license is ever added to the Codeberg repo, worth a second look at
  whether any of `theory_definitions.json`'s secondary-dominant/cadence
  encoding is directly reusable data (not just an idea) — parked until then.
