# Start here (read this first)

Plain-language status for humans and agents. Keep it short. For agent rules,
see `AGENTS.md` at the repo root.

## What is this project?

**Harmonyx API** — a two-way harmony tool:

1. **Analyze** — score (MusicXML/MIDI) → Roman numerals, key, cadences.
2. **Generate** — Roman-numeral progression → four-part SATB hymn (MusicXML),
   with optional propose / edit / lock / play in the browser.

## Where things stand (2026-07-21, end of handoff session)

### Done and pushed (`claude/harmonic-analysis-api-loc82f`)

- **Analyze** API + frontend drop-zone (as before).
- **Part-writing realizer** (`app/generation/`) + locked fixtures in
  `tests/test_partwriting.py` (do not edit those tests).
- Soprano chord-tone check bug **fixed**.
- **`POST /generate`** — RN list → MusicXML JSON (+ playback note list).
- **`POST /progression`** — rule-based functional-harmony grammar.
- **M2 generation eval** — round-trip + zero hard violations on fixtures; CI wired.
- **Frontend Generate tab** — propose, edit/lock RNs, realize, download.
- **OSMD** score preview (view).
- **Grand staff** export: SA on treble (stems up/down), TB on bass (stems up/down).
- **Play / Stop** — block chords @ **75 BPM**, rough Web Audio triangle synth.

Latest feature commit family includes through:
`c1cc643` (playback), `4f864dd` (grand staff), `cd8d305` (OSMD), etc.

### Not broken — but known limits

- Rule grammar progressions feel **Theory I vanilla** (few inversions, no
  modulation). Expected; design for a richer / LLM path is written, not built.
- Analyzer still has NCT noise, eager cadences, ~65% key eval (unchanged).
- Playback is intentionally low-fi (not SoundFont / no score cursor).

## Open queue (do not forget)

Priority is a **human choice** each session. Candidates:

| ID | Item | Notes |
|----|------|--------|
| Q1 | **LLM progression proposer** | Spec only — see `docs/LLM-PROGRESSION-SPEC.md`. No training from scratch; API key + corpus few-shot + validator. |
| Q2 | **M4 `POST /check`** | Upload score → part-writing violations. Reuses `rules.py`. |
| Q3 | **Richer rule grammar** | More inversions, secondary dominants, style presets (no LLM). |
| Q4 | **Analyzer A1/A2/A7** | NCT filter, fermata cadences, RN-agreement eval. |
| Q5 | Docs / PR polish | Keep STATUS in sync; PR #1 may need refresh. |

**Do not** re-implement M1–M3, grand staff, OSMD, or playback unless fixing a regression.

## If you're starting a new chat, paste this in

> Read `docs/START-HERE.md`, `AGENTS.md`, and (if working on AI progressions)
> `docs/LLM-PROGRESSION-SPEC.md`. Then **stop and wait** for my instructions —
> do not start implementing anything yet.

## Optional deeper reading

- `docs/STATUS.md` — technical snapshot
- `docs/LLM-PROGRESSION-SPEC.md` — LLM + corpus + validator design
- `docs/IMPLEMENTATION-PLAN.md` — older milestone plan (M0–M5 largely done
  except M4; LLM is new relative to that file)
- `docs/PARTWRITING-RULES.md` — locked theory for the realizer
- `docs/AI-DIARY.md` — chronological agent log (newest at bottom)
