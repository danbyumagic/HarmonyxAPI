# Research note: choral-llm-workbench (asb-42)

**Date:** 2026-07-21
**Repo:** https://github.com/asb-42/choral-llm-workbench
**Author:** asb-42
**Status:** Tier peer #5 — MusicXML + local-LLM choral transformation tool
**Source:** README, `USER_MANUAL.md`, `SYSTEM_PROMPTS.md`, `ARCHITECTURE-VUE.md`,
`CHANGELOG.md`, `KNOWN_ISSUES.md`, `docs/system/ROADMAP-v2.md`; full read of
`ikr_light.py`, `tlr_converter.py`, `transformation_validator.py`,
`core/llm/adapter.py`, `core/llm/satb.py`, `core/score/reharmonize.py`; ran
`pytest tests/test_functional.py` (4 passed) and `pytest tests/` (11 collection
errors — syntax error, missing `hypothesis` dep, broken constructor calls).
**Meta:** 0★, pushed 2026-02-23, MIT license. Mixed stack: Python core +
Gradio (legacy) + NestJS backend + Vue 3 frontend, all present simultaneously.

---

## 1. What it is

A **deterministic-transformation-engine-with-optional-LLM-assist** for choral
scores, aimed at professional choir conductors/arrangers rather than students:

1. Load a MusicXML choral score (music21-parsed).
2. Convert to an internal canonical model, **IKR-light** (Score → Part →
   Voice → Measure → Event; events are `Note` / `Rest` / `Harmony` / `Lyric`).
3. Serialize IKR-light to **TLR** (Textual LLM Representation) — one
   fully-explicit event per line, e.g. `NOTE t=0 dur=1/4 pitch=G4`,
   `HARMONY t=0 symbol=V7 key=C major`.
4. Send TLR + a **transformation-flag-gated system prompt** to a local LLM
   (Ollama, default `mistral-7b`); LLM returns modified TLR.
5. Parse TLR back to IKR-light, run a **`TransformationValidator`** hard
   barrier, diff old/new, re-emit MusicXML.

Explicit design stance (`docs/system/ROADMAP-v2.md`): *"LLM never enforces
rules; it proposes changes. All musical legality is enforced outside the
LLM."* — the same L4 philosophy Harmonyx already committed to (RN-only LLM
output + validate/fix gates), independently arrived at.

**Vs Harmonyx:** different product surface (whole-score *transformation* of
an existing choral piece — transpose / simplify / reharm / style-change —
vs Harmonyx's RN-list-to-SATB *generation* and RN progression *analysis*).
Closest conceptual overlap is **L4** (gated LLM proposing musical content)
and a **future reharm/arrange track** (§11 of the landscape doc), not
current Generate/Analyze.

---

## 2. IKR-light + TLR — the one idea worth stealing

`ikr_light.py` (61 lines) is a minimal dataclass model: `NoteEvent(onset,
duration, pitch_step, pitch_alter, octave, tie)`, `RestEvent`,
`HarmonyEvent(onset, harmony, key)`, `LyricEvent`, grouped under
`Measure → Voice → Part → Score`. Nothing surprising architecturally, but
`tlr_converter.py` turns it into a **plain-text, line-oriented, fully
explicit** serialization — no implicit defaults, no nesting — designed
specifically to be:

- **LLM-legible without a schema** (no JSON/XML escaping, no ambiguity about
  what "empty" means — everything explicit per line),
  - **Deterministically round-trippable** (`ikr_to_tlr` sorts parts/voices/
    measures/events for stable output; `tlr_to_ikr` is a straight line parser).
- **Diffable** — because it's line-per-event text, a plain `difflib`-style
  diff over TLR lines is a musically meaningful diff (their "Professional
  Diff Viewer" is just text diffing over TLR, not a custom score-diff algo).

This is a **different interface choice than Harmonyx's L4 plan** (structured
RN JSON per `docs/LLM-PROGRESSION-SPEC.md`) and than Resonance (`#01`, also
JSON). RN JSON is *higher-level* (theory objects); TLR is *lower-level*
(literal note/rest/harmony events) — apples to oranges for L4 chord-symbol
generation, but **directly relevant if/when Harmonyx ever needs an LLM to
touch note-level score content** (e.g. a future "explain this passage" or
"reharmonize this existing chorale" feature) rather than only RN symbols.

---

## 3. Transformation gating (`transformation_validator.py`)

A **hard barrier** pattern: four named transformation flags
(`transpose`, `rhythm_simplify`, `style_change`, `harmonic_reharm`), each with
an explicit `allowed_changes` / `forbidden_changes` list. The system prompt
is built *only* from active flags (`get_transformation_prompt_additions`) —
the LLM is told the literal allow-list and instructed to "reject requests
for transformation types not in the allowed list." Post-hoc, the validator
independently re-checks the returned score (e.g. transposition must preserve
duration/onset and use one consistent interval across all notes; harmonic
reharm must preserve melody pitch/rhythm/onset).

**Comparison to Harmonyx L2/L3:** conceptually the same shape as
`validate.py` + `fix.py` (gate LLM output against explicit rules,
deterministically), but scoped to *note-level* transformations of an
existing piece rather than *RN-level* generation. Worth a look if a future
Harmonyx feature does "LLM edits an existing score" rather than "LLM
proposes a fresh progression."

**Weakness to note, not copy:** the actual rule bodies are thin — e.g.
`_validate_harmonic_reharm` computes `orig_midi`/`trans_midi` per note but
then does nothing with them (`pass`); `_validate_style_change` only checks
part/measure counts, not "musical integrity" despite the docstring. The
*pattern* (flag-scoped allow-list → prompt injection → independent
post-validator) is sound; the *rule content* is a stub, unlike Harmonyx's
locked `test_partwriting.py` fixtures.

---

## 4. LLM harmonization itself — thin

`core/llm/adapter.py` / `core/llm/satb.py`: harmonization is **one chord per
measure**, described only as `{measure, root, quality}` (`major`/`minor`/
`dim` triads only — no sevenths, no inversions, no voice leading between
consecutive chords). `core/score/reharmonize.py`'s `make_chord`/
`replace_chord_in_measure` builds a block triad and drops it into the
measure; there is no SATB voice-leading logic anywhere in the repo — despite
"SATB" appearing throughout filenames (`gradio_app_satb_*.py` ×13 variants).
This is a **prompt/chord-symbol harmonizer for a monophonic or homorhythmic
line**, not a four-part realizer. Harmonyx's `realize.py` (hard DP,
locked voice-leading rules) is materially more advanced on this specific
axis — nothing to steal here, just confirms Harmonyx's realizer is ahead
of this peer on the actual part-writing problem.

---

## 5. Repo health (signal, not just code)

- **Working tree sprawl**: 20 near-duplicate `cli/gradio_app_satb_*.py`
  files (`_ghosts`, `_enhanced`, `_fixed`, `_working`, `_ultra_minimal`,
  `_session`, …) alongside `app.py` **and** `app.py.backup`, plus a fully
  separate NestJS (`backend/`) + Vue 3 (`frontend/`) stack described in
  `ARCHITECTURE-VUE.md` as *replacing* the Gradio UI — but the Gradio files
  are all still present and referenced from the README's own Quick Start.
- `KNOWN_ISSUES.md` self-documents an **"URGENT: ABANDON GRADIO APPROACH —
  FUNDAMENTAL INCOMPATIBILITY"** framework migration mid-project.
- CI (`ci.yml`) only runs `pytest tests/test_functional.py` (4 tests) plus
  `black`/`mypy`/`flake8` over the whole tree — **not** the other 24 test
  files. Running the full `tests/` directory myself hit **11 collection
  errors**: a hard `IndentationError` in `test_roundtrip.py`, a missing
  `hypothesis` dependency (`test_property_negative.py`), and a broken
  `EditorSession.__init__()` call in `test_ghosts.py`. The green CI badge
  reflects a narrow slice, not repo health.
- `CHANGELOG.md` claims a shipped "v1.1.0 — Professional UX Features"
  release with polished bullet points (Helmholtz notation, diff viewer,
  hard validation barriers) that read as aspirational/marketing relative to
  the actual code depth found above.

**Reading of this peer overall:** a personal/exploratory project with a
genuinely good architectural idea (IKR-light + TLR + flag-gated validator)
buried in heavy churn and incomplete follow-through elsewhere. Treat the
*pattern*, not the code, as the reusable artifact — do not vendor anything
from this repo.

---

## 6. Comparison matrix vs Harmonyx

| Dimension | choral-llm-workbench | Harmonyx |
|-----------|----------------------|----------|
| Product | Transform an *existing* choral score | Generate SATB from RN; analyze score→RN |
| LLM interface | TLR (line-per-event text) | RN JSON (planned, L4) |
| Gate pattern | Flag allow-list → prompt → post-validator | validate.py + fix.py (L2/L3, done) |
| Harmonization depth | 1 chord/measure, triads only, no voice leading | Full SATB hard-DP realizer, locked fixtures |
| Score I/O | MusicXML in/out via music21 | MusicXML in/out via music21 |
| UI | Gradio (legacy) + Vue3/NestJS (in-progress, overlapping) | Single web frontend, OSMD, Play/Stop |
| Tests | 25 files; CI runs 1; full suite fails to collect | Locked fixtures pass; CI wired to M2 eval |
| License | MIT | Project's own |
| Maturity | Sprawling, self-documented mid-migration | Productizing, narrower scope, stricter gates |

---

## 7. Steal / don't-steal

### High value (ideas)

1. **TLR-style plain-text event serialization** as an option for any future
   feature where an LLM must read/write literal note-level score content
   (not chord symbols) — explicit, sorted, diffable, no schema needed.
   Keep as a **later** idea for a reharm/arrange or "explain this passage"
   track, not for current RN-based L4.
2. **Flag-scoped prompt construction** (`get_transformation_prompt_additions`)
   — only inject allowed-operation text into the system prompt for the
   operations actually requested. Applicable pattern for Harmonyx L4 if
   propose ever grows multiple LLM "modes" (generate vs explain vs reharm).
3. **Text-diff-as-score-diff**: if TLR-like text is adopted anywhere, a
   plain line diff becomes a musically meaningful diff for free — cheap way
   to show "what did the LLM change" in a UI.

### Medium value

4. Explicit key-context field on harmony events (`HARMONY t=0 symbol=V7
   key=C major`) — small idea, ensures reharm prompts always carry tonal
   context per event rather than only score-level key.

### Low value / do not steal

5. Running Gradio + NestJS + Vue simultaneously "in migration" — pure
   anti-pattern; pick one UI stack per `AGENTS.md` discipline.
6. Chord harmonization depth (root+quality only) — Harmonyx's realizer is
   already ahead; nothing to backport.
7. Their thin validator rule bodies (`pass`-only branches) — the pattern is
   good, the content is not; do not copy rule implementations verbatim.
8. Trusting their CHANGELOG/marketing language as a maturity signal — verify
   by running tests, as done here.

### Do not

- Vendor any code from this repo (unclear real maintenance state, narrow CI,
  broken full test suite).
- Treat "SATB" in their filenames as evidence of a four-part realizer —
  it isn't one.

---

## 8. Open questions

1. Does Harmonyx ever need a **note-level** LLM interface (vs RN-level)? If
   a "reharmonize this existing chorale" or "explain this passage" feature
   is ever scoped, TLR is the reference pattern to revisit — log this under
   the landscape doc's domain-expansion backlog (§11), not as a near-term
   task.
2. Is a flag-gated multi-mode prompt builder worth adopting once L4 grows
   beyond single-mode "propose a progression"?
3. Confirm before any future reference: this repo's actual maintenance
   status (0★, single push date, self-documented mid-migration) — re-check
   liveliness if ever revisited.

---

## 9. One-screen summary

**choral-llm-workbench** = MusicXML ↔ IKR-light ↔ TLR (line-per-event text)
↔ local LLM (Ollama), flag-gated transformation validator, thin one-chord-
per-measure harmonization, Gradio+Vue+NestJS all present at once, CI covers
a narrow slice, full test suite doesn't collect.

**Harmonyx** = RN-list → full SATB hard-DP realizer with locked fixtures;
RN-level (not note-level) LLM interface planned for L4.

**Steal:** TLR-style explicit text serialization and text-diff-as-score-diff
*as a pattern* for a future note-level LLM feature; flag-scoped prompt
construction. **Don't steal:** any actual code, their harmonization depth,
or running multiple UI stacks concurrently.

---

*End of deep-dive #05. Per `docs/NEXT-RESEARCH-PASTE.txt`, stop here for
check-in before #06 (When-in-Rome).*
