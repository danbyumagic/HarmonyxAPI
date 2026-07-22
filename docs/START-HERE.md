# Start here (read this first)

Plain-language status for humans and agents. Keep it short. For agent rules,
see `AGENTS.md` at the repo root.

## What is this project?

**Harmonyx API** — a two-way harmony tool:

1. **Analyze** — score (MusicXML/MIDI) → Roman numerals, key, cadences.
2. **Generate** — Roman-numeral progression → four-part SATB hymn (MusicXML),
   with optional propose / edit / lock / play in the browser.

## Where things stand (2026-07-21)

### Done on branch `claude/harmonic-analysis-api-loc82f`

**Core product (earlier)**

- **Analyze** API + frontend drop-zone.
- **Part-writing realizer** (`app/generation/`) + locked fixtures in
  `tests/test_partwriting.py` (**do not edit** those tests).
- Soprano chord-tone check bug fixed.
- **`POST /generate`** — RN list → MusicXML JSON (+ playback note list).
- **`POST /progression`** — rule-based functional-harmony grammar.
- **M2 generation eval** — round-trip + zero hard violations on fixtures; CI wired.
- **Frontend Generate tab** — propose, edit/lock RNs, realize, download.
- **OSMD** score preview; **grand staff** export; **Play / Stop** @ 75 BPM.
- **Soprano-line alternatives** — `soprano_alternatives()` (`app/generation/realize.py`),
  `POST /generate/soprano-options` (up to 3 melodic options per progression), and
  a Generate-tab "Soprano options" row of preview cards (▶ to hear the line
  alone, click to re-finalize the score with that soprano) — `app/static/index.html`.
  This was the last task of its 4-task plan; **good point to suggest a chat reset.**

**Richer rule grammar (Q3 — done)**

| Chunk | Status | What |
|-------|--------|------|
| **Q3a** | Done | More inversions + Cad64 approaches (default path). |
| **Q3b** | Done | Secondary dominants behind `spice` 0–3. |
| **Q3c** | Done | `style` presets (`student` / `hymnal` / `spicy`); docs §9b. |

Default propose stays student-safe (`spice=0`). Opt in with `spice` or `style`
(API and Generate-tab **spice slider / style pills**). Spec:
`docs/RICH-GRAMMAR-SPEC.md`.

**LLM progression foundation (L1–L3)**

| Phase | Status | Where |
|-------|--------|--------|
| **L0** design | Done | `docs/LLM-PROGRESSION-SPEC.md` |
| **L1** corpus | Done | `data/progression_corpus.json`, `app/generation/corpus.py` |
| **L2** validator | Done | `app/generation/validate.py` |
| **L3** deterministic fixer | Done | `app/generation/fix.py` |
| **L4–L7** LLM client / API / UI | **Not started** | see LLM spec |

**Analyzer improvements (Q4 — done)**

| Chunk | Status | What |
|-------|--------|------|
| **A1** | Done | NCT filtering — passing/neighbor tones classified by melodic step + weak beat, neutralized before chordify. |
| **A2** | Done | Fermata-based phrase segmentation (cadences checked only at phrase ends) + PAC/IAC refinement of authentic cadences. |
| **A7** | Done | `eval/run_rn_eval.py` — chord-by-chord RN-agreement vs. music21's bundled Riemenschneider chorale analyses. 42% primary / 38% strict baseline (949 events, 17 chorales); wired into CI as visibility-only, not yet a gate. |

Confirm `git log` / `git status` before assuming push state.

### Not broken — but known limits

- Grammar is richer when opted in; **default** is still homework-safe.
- L1–L3 validate/fix spicy RNs; Propose uses the rule grammar (not LLM yet).
- Analyzer: NCT filtering + fermata-gated cadences landed (A1/A2); ~65% key
  eval unchanged (A1/A2 don't touch key detection); RN-agreement now
  measured at 42%/38% (A7) — was previously unmeasured, not a regression.
  A MIDI source has no fermata data, so it still falls back to checking
  every adjacent chord pair for cadences (the pre-A2 behavior).
- Playback is intentionally low-fi (not SoundFont / no score cursor).

## Open queue (do not forget)

Priority is a **human choice** each session. Candidates:

| ID | Item | Notes |
|----|------|--------|
| Q1 | LLM progression L4+ | L1–L3 done; next is L4 client — `docs/LLM-PROGRESSION-SPEC.md` (+ research #01). |
| Q2 | **M4 `POST /check`** | Upload score → part-writing violations. Blueprint: research #03 PartWise. |
| Q5 | Docs / PR polish | PR #1 may need refresh. |
| Q6 | Raise A7's RN-agreement above baseline | 42%/38% is a first measurement, not a target; no work scoped yet. |

**Research peers (01–15 done):** notes under `docs/research/`. Tier 1, Tier 2,
and Tier 3 of `docs/RESEARCH-QUEUE.md` are all now closed in full. Only
Tier 4 (OMR: Audiveris, homr) remains logged, and it stays parked per
`docs/AI-DIARY.md` Entry 4 — no default research chunk is queued; human
must name a new candidate or explicitly revisit Tier 4. Research is **not**
a build license.

**Do not** re-implement M1–M3, grand staff, OSMD, playback, L1–L3, or Q3
unless fixing a regression.

## If you're starting a new chat, paste this in

Short version (also in `docs/NEXT-AGENT-PASTE.txt`):

> Read `docs/START-HERE.md`, `AGENTS.md`, and `docs/AGENT-START-HERE.md`.
> Then **stop and wait** for my instructions — do not start implementing
> anything yet.

If the task is named (e.g. L4), also read that task’s spec before waiting.
For classical×AI **research** sessions, paste `docs/NEXT-RESEARCH-PASTE.txt`.

## Optional deeper reading

- `docs/STATUS.md` — technical snapshot
- `docs/RICH-GRAMMAR-SPEC.md` — **Q3** richer rule grammar (implemented Q3a–c)
- `docs/LLM-PROGRESSION-SPEC.md` — LLM path (L1–L3 implemented; L4+ not)
- `docs/IMPLEMENTATION-PLAN.md` — older milestone plan (M0–M5 largely done
  except M4)
- `docs/PARTWRITING-RULES.md` — locked theory for the realizer (§9 / §9b)
- `docs/CLASSICAL-AI-LANDSCAPE.md` — external classical×AI / arrange landscape
  (GitHub peers, Tier S–D map; research only, not a build queue)
- `docs/research/01`–`15-*.md` — peer deep-dives (Resonance, choral-counterpoint,
  PartWise, chorale-optimizer, choral-llm-workbench, When-in-Rome,
  AccoMontage2+POP909, Shimaoka-SATB-SkillSet, music-arranger, thiri-mcp+music21-mcp,
  AugmentedNet, JJazzLab, rnbert+muMoE-RNBERT, ai-music-theory+MuTheoryEval,
  diatone+mcp-score+Humdrum tooling)
- `docs/NEXT-RESEARCH-PASTE.txt` — paste for next **research** session
- `docs/AI-DIARY.md` — chronological agent log (newest at bottom)
