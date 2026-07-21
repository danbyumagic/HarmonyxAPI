# Start here (for the next AI agent)

Read this file, then `AGENTS.md` at the repo root, then `docs/START-HERE.md`.
**Then stop and wait for the user's explicit task.** Do not invent work.

This file is **not** a license to implement the next milestone unprompted.

## Project snapshot (do not re-build)

Already on branch `claude/harmonic-analysis-api-loc82f` (pushed):

- Realizer + rules + voicing (soprano chord-tone check fixed)
- `POST /generate` (MusicXML + `playback` @ 75 BPM block chords)
- `POST /progression` (rule grammar)
- M2 `eval/run_generation_eval.py` + CI gate
- Frontend Generate tab: propose / lock / realize / OSMD / Play / download
- Grand staff SATB layout (SA treble, TB bass, correct stems)

Verify if needed:

```bash
python -m pytest tests/ -q
python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0
```

## Hard rules

- Never edit `tests/test_partwriting.py` (locked spec).
- Small chunks only; ask before large multi-file odysseys (`AGENTS.md` Rule 1–2).
- Commit/push at natural stops (ephemeral environments).

## If the user asks you to implement something

They will name **one** chunk. Examples of open work (human picks):

1. LLM progression — **only** as phased in `docs/LLM-PROGRESSION-SPEC.md`
   (default: do not train; API key + corpus + validator).
2. M4 `POST /check` (part-writing on upload).
3. Richer rule grammar (no LLM).
4. Analyzer improvements (NCT / cadences / RN eval).

Until they name a chunk: **report that you read the handoff and wait.**

## Optional reading (only if the named task needs it)

- `docs/LLM-PROGRESSION-SPEC.md` — AI progression design
- `docs/STATUS.md` — technical map
- `docs/PARTWRITING-RULES.md` — realizer theory
- `docs/AI-DIARY.md` — history (newest at bottom); do not re-read all unless needed
