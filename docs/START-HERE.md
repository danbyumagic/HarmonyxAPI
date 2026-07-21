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
- **`POST /progression`** — rule-based functional-harmony grammar (vanilla).
- **M2 generation eval** — round-trip + zero hard violations on fixtures; CI wired.
- **Frontend Generate tab** — propose, edit/lock RNs, realize, download.
- **OSMD** score preview; **grand staff** export; **Play / Stop** @ 75 BPM.

**LLM progression foundation (L1–L3, code on branch — push if not yet remote)**

| Phase | Status | Where |
|-------|--------|--------|
| **L0** design | Done | `docs/LLM-PROGRESSION-SPEC.md` |
| **L1** corpus | Done | `data/progression_corpus.json`, `app/generation/corpus.py` |
| **L2** validator | Done | `app/generation/validate.py` |
| **L3** deterministic fixer | Done | `app/generation/fix.py` |
| **L4–L7** LLM client / API / UI | **Not started** | see LLM spec |

Commits (local feature branch family includes): `f0ae8ab` (L1), `154155f` (L2),
`78eb0d7` (L3), plus earlier playback/grand-staff/OSMD work. Confirm
`git log` / `git status` before assuming push state.

### Not broken — but known limits

- Rule grammar progressions still feel **Theory I vanilla** (few inversions,
  no secondary dominants in the *generator*). **Q3 is designed, not built** —
  see `docs/RICH-GRAMMAR-SPEC.md`.
- L1–L3 enable validating/fixing spicy RNs but do **not** change Propose yet.
- Analyzer still has NCT noise, eager cadences, ~65% key eval (unchanged).
- Playback is intentionally low-fi (not SoundFont / no score cursor).

## Open queue (do not forget)

Priority is a **human choice** each session. Candidates:

| ID | Item | Notes |
|----|------|--------|
| **Q3** | **Richer rule grammar** | **Next recommended offline win.** Spec: `docs/RICH-GRAMMAR-SPEC.md`. Chunks Q3a → Q3b → Q3c. |
| Q1 | LLM progression L4+ | L1–L3 done; next is L4 client — `docs/LLM-PROGRESSION-SPEC.md`. |
| Q2 | **M4 `POST /check`** | Upload score → part-writing violations. Reuses `rules.py`. |
| Q4 | Analyzer A1/A2/A7 | NCT filter, fermata cadences, RN-agreement eval. |
| Q5 | Docs / PR polish | PR #1 may need refresh; push L1–L3 if still local-only. |

**Do not** re-implement M1–M3, grand staff, OSMD, playback, or L1–L3 unless
fixing a regression.

## If you're starting a new chat, paste this in

**General / wait for task:**

> Read `docs/START-HERE.md`, `AGENTS.md`, and (if the task names them)
> `docs/RICH-GRAMMAR-SPEC.md` or `docs/LLM-PROGRESSION-SPEC.md`. Then **stop
> and wait** for my instructions — do not start implementing anything yet.

**Q3 work specifically:**

> Read `docs/START-HERE.md`, `AGENTS.md`, and `docs/RICH-GRAMMAR-SPEC.md`.
> Then **stop and wait**. When I say go, implement **only** the named chunk
> (Q3a, Q3b, or Q3c).

## Optional deeper reading

- `docs/STATUS.md` — technical snapshot
- `docs/RICH-GRAMMAR-SPEC.md` — **Q3** richer rule grammar (design)
- `docs/LLM-PROGRESSION-SPEC.md` — LLM path (L1–L3 implemented; L4+ not)
- `docs/IMPLEMENTATION-PLAN.md` — older milestone plan (M0–M5 largely done
  except M4)
- `docs/PARTWRITING-RULES.md` — locked theory for the realizer
- `docs/AI-DIARY.md` — chronological agent log (newest at bottom)
