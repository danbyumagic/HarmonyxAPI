# Start here (for the next AI agent)

Read this file, then `AGENTS.md` at the repo root, then `docs/START-HERE.md`.
**Then stop and wait for the user's explicit task.** Do not invent work.

This file is **not** a license to implement the next milestone unprompted.

## Project snapshot (do not re-build)

Already on branch `claude/harmonic-analysis-api-loc82f`:

- Realizer + rules + voicing (soprano chord-tone check fixed)
- `POST /generate` (MusicXML + `playback` @ 75 BPM block chords)
- `POST /progression` (rule grammar — still vanilla)
- M2 `eval/run_generation_eval.py` + CI gate
- Frontend Generate tab: propose / lock / realize / OSMD / Play / download
- Grand staff SATB layout (SA treble, TB bass, correct stems)

**Also implemented (L1–L3 — do not re-do):**

- `data/progression_corpus.json` + `app/generation/corpus.py`
- `app/generation/validate.py` (`validate_progression`)
- `app/generation/fix.py` (`suggest_fixes`; `suggest=True` on validator)

**Designed only:**

- Q3 richer grammar → `docs/RICH-GRAMMAR-SPEC.md` (Q3a / Q3b / Q3c)
- LLM L4+ → `docs/LLM-PROGRESSION-SPEC.md`

Verify if needed:

```bash
python -m pytest tests/ -q
python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0
```

Expect on the order of **~133** tests after L1–L3 (count may drift).

## Hard rules

- Never edit `tests/test_partwriting.py` (locked spec).
- Small chunks only; ask before large multi-file odysseys (`AGENTS.md` Rule 1–2).
- Commit/push at natural stops (ephemeral environments).
- One named chunk per session unless the user expands scope.

## If the user asks you to implement something

They will name **one** chunk. Examples of open work (human picks):

1. **Q3 richer rule grammar** — only as phased in `docs/RICH-GRAMMAR-SPEC.md`
   (default start: **Q3a** inversions + Cad64; then Q3b spice API; then Q3c).
2. LLM progression **L4+** — only as phased in `docs/LLM-PROGRESSION-SPEC.md`
   (L1–L3 already done; do not re-implement corpus/validator/fixer).
3. M4 `POST /check` (part-writing on upload).
4. Analyzer improvements (NCT / cadences / RN eval).

Until they name a chunk: **report that you read the handoff and wait.**

## Optional reading (only if the named task needs it)

- `docs/RICH-GRAMMAR-SPEC.md` — Q3 design (next offline win)
- `docs/LLM-PROGRESSION-SPEC.md` — AI progression design (L4+ remaining)
- `docs/STATUS.md` — technical map
- `docs/PARTWRITING-RULES.md` — realizer theory
- `docs/AI-DIARY.md` — history (newest at bottom); do not re-read all unless needed
