# Start here (for the next AI agent)

Read this file, then `AGENTS.md` at the repo root, then `docs/START-HERE.md`.
**Then stop and wait for the user's explicit task.** Do not invent work.

This file is **not** a license to implement the next milestone unprompted.

Paste-ready prompts:
- **Build / general:** `docs/NEXT-AGENT-PASTE.txt`
- **Research peers only:** `docs/NEXT-RESEARCH-PASTE.txt` (default: next item
  in `docs/RESEARCH-QUEUE.md`)

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
| 05 | `docs/research/05-choral-llm-workbench.md` | Note-level LLM interface pattern (IKR-light/TLR); not needed for RN-based L4 |
| 06 | `docs/research/06-when-in-rome.md` | RN meta-corpus; L1 few-shot expansion + analyzer A7 eval |
| 07 | `docs/research/07-accomontage2.md` | Pop melody→chords+texture pipeline; Tier B, arrangement-track only |
| 08 | `docs/research/08-shimaoka-satb-skillset.md` | LLM-context-only SATB knowledge base; counter-example to code-enforced validation; 2nd source on augmented-sixth gap |
| 09 | `docs/research/09-music-arranger.md` | Claude tool-call NL→params + CP-SAT SATB solver twin |
| 10 | `docs/research/10-thiri-mcp-and-music21-mcp.md` | Two MCP theory-server architectures |
| 11 | `docs/research/11-augmentednet.md` | CRNN multi-task neural RNA; produced When-in-Rome's automatic analyses; ~45-52% full-RN accuracy ceiling reference |
| 12 | `docs/research/12-jjazzlab.md` | Jazz backing-track app; product-completeness study — SPI-separated model/engine/UI, concatenative pattern-retrieval as a 3rd realization-strategy alternative |
| 13 | `docs/research/13-rnbert-and-mumoe-rnbert.md` | MusicBERT fine-tuned for RNA (~57-62% full-RN composite, beats AugmentedNet/ChordGNN); muMoE extension adds expert-activation interpretability, not accuracy — no neural path scoped for Harmonyx's analyzer |

Landscape map: `docs/CLASSICAL-AI-LANDSCAPE.md`. Research #01–#13 is
complete; Tier 1, Tier 3 #11, Tier 2 #5, and Tier 2 #6 of
`docs/RESEARCH-QUEUE.md` are closed. Next default: **ai-music-theory +
MuTheoryEval** (theory-knowledge KB / LLM eval hub) or Tier 3 remainder
(diatone, mcp-score, Humdrum tooling) — human picks.

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
5. Research (next item in `docs/RESEARCH-QUEUE.md`) only if they paste
   research mode or say "continue research."

Until they name a chunk: **report that you read the handoff and wait.**

## Optional reading (only if the named task needs it)

- `docs/LLM-PROGRESSION-SPEC.md` — AI progression design (L4+ remaining)
- `docs/RICH-GRAMMAR-SPEC.md` — Q3 (implemented; reference only)
- `docs/STATUS.md` — technical map
- `docs/PARTWRITING-RULES.md` — realizer theory (§9 / §9b)
- `docs/CLASSICAL-AI-LANDSCAPE.md` — external peers (study map)
- `docs/AI-DIARY.md` — history (newest at bottom); skim recent entries only
