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

Confirm `git log` / `git status` before assuming push state.

### Not broken — but known limits

- Grammar is richer when opted in; **default** is still homework-safe.
- L1–L3 validate/fix spicy RNs; Propose uses the rule grammar (not LLM yet).
- Analyzer still has NCT noise, eager cadences, ~65% key eval (unchanged).
- Playback is intentionally low-fi (not SoundFont / no score cursor).

## Open queue (do not forget)

Priority is a **human choice** each session. Candidates:

| ID | Item | Notes |
|----|------|--------|
| Q1 | LLM progression L4+ | L1–L3 done; next is L4 client — `docs/LLM-PROGRESSION-SPEC.md` (+ research #01). |
| Q2 | **M4 `POST /check`** | Upload score → part-writing violations. Blueprint: research #03 PartWise. |
| Q4 | Analyzer A1/A2/A7 | NCT filter, fermata cadences, RN-agreement eval. |
| Q5 | Docs / PR polish | PR #1 may need refresh. |

**Research peers (01–13 done):** notes under `docs/research/`. Tier 1, Tier 3
#11 (`napulen/AugmentedNet`), Tier 2 #5 (`JJazzLab`), and Tier 2 #6
(`rnbert`/`muMoE-RNBERT`) of `docs/RESEARCH-QUEUE.md` are now closed; default
next is Tier 2 #7 **ai-music-theory + MuTheoryEval** or Tier 3 remainder — see
that file for the live queue. Research is **not** a build license.

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
- `docs/research/01`–`13-*.md` — peer deep-dives (Resonance, choral-counterpoint,
  PartWise, chorale-optimizer, choral-llm-workbench, When-in-Rome,
  AccoMontage2+POP909, Shimaoka-SATB-SkillSet, music-arranger, thiri-mcp+music21-mcp,
  AugmentedNet, JJazzLab, rnbert+muMoE-RNBERT)
- `docs/NEXT-RESEARCH-PASTE.txt` — paste for next **research** session
- `docs/AI-DIARY.md` — chronological agent log (newest at bottom)
