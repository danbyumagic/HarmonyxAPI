# Spec: LLM progression proposer (design only)

**Status:** design / not implemented.  
**Date:** 2026-07-21.  
**Do not implement this entire doc in one session.** Work in named phases only,
after the user approves a chunk.

Related: existing optional LLM **explainer** on `/analyze` (`app/explainer.py`,
`ANTHROPIC_API_KEY`). Same product pattern: deterministic core always works;
LLM is optional spice.

---

## 1. Goals

- Make generated Roman-numeral progressions **more interesting** than the
  current Theory-I weighted grammar (more inversions, secondary dominants,
  repertoire-like shapes) **when the user opts in**.
- Keep **rule grammar** as the default offline path (`POST /progression` today).
- Never require training a model from scratch.

## 2. Non-goals (v1)

- Training or fine-tuning a foundation model.
- Scraping “the whole internet” for progressions.
- Letting the LLM write SATB notes or bypass part-writing rules.
- Silent auto-rewrite of user intent without showing a diff (prefer visible fixes).
- Full modulation engine in the first LLM slice (schema may allow `region` later).

---

## 3. Architecture (closed product loop)

```
User request (key, length, cadence, style/spice)
        │
        ▼
Retrieve 2–5 corpus examples (tags / spice)
        │
        ▼
LLM API (API key)  ──►  JSON { "progression": ["I", ...] }
        │
        ▼
Validator (theory house rules + engine realizability)
        │
   ┌────┴────┐
   OK        FAIL → suggestions (minimal edits) → user pick / edit
   │
   ▼
Existing realize /generate → grand staff + playback
```

| Component | Role | LLM? |
|-----------|------|------|
| Corpus | Grounding examples | No |
| Proposer | Invent RN list | **Yes (API)** |
| Validator | Legal + realizable | No |
| Fixer (deterministic first) | Closest legal neighbors | No |
| LLM repair (optional later) | Minimal rewrite given errors | Optional |
| Realizer | SATB notes | No |

**Fallback:** if no API key or LLM fails → current `generate_progression` grammar.

---

## 4. API key utilization

- **Preferred:** server-side env key (e.g. `ANTHROPIC_API_KEY`), same as explainer.
- Feature flag / UI: “Propose with AI” disabled when key absent.
- **Not** train local weights for v1.
- Optional later: user-supplied key; or local model (Ollama) for network-closed use.

Prompt each request with:

1. Short house rules (forbidden transitions, cadence contract, output schema).
2. Few-shot **corpus** examples (not web search at runtime).
3. User constraints (key, length, cadence, spice, locks).

Force structured output: JSON object with `progression: string[]` only (v1).

---

## 5. Corpus

### 5.1 Purpose

High-quality, curated RN phrases for few-shot / retrieval — **not** a web dump.

Sources (v0 mix):

- Hand-written phrase templates (~20–40)
- Analyzer-derived phrases from a few public-domain chorales (~20–40)
- Human-approved grammar outputs (~10–20)

Target before wiring LLM: **~50–100** entries.

### 5.2 Entry shape (v1 recommended)

```json
{
  "id": "template-pac-applied-01",
  "source": {
    "type": "hand_template",
    "ref": "applied dominant into V",
    "license": "original"
  },
  "key": "C major",
  "mode": "major",
  "progression": ["I", "vi", "ii6", "V/V", "V", "I"],
  "cadence": "PAC",
  "length": 6,
  "tags": [
    "hymnal",
    "common_practice",
    "has_inversion",
    "has_secondary_dominant",
    "no_modulation"
  ],
  "region": [
    { "from": 0, "to": 5, "key": "C major" }
  ],
  "quality": {
    "spice": 2,
    "student_safe": true,
    "realizer_ok": true
  },
  "notes": "ii6 prep, V/V, PAC. Good few-shot for mildly spicy."
}
```

**Minimal viable entry:** `id`, `key`, `progression`, `cadence`, `tags`.

Suggested on-disk location (when implemented):
`eval/expected/progression_corpus.json` or `data/progression_corpus.json`.

---

## 6. Validator

### 6.1 Two gates

| Gate | Question |
|------|----------|
| **A. Theory / house style** | Forbidden edges, parseable figures, cadence contract, locks |
| **B. Engine** | `candidate_voicings` / `realize` succeed for this stack |

Report which gate failed.

### 6.2 Issue object

```json
{
  "ok": false,
  "progression": ["I", "V", "IV", "I"],
  "issues": [
    {
      "code": "forbidden_transition",
      "severity": "theory",
      "index": 1,
      "span": [1, 2],
      "found": { "from": "V", "to": "IV" },
      "message": "Beat 3: V → IV is a retrogression we don't allow in house style.",
      "suggestions": [
        {
          "label": "Resolve to tonic",
          "progression": ["I", "V", "I", "I"],
          "edits": [{ "index": 2, "from": "IV", "to": "I" }]
        },
        {
          "label": "Deceptive",
          "progression": ["I", "V", "vi", "I"],
          "edits": [{ "index": 2, "from": "IV", "to": "vi" }]
        }
      ]
    }
  ]
}
```

### 6.3 Starter issue codes

| code | severity |
|------|----------|
| `empty_progression` | block |
| `unknown_figure` | block |
| `forbidden_transition` | block |
| `cadence_mismatch` | block |
| `lock_conflict` | block |
| `unrealizable_chord` | block |
| `unrealizable_path` | block |
| `spice_stripped` | info |
| `normalized_figure` | info |

### 6.4 Message style

Always: **where** (beat/index), **what** (figures), **why** (one line),
**what to do** (≤3 suggestions or edit manually).

### 6.5 “Closest fix” policy

Prefer, in order:

1. Minimal number of chord edits  
2. Honor locked slots  
3. Preserve requested cadence  
4. Preserve spice when a legal spicy alternative exists  
5. Fall back to bland textbook fix only if needed — and label it  

Deterministic fixer **first**; optional LLM repair pass later.

---

## 7. UX (when UI is wired)

- Grammar propose remains default.
- “Propose with AI” only if key configured.
- On validation failure, highlight beat and offer suggestion chips
  (do not silently replace).
- Then existing Realize → OSMD → Play @ 75 BPM.

---

## 8. Implementation phases (chunk boundaries)

Execute **one phase per session** unless the user expands scope.

| Phase | Deliverable | Done when |
|-------|-------------|-----------|
| **L0** | This spec (done as design) | Merged in docs |
| **L1** | Corpus file + 20–50 hand/analyzer entries + loader tests | JSON validates; loadable |
| **L2** | `validate_progression(...)` + issue/suggestion types + unit tests | Forbidden + cadence + unknown figure covered |
| **L3** | Deterministic fixer (minimal edit suggestions) | Suggestions pass validator |
| **L4** | LLM client: prompt builder + parse JSON + API key gate | Dry-run with mock; no key → clear error |
| **L5** | `POST /progression` flag e.g. `source: "llm" \| "grammar"` or separate route | Endpoint + tests |
| **L6** | Frontend: AI propose + show validation chips | Manual smoke OK |
| **L7** | Optional LLM repair pass | Only if L2–L3 insufficient |

**Do not start at L4 without L1–L2** unless the user explicitly says so
(unvalidated LLM output is not shippable).

---

## 9. Relationship to current grammar

- Keep `app/generation/grammar.py` as default and fallback.
- Long-term: enrich grammar (inversions, V/x) **in parallel** with LLM path
  (see open queue Q3 in `START-HERE.md`) so offline mode also improves.
- Realizer stays source of truth for playable notes.

---

## 10. Open product decisions (human)

1. Silent fix vs always show diff? **Default in this spec: always show.**  
2. Student mode: strip secondary dominants or only warn?  
3. Corpus in public repo (hand templates OK) vs private mined data?  
4. Modulation: postpone engine; optional `region` field in corpus only?

---

## 11. Success criteria (feature complete at L6)

- With API key: user can request a spicier progression than vanilla grammar
  on average (subjective + tag diversity metrics optional).
- Every LLM proposal is validated before realize.
- Without API key: grammar path unchanged.
- No regression: `pytest`, generation eval, existing endpoints green.
