# Start here (for the next AI agent)

Read this file, then `AGENTS.md` at the repo root, then `docs/START-HERE.md`.
**Then stop and wait for the user's explicit task.** Do not invent work.

This file is **not** a license to implement the next milestone unprompted.

Paste-ready prompts:
- **Build / general:** `docs/NEXT-AGENT-PASTE.txt`
- **Research peers only:** `docs/NEXT-RESEARCH-PASTE.txt` (default #05)

---

## Project snapshot (do not re-build)

Branch: `claude/harmonic-analysis-api-loc82f` (confirm `git status` / `git log`).

### Product (implemented)

- Realizer + rules + voicing (soprano chord-tone check fixed)
- `POST /generate` (MusicXML + `playback` @ 75 BPM block chords)
- `POST /progression` (rule grammar + `spice` 0–3 + optional `style`)
- M2 `eval/run_generation_eval.py` + CI gate
- Frontend Generate tab: propose / lock / realize / OSMD / Play / download
- Generate tab **spice slider + style pills** (Student / Hymnal / Spicy / Max)
- Grand staff SATB layout (SA treble, TB bass, correct stems)

### L1–L3 (do not re-do)

- `data/progression_corpus.json` + `app/generation/corpus.py`
- `app/generation/validate.py` (`validate_progression`)
- `app/generation/fix.py` (`suggest_fixes`; `suggest=True` on validator)

### Q3 (do not re-do)

- Q3a inversions + Cad64 — `app/generation/grammar.py`
- Q3b secondary dominants + `spice`
- Q3c `style` presets + PARTWRITING-RULES §9b
- Frontend spice/style controls — `app/static/index.html`

### Research (done — notes only; not a build queue)

| # | Notes | Use when building |
|---|--------|-------------------|
| 01 | `docs/research/01-resonance.md` | **L4** LLM contract / fallback |
| 02 | `docs/research/02-choral-counterpoint.md` | **M4** hard/soft tiers, Bach culture |
| 03 | `docs/research/03-partwise.md` | **M4** evaluate UX + API projection |
| 04 | `docs/research/04-chorale-optimizer.md` | Realizer alternatives; keep DP default |

Landscape map: `docs/CLASSICAL-AI-LANDSCAPE.md`. Next research default: **#05
choral-llm-workbench**.

### Designed / not started (build)

- LLM L4+ → `docs/LLM-PROGRESSION-SPEC.md`
- M4 `POST /check`
- Analyzer A1/A2/A7

Verify if needed:

```bash
python -m pytest tests/ -q
python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0
```

Expect on the order of **~155** tests after Q3 (count may drift).

---

## Hard rules

- Never edit `tests/test_partwriting.py` (locked spec).
- Small chunks only; ask before large multi-file odysseys (`AGENTS.md` Rule 1–2).
- Commit/push at natural stops (ephemeral environments).
- One named chunk per session unless the user expands scope.
- Research notes do **not** authorize porting peer code into the product.

## If the user asks you to implement something

They will name **one** chunk. Examples of open work (human picks):

1. LLM progression **L4+** — phased in `docs/LLM-PROGRESSION-SPEC.md`; steal
   patterns from research #01 (not Resonance product copy).
2. M4 `POST /check` — UX/API from research #03; rule depth from our `rules.py`;
   V/W thinking from #02.
3. Analyzer improvements (NCT / cadences / RN eval).
4. Docs / PR polish.
5. Research #05+ only if they paste research mode or say “continue research.”

Until they name a chunk: **report that you read the handoff and wait.**

## Optional reading (only if the named task needs it)

- `docs/LLM-PROGRESSION-SPEC.md` — AI progression design (L4+ remaining)
- `docs/RICH-GRAMMAR-SPEC.md` — Q3 (implemented; reference only)
- `docs/STATUS.md` — technical map
- `docs/PARTWRITING-RULES.md` — realizer theory (§9 / §9b)
- `docs/CLASSICAL-AI-LANDSCAPE.md` — external peers (study map)
- `docs/AI-DIARY.md` — history (newest at bottom); skim recent entries only
