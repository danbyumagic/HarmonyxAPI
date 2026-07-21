# Classical music × AI — research landscape

Living map of open-source projects, papers, and product patterns that matter
if the long-term goal is to be **the** serious stack for classical music theory,
analysis, part-writing, and arrangement with AI.

Paired with Harmonyx as the home product:

| Harmonyx track | One-liner |
|----------------|-----------|
| **Analyze** | MusicXML/MIDI → Roman numerals, key, cadences |
| **Generate** | RN progression → SATB MusicXML (deterministic part-writing) |
| **Propose** | Rule grammar + (soon) LLM progression with validate/fix gates |
| **Check** | (planned M4) score → part-writing violations |

This file is **not** an implementation plan. It is a bookmark of what exists
in the wild, how it clusters, and which repos to study when expanding scope.

_First compiled: 2026-07-21 (GitHub + web scan)._  
_Refresh by re-running the searches in §8._

---

## 1. Ambition framing

**Near term (Harmonyx):** best-in-class *classical* harmonic analysis +
SATB realization + theory-gated AI propose/check.

**Long term (“king of classical × AI”):** own the stack where:

1. **Theory is computed, not guessed** — RN, voice-leading, form, counterpoint.
2. **AI is optional creativity** — progressions, explanations, style, repair —
   always under validators / fixers / locked fixtures.
3. **Scores are first-class** — MusicXML in/out, OSMD/preview, corpora, eval.
4. **Pedagogy + professional** — student-safe defaults *and* spicy/richer
   grammar; later arrangement, reharm, multi-voice styles.

Most of GitHub is either (a) audio text-to-song (Suno-class), (b) thin theory
chatbots, or (c) jazz/pop accompaniment. **Classical rule-governed symbolic
work is a thinner, higher-signal niche** — that is the moat.

---

## 2. Tier map (where to invest attention)

```
Tier S  — Architecture peers / product twins (study deeply)
Tier A  — Direct classical: SATB, RNA, part-writing, chorale
Tier B  — Arrangement / reharm / lead-sheet (expand scope later)
Tier C  — LLM agents, DAW tools, theory KBs (patterns & infra)
Tier D  — Audio full-song, generic tutors (aware of, rarely copy)
```

---

## 3. Tier S — Architecture peers (must study)

These encode the same product philosophy as Harmonyx L1–L4:
**LLM (or search) proposes; deterministic theory enforces.**

| Repo | URL | Why it is Tier S | Notes |
|------|-----|------------------|-------|
| **resonance** | https://github.com/will825/resonance | LLM emits **Roman numerals only**; TS theory engine → voice-led MIDI; Zod validate; offline fallback | Closest L4 architecture mirror (2026-06/07). Live demo on Vercel. |
| **choral-counterpoint** | https://github.com/DashWieland/choral-counterpoint | SATB + Fux engine, Bach-calibrated checkers, corpus oracle, **no LLM at runtime**; started as Claude skill | Same “rules as product” story as part-writing realizer. HTTP compose API. Jul 2026. |
| **choral-llm-workbench** | https://github.com/asb-42/choral-llm-workbench | MusicXML roundtrip + LLM-assisted choral reharm/style; music21; ghost chords | Professional choir arranger angle. Jan 2026. |
| **thiri-mcp** | https://github.com/BluesPrince/thiri-mcp | Deterministic theory MCP: RNA, voicing, reharm | “Computed, not hallucinated.” Thin client over a **hosted** proprietary engine, production-hardened (timeout/quota/error patterns). See research #10. |
| **music21-mcp** | https://github.com/SimonsonM/music21-mcp | music21 as MCP tools (key, RNA, counterpoint, harmonize) | Thin wrapper directly over a **local** open engine — closer template for Harmonyx if MCP is ever scoped. See research #10. |
| **music-arranger** | https://codeberg.org/scarrow/music-arranger | NL → Claude tool-call → CP-SAT (OR-Tools) SATB solver | Closest "L4 + realizer, one architecture" twin; see research #09. |

### Resonance architecture (reference diagram)

```
Vibe ──▶ LLM ──▶ JSON (Roman numerals + metadata) ──▶ schema validate
                      │ fail / no key
                      ▼
              deterministic fallback templates
                      │
                      ▼
         theory engine: RN → chords → voice-lead → MIDI / play
```

Harmonyx analogue: `POST /progression` (grammar or LLM) → `validate` / `fix`
→ `POST /generate` (DP realizer + `rules.py`).

---

## 4. Tier A — Classical: analysis, SATB, part-writing

### 4.1 Generation / harmonization / check

| Repo | URL | Overlap | Updated (scan) |
|------|-----|---------|----------------|
| **chorale-optimizer** | https://github.com/604korupt/chorale-optimizer | RN + soprano → SATB via beam search + iterative rule enforcement; VexFlow + play | 2026-06 |
| **ChoraleHarmonizer** | https://github.com/TimoKellerMath/ChoraleHarmonizer | Soprano → ATB; small transformer + **data-calibrated** voice-leading rules; music21 Bach corpus; MIDI/MusicXML | 2026-07 |
| **PartWise** | https://github.com/cjohanson64-netizen/PartWise | Student SATB **evaluator**: OSMD editor, RN under bass, scores + revision tips | 2026-05 — blueprint for **M4 `/check`** |
| **EasyArray/Harmonizer** | https://github.com/EasyArray/Harmonizer | Jupyter chorale harmonization workbench | 2026-05 |
| **EasyArray/chorale-lab** | https://github.com/EasyArray/chorale-lab | Statistical analysis of Bach chorales | 2026-03 |
| Species / Fux generators | e.g. `jakub-hubicka/Counterpoint-Generator-*`, `AyazEarley/Counterpoint-Generator` | Rule-search pedagogy; same shape as part-writing | various 2025–26 |

### 4.2 Roman-numeral analysis (research + corpora)

| Repo | URL | Overlap | Notes |
|------|-----|---------|-------|
| **When-in-Rome** | https://github.com/MarkGotham/When-in-Rome | Meta-corpus ~2k functional analyses + music21 code | ~85★; gold standard for RN data / eval / few-shot |
| **AugmentedNet** | https://github.com/napulen/AugmentedNet | CRNN multi-task neural RNA (ISMIR 2021 / PhD 2022) | **Done**, see research #11; produced When-in-Rome's `analysis_automatic.rntxt`; 50★, MIT |
| **rnbert** | https://github.com/malcolmsailor/rnbert | Fine-tuned MLM for RNA (ISMIR 2024) | Neural RNA baseline |
| **muMoE-RNBERT** | https://github.com/TomusD/muMoE-RNBERT | ICASSP 2026 interpretable MoE RNA on RNBERT | SOTA research direction for analyzer |
| **ChordGNN** | https://github.com/manoskary/ChordGNN | GNN Roman analysis | Archived; still cited |
| **cygnus** | https://github.com/fredericjalbertdesforges/cygnus | Piano: transcription → harmonic analysis → form | arXiv 2026 |
| **PARC** | https://github.com/ThiagoPoppe/parc | Polyphonic audio → Roman corpus dataset | 2026 |
| **opera-seria-harmonic-analysis** | https://github.com/NZumbusch/opera-seria-harmonic-analysis | Historical RNA niche | 2026 |
| Product analogue (not full OSS core) | https://second-ear.app/tools/roman-numeral-analysis/ | MusicXML → RN via music21 | Market proof for `/analyze` |

### 4.3 Harmonyx internal map (Tier A)

| Harmonyx piece | Closest external peers |
|----------------|------------------------|
| `rules.py` / locked `test_partwriting.py` | choral-counterpoint checkers; chorale-optimizer rules; ChoraleHarmonizer rule engine |
| `realize.py` DP | chorale-optimizer beam search; choral-counterpoint engine |
| M4 `POST /check` (not built) | **PartWise** |
| Analyzer + key eval | When-in-Rome; RNBERT / μMoE; music21 baselines |
| L1 corpus / L2 validate / L3 fix | resonance validate+fallback; thiri-mcp; choral-counterpoint gates |
| OSMD + play frontend | PartWise; chorale-optimizer VexFlow |

---

## 5. Tier B — Arrangement, accompaniment, reharmonization

Classical *hymn* generation is not the same as *arrangement research*, but a
king-of-domain roadmap eventually includes: melody-in, texture, reduction,
orchestration, choir reharm.

### 5.1 Accompaniment / arrangement research

| Repo | URL | Focus | Stars (scan) |
|------|-----|--------|--------------|
| **AccoMontage2** | https://github.com/billyblu2000/AccoMontage2 | Melody → chords + accompaniment arrangement (Python package) | ~166 |
| **AccoMontage** | https://github.com/zhaojw1998/AccoMontage | Phrase selection + style transfer (ISMIR) | research parent |
| **POP909-Dataset** | https://github.com/music-x-lab/POP909-Dataset | Pop arrangement generation corpus | ~395 |
| **D3EMO** | https://github.com/OlyMarco/D3EMO | Emotion-driven piano accompaniment from lead sheet (diffusion) | 2026-07 |
| **EMO_Harmonizer** | https://github.com/Yuer867/EMO_Harmonizer | Emotion-conditioned melody harmonization | research |
| **JJazzLab** | https://github.com/jjazzboss/JJazzLab | Mature open **jazz backing track** arranger app | ~574; **Done**, see research #12 — model/engine/UI SPI separation + concatenative pattern-retrieval generation, no ML |
| **oh-sheet** | https://github.com/Oh-Sheet-Team/oh-sheet | Audio/YouTube → two-hand piano arrangement + PDF | ~322 |
| **music_orchestration** | https://github.com/Landmark-Innovation-Labs/music_orchestration | Audio → orchestral arrangement MVP | early |
| **AI-for-Projective-Musical-Orchestration** | https://github.com/andrew-simons/AI-for-Projective-Musical-Orchestration | MIT Media Lab Opera of the Future | research |

### 5.2 Reharmonization / jazz enrichment

| Repo | URL | Notes |
|------|-----|-------|
| **bebop** | https://github.com/peterklingelhofer/bebop | Tiered reharm (7ths → ii–V → tritone → Coltrane) → MIDI |
| **Music-Chords-Enhancer** | https://github.com/HaiHoang-AI/Music-Chords-Enhancer | Rule-based chord enrichment over lyrics |
| **fleet-midi-substitution** | https://github.com/SuperInstance/fleet-midi-substitution | Substitution from agent tension state |
| **changes** | https://github.com/gjcourt/changes | Jazz standards + transpose + RN |

**Bridge to Harmonyx:** `spice` / secondary dominants / style presets are the
*classical* controlled-enrichment analogue of reharm tiers.

---

## 6. Tier C — LLM agents, DAW, theory knowledge, metrics

### 6.1 Multi-agent / symbolic LLM composition

| Repo | URL | Notes |
|------|-----|-------|
| **CoComposer** | https://github.com/PhotonCombiner/CoComposer | Multi-agent symbolic composition (AutoGen; traditional workflow roles) |
| **GenAI_Agents** | https://github.com/NirDiamant/GenAI_Agents | Large tutorial set; includes LangGraph music compositor notebook |
| **MIDI-GPT** | https://github.com/Metacreation-Lab/MIDI-GPT | Controllable multitrack symbolic GPT (~76★) |
| **BeatEdit** | https://github.com/Haoyu-Gu/BeatEdit-code | ACM MM 2026 — symbolic gen as **explicit editing** |
| **microsoft/muzic** | https://github.com/microsoft/muzic | Large MS understanding + generation suite (~4.9k★) |
| MuseCoco / MIREX baselines | e.g. https://github.com/ZZWaang/mirex2025-musecoco | Controllable symbolic baselines |

**Product lesson:** multi-agent papers are interesting; **shipping** classical
tools still win with structured RN/spec + deterministic engines.

### 6.2 DAW / producer AI

| Repo | URL | Notes |
|------|-----|-------|
| **ableton-producer-skills** | https://github.com/Korben00/ableton-producer-skills | Claude skills: compose, arrange, reharm in Ableton |
| **ableton-copilot** | https://github.com/F-Fischer/ableton-copilot | Ableton MCP, theory-aware generators |
| **logic-pro-mcp** | https://github.com/MongLong0214/logic-pro-mcp | Logic control via MCP |
| **tuneflow-py** | https://github.com/tuneflow/tuneflow-py | AI algorithms as DAW plugins (~887★) |

### 6.3 Theory knowledge & LLM evaluation

| Repo | URL | Notes |
|------|-----|-------|
| **ai-music-theory** | https://github.com/music-comp/ai-music-theory | Machine-readable theory KB (MCP) from many textbooks |
| **MuTheoryEval** | https://github.com/thevertexlab/MuTheoryEval | Hub for evaluating LLM music-theory knowledge |
| Thin “AI theory trainer” chatbots | many student repos | Low signal — skip unless packaging ideas |

### 6.4 Metrics & large score corpora

| Repo | URL | Notes |
|------|-----|-------|
| **smg_metric** | https://github.com/OlyMarco/smg_metric | 25 objective metrics for symbolic generation (harmony, rhythm, polyphony, structure) |
| **PDMX** | https://github.com/pnlong/PDMX | Large public-domain MusicXML dataset (~137★) |
| **When-in-Rome** | (above) | Analyses meta-corpus |
| **POP909** | (above) | Arrangement pairs |

### 6.5 Notation infrastructure (always relevant)

| Project | URL | Role |
|---------|-----|------|
| OpenSheetMusicDisplay | https://github.com/opensheetmusicdisplay/opensheetmusicdisplay | Browser MusicXML render (Harmonyx already) |
| Verovio | https://github.com/rism-digital/verovio | MEI/MusicXML engraving |
| alphaTab | https://github.com/CoderLine/alphaTab | Notation + tab |
| MuseScore | https://github.com/musescore/MuseScore | Full notation suite |
| music21 | https://github.com/cuthbertLab/music21 | Analysis / conversion backbone |
| MusicXML spec | https://github.com/w3c-cg/musicxml | Interchange format |

---

## 7. Tier D — Adjacent noise (know of; rarely prioritize)

- **Full-song audio models:** YuE, DiffRhythm, MusicGen, MusicGPT wrappers,
  Suno/Udio prompt packs — huge mindshare, wrong representation for classical
  theory correctness.
- **Generic “AI music theory chatbot”** apps — explain scales/chords; no
  score correctness, no locked fixtures.
- **Playlist / library “orchestrators”** — name collision with musical
  orchestration.
- **Game / hand-gesture music controllers** — unrelated.

Useful only for marketing language or future audio→score pipelines (OMR,
transcription), not for the core theory moat.

---

## 8. How this was found (refresh recipe)

Scanned **2026-07-21** via `gh search repos` + web search. Useful queries:

```text
# Classical / SATB / RNA
gh search repos "SATB part writing" OR chorale --language=Python --sort=updated
gh search repos "roman numeral analysis" --sort=updated
gh search repos "harmonic analysis" music21 --sort=updated
gh search repos "part-writing OR partwriting OR voice-leading" --sort=updated

# Arrangement / reharm
gh search repos "music reharmonization" OR reharmonize --sort=updated
gh search repos "melody harmonization" OR "automatic harmonization" --sort=updated
gh search repos "accompaniment generation" OR AccoMontage --sort=updated

# AI theory / LLM
gh search repos "AI music theory" OR "LLM music composition" --sort=updated
gh search repos "functional harmony" progression generator --sort=updated

# Architecture twins
gh search repos "Roman numerals" voice-led OR "theory engine" --sort=updated
```

Also check: arXiv `cs.SD` / ISMIR / ICASSP music tracks; topics
`music-generation`, `music-theory`, `symbolic-music`.

When refreshing, **re-verify stars and dates** — many 2026 student repos are
one-shot scaffolds.

---

## 9. Strategic patterns (what “winning” looks like)

Observed across the best repos:

1. **Hard checkers beat soft models for classical.** Parallel fifths, LT
   resolution, ranges — either pass or fail. Bach can *calibrate* soft costs;
   textbooks define hard gates.
2. **RN (or structured chord symbols) as the AI interface.** Never free-form
   MIDI from the LLM if correctness matters (Resonance, Harmonyx L plan).
3. **Corpus oracles** (When-in-Rome, Bach 371, outer-voice tables) beat pure
   textbook when “taste” is required.
4. **OSMD / VexFlow + Play** is table stakes for demos and pedagogy.
5. **MCP / agent tools** are the 2026 distribution channel for theory engines.
6. **Locked tests / false-alarm checks on Bach** (run checkers on real
   chorales) separate serious engines from toys.
7. **Pedagogy products** (PartWise-style check + feedback) may be a larger
   market than pure generation.

Harmonyx already sits on (1)(2)(4)(6) with L1–L3, locked part-writing fixtures,
and OSMD. Gaps vs landscape: M4 check UX, L4 client, richer analyzer (NCT,
fermata cadences, neural RNA optional), arrangement track deferred.

---

## 10. Suggested deep-dive order (for later sessions)

Do **not** implement from this list without an explicit human chunk. Study order:

| Priority | Repo | Session goal |
|----------|------|--------------|
| 1 | **resonance** | Map their JSON RN schema + validate/fallback to L4+ |
| 2 | **choral-counterpoint** | Compare rule set + Bach oracle to `rules.py` / PARTWRITING-RULES |
| 3 | **PartWise** | UX + API shape for M4 `/check` |
| 4 | **chorale-optimizer** | Alternative search/fix vs DP realizer |
| 5 | ~~**choral-llm-workbench**~~ | **Done** — MusicXML + LLM reharm; see `docs/research/05-choral-llm-workbench.md` |
| 6 | ~~**When-in-Rome**~~ | **Done** — corpus expansion for L1 few-shot + analyzer eval; see `docs/research/06-when-in-rome.md` |
| 7 | ~~**AccoMontage2 + POP909**~~ | **Done** — pop melody→chords+texture pipeline; see `docs/research/07-accomontage2.md` |
| 8 | ~~**JJazzLab**~~ | **Done** — product-completeness lessons (SPI separation, retrieval-based generation); see `docs/research/12-jjazzlab.md` |
| 8.5 | ~~**AugmentedNet**~~ | **Done** — neural multi-task RNA baseline + accuracy ceiling reference; see `docs/research/11-augmentednet.md` |
| 9 | **rnbert / muMoE-RNBERT** | Only if investing in neural RNA |
| 10 | **ai-music-theory + MuTheoryEval** | Explainer grounding / LLM trust for theory chat |

---

## 11. Domain expansion backlog (idea only — not scheduled)

If “king of classical × AI” becomes a multi-product strategy:

| Domain | Building blocks from this map | Harmonyx seed |
|--------|-------------------------------|---------------|
| Student part-writing tutor | PartWise + locked rules + OSMD | M4 `/check` + generate |
| RNA research / app | When-in-Rome + RNBERT + music21 | `/analyze` + eval |
| Chorale / hymn factory | choral-counterpoint patterns + grammar | `/progression` + `/generate` |
| Choir reharm / arrange | choral-llm-workbench | MusicXML roundtrip + spice |
| Melodic harmonization | AccoMontage2, EMO_Harmonizer | New “melody-in” track |
| Counterpoint pedagogy | Fux generators + checkers | New track or mode |
| Agent-native theory | thiri / music21 MCP | Expose Harmonyx tools |
| Orchestration / reduction | MIT projective orch, audio→score | Far future |
| Note-level LLM edit interface | choral-llm-workbench's IKR-light + TLR (line-per-event text) pattern — see research #05 §2 | If a future feature needs an LLM to touch literal note/rest content (reharmonize an existing chorale, explain a passage) rather than only RN symbols. Not needed for current RN-based L4. |
| Analyzer eval against real ground truth | When-in-Rome's 371 Bach chorales + slice-based RN-vs-score agreement scoring — see research #06 §3–4 | Next time analyzer A7 (RN-agreement eval) is scoped; reimplement the matching idea, don't vendor `romanUmpire.py` (CC BY-SA + coupled to WiR's layout). |
| Richer grammar features (Neapolitan 6th, borrowed/modal-mixture chords, Picardy third, pedal point/sustained bass) | Shimaoka-SATB-SkillSet's prefix-degree-suffix notation names each as a distinct feature Harmonyx doesn't model — see research #08 §3 | If the rule grammar is ever extended past Q3c; not urgent, just a named checklist so the gap isn't re-discovered from scratch. |
| Augmented-sixth chords | Two independent peers now flag this gap: When-in-Rome's `It6`/`Fr43`/`Ger65` notation (#06 §2) + Shimaoka's usage rules (only at D₂, ⟨2nd⟩ disposition default) (#08 §3) | If/when scoped: use WiR's wire syntax, Shimaoka's "when to use which form" theory. |
| Pre-solve infeasibility diagnostics ("why would this fail" before/instead of a bare error) | music-arranger's `verify_solver.py` names specific failure modes (melody-outside-scale, empty-domain conflict, cadence truncation, cadence-vs-melody conflict) before solving — see research #09 §3 | If M4 `POST /check` or `POST /generate`/`POST /progression` error responses are revisited; independent of the DP-vs-CP-SAT question. |
| Global constraint solving (CP-SAT) as a DP-realizer alternative | music-arranger uses Google OR-Tools CP-SAT for one-pass joint hard+soft constraint optimization instead of Harmonyx's sequential DP — see research #09 §2 | Only relevant if the rule grammar ever needs a genuinely non-local constraint the DP realizer's step-adjacency scoring can't express; not needed today, locked DP fixtures stay as-is. |
| Agent-native theory (MCP exposure of `/analyze` + `/generate` + future `/check`) | thiri-mcp (hosted-API-client template, production hardening: timeout/quota/structured-error patterns) vs. music21-mcp (`@mcp.tool()`-over-local-library template, closer to Harmonyx's own shape) — see research #10 | If an MCP-exposure chunk is ever scoped: use music21-mcp's low-boilerplate local-wrapper pattern + thiri-mcp's hardening checklist. Not on the open queue today. |
| Analyzer neural-baseline ceiling | AugmentedNet's published ~45-52% full-RN accuracy on a trained, multi-task, synthetic-augmented model — see research #11 | Cite as an external sanity-check number next time analyzer eval (A7) results are reported; don't chase it as a target, different eval methodology. |
| Third realization-strategy option: pattern-retrieval | JJazzLab's JJSwing engine matches/splices small hand-curated pre-voiced MIDI phrases by chord-sequence + tag, no ML/no solver — see research #12 §2 | If a second, faster/looser generation mode is ever wanted alongside the locked DP realizer, alongside CP-SAT (#09) and VAE-embedding retrieval (#07) as the other two known alternatives. Not scoped; DP + locked fixtures stay default. |
| Explicit plugin SPI as a product decision | JJazzLab's public `Rhythm`/`MusicGenerator`/`RhythmParameter` interfaces + standalone `JJazzLabToolkit` jar let third parties add style plugins without touching the app — see research #12 §4 | If Harmonyx's generation engine is ever opened to alternate realization strategies or third-party rule sets, design the interface deliberately (like this) rather than discovering the seam via refactor. Not scoped today. |

---

## 12. Relation to project docs

| Doc | Role vs this file |
|-----|-------------------|
| [`START-HERE.md`](START-HERE.md) | Current Harmonyx product status |
| [`STATUS.md`](STATUS.md) | Technical snapshot |
| [`LLM-PROGRESSION-SPEC.md`](LLM-PROGRESSION-SPEC.md) | L0–L7 plan (use Resonance as external peer) |
| [`PARTWRITING-RULES.md`](PARTWRITING-RULES.md) | Locked classical rules |
| [`ROADMAP.md`](ROADMAP.md) | Discussion ideas (may absorb items from §11) |
| [`AI-DIARY.md`](AI-DIARY.md) | Chronological log of when this scan happened |

---

## 13. Deep-dive research notes

Written notes (read these before re-cloning peers):

| # | File | Repo |
|---|------|------|
| 01 | [`docs/research/01-resonance.md`](research/01-resonance.md) | will825/resonance — L4 architecture twin |
| 02 | [`docs/research/02-choral-counterpoint.md`](research/02-choral-counterpoint.md) | DashWieland/choral-counterpoint — SATB checker + Bach oracle |
| 03 | [`docs/research/03-partwise.md`](research/03-partwise.md) | cjohanson64-netizen/PartWise — M4 `/check` UX + evaluate API |
| 04 | [`docs/research/04-chorale-optimizer.md`](research/04-chorale-optimizer.md) | 604korupt/chorale-optimizer — beam + fixups vs DP realizer |
| 05 | [`docs/research/05-choral-llm-workbench.md`](research/05-choral-llm-workbench.md) | asb-42/choral-llm-workbench — IKR-light/TLR note-level LLM interface pattern |
| 06 | [`docs/research/06-when-in-rome.md`](research/06-when-in-rome.md) | MarkGotham/When-in-Rome — RN meta-corpus for L1 few-shot + analyzer eval |
| 07 | [`docs/research/07-accomontage2.md`](research/07-accomontage2.md) | billyblu2000/AccoMontage2 + music-x-lab/POP909-Dataset — pop melody→chords+texture arrangement pipeline |
| 08 | [`docs/research/08-shimaoka-satb-skillset.md`](research/08-shimaoka-satb-skillset.md) | ShikiSuen/Shimaoka-SATB-SkillSet — LLM-context-only Swing Theory SATB knowledge base; counter-example to "LLM proposes, code enforces"; 2nd source flagging the augmented-sixth notation gap |
| 09 | [`docs/research/09-music-arranger.md`](research/09-music-arranger.md) | scarrow/music-arranger — Claude tool-call NL extraction + Google OR-Tools CP-SAT SATB solver; "L4 + realizer, one architecture" twin; steals: pre-solve infeasibility diagnostics, soft/hard scale confirmation; don't steal: CP-SAT replacing DP, wide NL→full-arrangement tool schema |
| 10 | [`docs/research/10-thiri-mcp-and-music21-mcp.md`](research/10-thiri-mcp-and-music21-mcp.md) | BluesPrince/thiri-mcp + SimonsonM/music21-mcp — two opposite answers to "how to expose theory ops as MCP tools" (hosted-proprietary-client vs. local-open-wrapper); steals: production-hardening checklist, low-boilerplate `@mcp.tool()` pattern; don't steal: hosted-API-with-quota architecture (doesn't apply — Harmonyx is the engine) |
| 11 | [`docs/research/11-augmentednet.md`](research/11-augmentednet.md) | napulen/AugmentedNet — CRNN multi-task neural RNA (11-14 output heads: key/degree/quality/inversion/voice-pitches, reconciled via pcset-cosine match at inference, not raw argmax); produced When-in-Rome's automatic-analysis files; steals: decomposed-task + voted-reconciliation pattern, corpus-registry layout, published accuracy ceiling (~45-52% full-RN even for a trained model) as an analyzer-eval reference point; don't steal: the network itself, synthetic-texturization training strategy |
| 12 | [`docs/research/12-jjazzlab.md`](research/12-jjazzlab.md) | jjazzboss/JJazzLab — mature jazz backing-track app (NetBeans RCP, 65-module Maven tree); product-completeness study, not a theory peer; steals: strict model/engine/UI separation behind a public `Rhythm`/`MusicGenerator` SPI, JJSwing's concatenative pattern-retrieval generation (hand-curated MIDI phrase bank scored by chord-sequence+tag, no ML/solver) as a third lightweight realization-strategy alternative next to CP-SAT (#09) and VAE-embedding retrieval (#07); don't steal: NetBeans/desktop-app infra, jazz-specific content |

Research queue #01–#07 (the originally planned order) is complete. Further
deep-dives now come from `docs/RESEARCH-QUEUE.md` (Tier 1–4 candidates found
in the 2026-07-21 follow-up scans, plus human-flagged repos) — see that file
for the live queue and suggested order. #08–#12 are entries from that queue;
the rest still need an explicit human ask.

### PartWise one-liner (after #03)

Student SATB evaluator: OSMD editor → `POST /api/satb/evaluate` → pass/warn/fail
checks, issue-weighted %, note colors. **Steal UX/API projection; keep our
`rules.py` depth; skip TryAngleTree runtime.**

### chorale-optimizer one-liner (after #04)

Soprano MIDI + chord symbols → ATB via **beam (w=40) + ≤6 iterative rule
fixups**; Tkinter + VexFlow/WebAudio; 81 tests; always emits (best-effort).
**Steal:** cadence phrase splits, residual flags, N6/Ger/secondary vocab
checklist, optional best-effort *mode* ideas. **Keep** fail-closed DP + locked
fixtures as default; do not replace `realize.py` with soft beam+fix.

---

## 14. Changelog

| Date | What |
|------|------|
| 2026-07-21 | Initial landscape from two GitHub/web research passes (Harmonyx-adjacent + broad arrange/AI-theory). |
| 2026-07-21 | Research #11 (AugmentedNet) added; §4.2, §10, §13 updated. |
| 2026-07-21 | Research #12 (JJazzLab) added; §5.1, §10, §11, §13 updated. |
| 2026-07-21 | Deep-dives #01 Resonance, #02 choral-counterpoint → `docs/research/`. |
| 2026-07-21 | Deep-dive #03 PartWise → `docs/research/03-partwise.md` (M4 UX/API blueprint). |
| 2026-07-21 | Deep-dive #04 chorale-optimizer → `docs/research/04-chorale-optimizer.md` (beam+fix vs DP). |
| 2026-07-21 | Deep-dive #05 choral-llm-workbench → `docs/research/05-choral-llm-workbench.md` (IKR-light/TLR pattern). |
| 2026-07-21 | Deep-dive #06 When-in-Rome → `docs/research/06-when-in-rome.md` (RN meta-corpus; L1 few-shot + A7 eval source). |
| 2026-07-21 | Deep-dive #07 AccoMontage2 + POP909 → `docs/research/07-accomontage2.md` (pop arrangement pipeline; Tier B, not classical — arrangement-track reference only). Closes the #01–#07 research queue. |
| 2026-07-21 | New candidates found via follow-up GitHub scans + a human-flagged repo → `docs/RESEARCH-QUEUE.md` (11 repos, tiered). |
| 2026-07-21 | Deep-dive #08 Shimaoka-SATB-SkillSet → `docs/research/08-shimaoka-satb-skillset.md` (LLM-context-only SATB knowledge base; counter-example to code-enforced validation; 2nd source on augmented-sixth gap). |
| 2026-07-21 | Deep-dive #09 music-arranger → `docs/research/09-music-arranger.md` (Claude tool-call NL extraction + CP-SAT SATB solver; DP-vs-CP-SAT comparison; pre-solve diagnostics idea for M4). |
| 2026-07-21 | Deep-dive #10 thiri-mcp + music21-mcp → `docs/research/10-thiri-mcp-and-music21-mcp.md` (hosted-proprietary vs. local-open MCP theory server architectures; hardening checklist + low-boilerplate wrapper template). Closes Tier 1 of `RESEARCH-QUEUE.md`. |

When you re-scan, append a changelog row and note new Tier S/A finds at the top
of §3–§4.
