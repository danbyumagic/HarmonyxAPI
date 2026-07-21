# Research note: Shimaoka-SATB-SkillSet (ShikiSuen)

**Date:** 2026-07-21
**Repo:** https://github.com/ShikiSuen/Shimaoka-SATB-SkillSet
**Author:** Shiki Suen (孫志貴) — packaging Shimaoka Yuzuru's (島岡譲) *総合和声：
実技・分析・原理* (Tokyo University of the Arts four-part-harmony textbook)
**Status:** Tier 1 peer #1 (per `docs/RESEARCH-QUEUE.md`) — pure
knowledge-base-as-LLM-context repo, no code engine
**Source:** `README_EN.md`, `shimaoka-harmony-en/SKILL.md` (full),
`references/voice-leading.md`, `references/d-chords.md`,
`references/notation-syntax.md`, `references/rules.md` (all full), `AGENTS.md`
(repo's own meta-instructions), one `VALUEADD/` review (`[Sonnet5]Review-...md`)
skimmed for outside critique. Not read in full: `chord-system.md`,
`cadence.md`, `d-formation.md`, `modulation.md`, `s-chord.md`,
`ornamentation.md`, `sequence.md`, `nonchord.md`, `examples.md`,
`melody-harmonization.md`, the Chinese-character mirror
(`shimaoka-harmony/`), `ShimaokaChordStructExample.swift`, remaining 8
`VALUEADD/` reviews.
**Meta:** 1★, single author, pushed 2026-07-14 (fresh). MIT for the notation
system/Swift/repo structure; harmonic theory content itself is "academic
public domain" (the Shimaoka textbook's own copyright status is not
independently verified here — treat citations, not verbatim reproduction, as
safe).

---

## 1. What it is

Not a tool, model, or API — a **structured markdown knowledge base** meant to
be handed to an LLM as system-prompt/context material so the LLM itself
performs SATB part-writing directly, following Shimaoka Yuzuru's "Swing
Theory" (揺れ理論/yure): chords oscillate between a stable **rest** position
and a tension-bearing **displacement**, and a full phrase is built from
**cadential units** (K1/K2/K3) chained together. `SKILL.md` is the entry
point (core philosophy, terminology, an 8-step writing procedure, quick-ref
tables); 14 `references/*.md` files hold the topic depth; `_SKILL-
Amalgamated.md` is the full merge for one-shot loading. Both a Chinese-
character-native version (`shimaoka-harmony/`) and an English Roman-numeral
mirror (`shimaoka-harmony-en/`) exist, described as notationally isomorphic.

**Vs Harmonyx:** zero product/architecture overlap — there is no
validator, no realizer, no enforcement code at all here. This is the explicit
philosophical counter-example to Harmonyx's core bet ("LLM proposes, code
enforces" — already independently validated by research #05
choral-llm-workbench). Shimaoka-SATB-SkillSet instead bets everything on
**LLM proposes, LLM enforces via sufficiently detailed prompt context** —
worth citing precisely because it's the road not taken, not because it's
wrong.

---

## 2. Swing Theory vs. Harmonyx's functional-harmony grammar

Shimaoka's functional system (T / D₁–D₆ / S) reframes "how far is this chord
from tonic" as a **distance measured in steps around the circle of fifths**
(`Ⅰ→Ⅴ→Ⅱ→Ⅵ→Ⅲ→Ⅶ→Ⅳ→Ⅰ` = clockwise = D-progression), rather than the
three-way discrete T/S/D label Harmonyx's `grammar.py` and Western textbooks
both use. This is a genuinely different design axis, not just renamed
terminology — but the Sonnet5 review already flagged the internal seam:
`Ⅳ` is simultaneously "S" (1 step counterclockwise) and "D6" (6 steps
clockwise) and the docs don't resolve which wins. Not something to adopt —
Harmonyx's T/S/D + secondary-dominant (`/V` etc.) grammar from Q3b is simpler
and has no such self-contradiction. Filed as a **don't-steal**: the
"distance" framing is intellectually interesting but not more actionable
than what Harmonyx already has.

The **cadential-unit / cadential-chain** framing (K1 `I-V-I`, K2 `I-ii-V-I`,
K3 `I-IV-I`, chained into full phrases) is closer to something Harmonyx
already effectively does implicitly via `grammar.py`'s transition table and
`style` presets (Q3c), but Shimaoka names the unit explicitly and treats
phrase construction as "select unit skeleton → select cadence formula → fill
outward" rather than a Markov-style transition walk. Not an immediate change,
but worth remembering as a structuring idea if Harmonyx's grammar ever grows
a phrase-level (multi-cadence) planning step rather than the current
chord-by-chord walk.

---

## 3. Notation richness — a second confirmation of the augmented-sixth gap

This is the most concrete, actionable finding, and it independently
corroborates something research #06 (When-in-Rome) already flagged:
**Harmonyx's RN grammar has no augmented-sixth chords.** Shimaoka's system
gives full French/Italian/German 6th coverage (`d-chords.md`) with concrete
disposition guidance (⟨2nd⟩ most common; the lowered `rⅤ`-5th + upper T/`Ⅳ`
3rd form the augmented 6th) and usage rules (applicable only at D₂, i.e. on
`Ⅱ`; other scale degrees would imply modulation). Two independent peer
sources now flag the same gap — raises priority if augmented sixths are ever
scoped, per `RESEARCH-QUEUE.md`'s own note. When-in-Rome's `It6`/`Fr43`/
`Ger65` shorthand (already surfaced in research #06) remains the more
directly reusable *notation* precedent since it's RomanText-native and
music21-compatible; Shimaoka's contribution here is stronger on the *theory*
side (when to use which of the three forms) rather than the wire syntax.

The **prefix-degree-suffix notation** (`shimaoka-harmony-en/references/
notation-syntax.md`) is richer than Harmonyx's current RN vocabulary in ways
Harmonyx doesn't need today but that map to named future gaps:

| Shimaoka token | Meaning | Harmonyx today |
|---|---|---|
| `r` (rootless) | `rⅤ7` = rootless dominant 7th | Not modeled; music21 RNs are always root-explicit |
| `m` (quasi/borrowed) | `mⅣ` = borrowed from parallel mode | Not modeled — no modal-mixture chords in `grammar.py` |
| `p` (Neapolitan) | `pⅡ1` = Neapolitan 6th | Not modeled |
| `+`/`-` (forced major/minor) | `+Ⅰ` = Picardy third | Not modeled |
| `@` (tonicizing to) | `Ⅴ@Ⅱ` | Harmonyx already has this via `/V` secondary-dominant syntax (Q3b) — same concept, different token |
| `/` (sustained bass) | `Ⅴ7/Ⅰ` = V7 over pedal I | Not modeled — no pedal-point/sustained-bass notation |

None of these are recommended for immediate adoption — they're each a real
theory feature Harmonyx's grammar doesn't cover (Neapolitan 6ths, borrowed
chords/modal mixture, Picardy thirds, pedal points), consistent with
`docs/START-HERE.md`'s framing that the current grammar is intentionally
homework-safe-by-default and richer features are opt-in via `spice`/`style`.
This table is the useful artifact: a checklist of "named theory features not
yet in `PARTWRITING-RULES.md` §9b" if/when the grammar is extended further
past Q3c.

---

## 4. Rules compilation (A–G) — a structurally similar but independently-derived rule set

`references/rules.md` compiles the same category of rules as
`PARTWRITING-RULES.md` §0–8, organized differently (A disposition / B motion
/ C simultaneous-motion / D bass / E disposition-change / F–G ornamentation)
but covering near-identical ground: 5th-omission-only, no 3rd/root doubling,
leading-tone/chordal-7th obligatory resolution, parallel/hidden/direct
5ths-8ves forbidden with the same standard exceptions (contrary motion OK,
diminished→perfect 5th OK, inner-voice parallel 5ths more relaxed, disposition-
change-caused direct intervals OK between outer voices). This is useful as
**independent confirmation that Harmonyx's hard-rule set (`PARTWRITING-
RULES.md` §0–7) is complete and standard** — nothing here surfaces a rule
Harmonyx is missing for its currently-scoped hard checks. One genuinely new
item: **B2 Appendix**'s `rⅤ7 → Ⅰ2` exception (the chordal 7th may
exceptionally ascend by step, to avoid doubling the 3rd of a Cad64) — a
specific, narrow voice-leading exception Harmonyx's realizer doesn't
currently special-case. Not urgent (Cad64 handling already exists per Q3a),
but worth a note if a future M4 `POST /check` violation report needs to
distinguish "true parallel/resolution error" from "this specific
textbook-sanctioned exception."

---

## 5. `AGENTS.md` — a meta-artifact, not harmony content, but worth flagging

The repo's own `AGENTS.md` (its meta-instructions for AI agents working on
*that* repo, not harmony content) is a strong, opinionated "ship confidently,
don't ask permission for reversible choices" working philosophy (John
Carmack `.plan` style, BurntSushi PR style, "the three things you submit to
are: tests passing > existing style > explicit instructions"). This is
**the opposite instruction set from Harmonyx's own `AGENTS.md`** (small
chunks, ask before big spends, stop-and-wait at chunk boundaries) — not a
contradiction to resolve, just worth naming explicitly since both are
"agent working philosophy" documents encountered in the same research pass
and a future reader might otherwise conflate them. Not something to import;
Harmonyx's current discipline (Rule 1/2/2b) is a deliberate choice per
`docs/AI-DIARY.md`'s "expensive lesson" and stays as-is.

---

## 6. Steal / don't-steal

**Steal (ideas/references, not text):**
- The augmented-sixth usage rules (only valid at D₂, three named forms, ⟨2nd⟩
  disposition default) as theory backing *if* augmented sixths are ever
  scoped — pair with When-in-Rome's `It6`/`Fr43`/`Ger65` notation (research
  #06) for the wire syntax; this repo for the "when/why" (§3).
- The Neapolitan-6th / borrowed-chord / Picardy-third / pedal-point feature
  checklist (§3 table) as a reference list of "named gaps" if the rule
  grammar grows past Q3c.
- The `rⅤ7 → Ⅰ2` chordal-7th ascending exception (§4) as a specific
  voice-leading edge case worth encoding if M4's violation checker needs
  fine-grained textbook-exception awareness.

**Don't steal:**
- The T/D₁–D₆/S "functional distance" reframing (§2) — internally
  inconsistent per independent review (Ⅳ is both S and D6), no clearer than
  Harmonyx's existing T/S/D model.
- The repo's own `AGENTS.md` working philosophy (§5) — directly contradicts
  Harmonyx's deliberate small-chunks/ask-first discipline; not applicable
  here.
- Don't treat "LLM proposes, LLM enforces via prompt context alone" as a
  viable alternative to Harmonyx's validator/fixer (L2/L3) — this repo is
  the explicit counter-example the project already bet against, and nothing
  read here changes that calculus; no validator exists in this repo to even
  compare against.
- Don't vendor the Chinese-character notation, Swift proof-of-concept, or
  `VALUEADD/` review essays — none are architecture, all are either
  illustrative or non-code commentary.

## 7. Open questions

- Is augmented-sixth support (now flagged by two independent peers — #06 and
  this one) worth actually scoping as a grammar addition, or does it stay
  parked indefinitely as "richer than current default warrants"? A human
  call, not a research conclusion.
- Does the Neapolitan-6th / Picardy-third / modal-mixture feature list (§3)
  belong in `docs/RICH-GRAMMAR-SPEC.md` as a "known future extensions,
  unscoped" section, purely so it's not re-discovered from scratch next
  time a peer repo surfaces the same gap a third time?
