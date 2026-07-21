# Research #13 — rnbert + muMoE-RNBERT

- **rnbert**: `malcolmsailor/rnbert` — Sailor, "RNBert: Fine-Tuning a Masked
  Language Model for Roman Numeral Analysis," ISMIR 2024. 7★, no license
  file, paper CC BY 4.0.
- **muMoE-RNBERT**: `TomusD/muMoE-RNBERT` — Triantafyllou, Nicolaou,
  Panagakis, "Interpretable Music Harmonic Analysis Through Multilinear
  Mixture of Experts," ICASSP 2026 (+ accompanying MSc thesis). 2★, MIT.
  Extends RNBert's architecture with an interpretability layer; read as one
  chunk since it's a direct fork/extension, not an independent peer.

Read: both READMEs in full; the full RNBert paper (camera-ready PDF, all 8
pages incl. Table 4 results and references); `.gitmodules` (4 satellite
repos: `musicbert_fork`, `music_df`, `write_seqs`→`write_chord_tones_seqs`,
`reprs`); `data_splits/*.txt` (corpus manifest, 1,103 train / 149 valid / 146
test paths under `ABCData/`). Did not clone/run the code (fairseq + MusicBERT
checkpoint + GPU training pipeline — a multi-day undertaking, out of scope
for a research chunk) or read the muMoE thesis PDF (gated behind a Google
Drive link, not fetched).

## 1. What it is

RNBert fine-tunes **MusicBERT** (Zeng et al. 2021 — a BERT-base transformer
pretrained on 1M+ MIDI files using the OctupleMIDI encoding: 8 note features
—time-sig, tempo, bar, metric position, pitch, duration, velocity, and here
also an instrument slot—embedded and concatenated per note-token) for Roman
numeral analysis, via **token classification**: every note gets a predicted
key + degree + quality + inversion, logits of simultaneous notes are averaged
after "salami-slicing" the score into a purely homophonic grid, and adjacent
1000-token analysis windows (MusicBERT's max sequence length) are stitched
back together by cross-fading overlapping logits. A Viterbi pass over the key
logits (self-transition upweighted) suppresses implausibly brief key changes.
Optionally, an RN prediction head is **conditioned on the key** (via a 2-layer
MLP embedding of the key token, concatenated into the classification head
input) — trained with teacher-forcing on ground-truth keys, evaluated using
the model's own separately-trained key predictions.

muMoE-RNBERT is the same pipeline with the feed-forward layers in
MusicBERT's last 3 (of 12) layers replaced by **Multilinear Mixture of
Experts (μMoE)** layers — a CP-tensor-decomposition MoE technique from
Oldfield et al. (NeurIPS 2024, vision-model origin, not music-specific) —
using 48 experts. The point isn't higher accuracy (the README explicitly
says "without sacrificing performance," not improving it); it's
**interpretability**: after training, they extract per-note expert-activation
coefficients and build (a) quantitative bar charts of which musical labels
(key, cadence type, etc.) most often co-occur with a given expert firing
above a threshold, and (b) piano-roll heatmaps overlaying activation on the
actual score, so you can visually confirm e.g. "expert 17 fires on secondary
dominants" or similar per-expert specialization claims.

## 2. Corpus

**1,404 scores / ~1.29M notes / ~161k chords** — the largest RN-labeled
corpus assembled to date, combining the Digital & Cognitive Musicology Lab's
Beethoven/Mozart/19th-century-piano corpora, TAVERN (Beethoven+Mozart
variations), the Beethoven-piano-sonatas set from Chen & Su 2018, and
**When-in-Rome** (research #06) in full — i.e. this corpus is a superset of
WiR's ~1,300 analyses. For direct comparability with AugmentedNet (#11) and
ChordGNN, they also report a second training run on exactly AugmentedNet's
v1 split (347 scores). Two data-augmentation tricks on the training set only:
transpose to all 12 keys, and duration-scale ×2 (toward the corpus mean).
Synthetic-data augmentation (AugmentedNet/ChordGNN's technique) was tried and
**did not help** here — plausible reason given: RNBert's input is raw notes,
so synthetic vs. real is more visually/structurally distinguishable to the
model than it is to a model consuming pitch-vector time steps.

## 3. Headline results (Table 4, all "proportion of time-steps correct" at
32nd-note resolution)

| Model (AugmentedNet-v1 split, for fair comparison) | Degree | Quality | Inversion | Key | RN+root |
|---|---|---|---|---|---|
| AugmentedNet (#11) | .670 | .797 | .788 | **.829** | .464 |
| ChordGNN+(Post) | .714 | .784 | **.803** | .813 | .518 |
| **RNBert (key-cond.)** | **.731** | **.819** | .796 | .825 | **.574** |

| Model (full 1,404-score corpus) | Degree | Quality | Inversion | Key | RN-root |
|---|---|---|---|---|---|
| RNBert (unconditioned) | .762 | **.867** | .872 | .822 | .620 |
| RNBert (key-cond., predicted key) | .749 | .864 | **.872** | **.823** | **.624** |
| RNBert (key-cond., teacher-forced) | .859 | .865 | .872 | n/a | n/a |

Two things worth internalizing for Harmonyx's own analyzer eval framing:
- **The composite metric (RN+root/RN-root) is where RNBert's margin is
  largest**, not the individual sub-tasks — the paper's own read is that
  pretraining buys *coherence between* the predicted key/degree/quality/
  inversion, not just marginal per-task accuracy. A model that's "only" a
  few points better per-axis can still be dramatically better on the
  composite label because its sub-predictions agree with each other more
  often (worked example: an unconditioned model can get key wrong but
  degree "right" by accident, which the paper walks through with a real
  Beethoven quartet cadence — see §4.1 of the paper).
- **Key prediction on the full corpus (.822) is roughly the same as
  AugmentedNet's (.829) despite RNBert winning everywhere else** — because
  the full corpus includes much more 19th-century material (via WiR) that
  modulates far more freely than the AugmentedNet-v1 subset's
  Beethoven/Mozart-heavy content. This is a second independent data point
  (after research #11's ceiling number) that **RN/key accuracy numbers are
  only comparable across models trained/evaluated on the same corpus** —
  relevant caveat if Harmonyx's own analyzer A7 eval is ever benchmarked
  against any of these published figures.
- The paper is explicit that a large fraction of "wrong" predictions are
  probably **valid alternate analyses** (modulation vs. tonicization
  being the standing example, illustrated with the same Beethoven excerpt
  used for the key-conditioning discussion) — this may be placing a real
  ceiling under ~85-90% on any RN eval regardless of model quality, echoing
  research #11's ~45-52% full-RN-composite ceiling finding from a different
  angle (RNBert's own composite ceiling looks closer to ~60-62%, well above
  AugmentedNet's ~46%, but still far from 100%).

## 4. Comparison to Harmonyx

Harmonyx's analyzer (`app/analysis/`) is fully rule-based via music21, not
neural, and there is no plan on `docs/START-HERE.md`'s open queue (Q4:
"Analyzer A1/A2/A7") to add a neural path — Q4 is NCT filtering, fermata
cadences, and RN-agreement eval, all still rule/heuristic work. RNBert/
muMoE-RNBERT are relevant only as:

1. **An external accuracy ceiling reference**, alongside AugmentedNet
   (#11) — now Harmonyx has two independently-published numbers (~46-52%
   AugmentedNet full-RN, ~57-62% RNBert composite RN) bracketing what
   "good" looks like for full Roman-numeral-composite accuracy on
   real corpora, useful context if analyzer A7 (RN-agreement eval) is ever
   reported publicly.
2. **A concrete illustration of the "multitask decomposition + coherence"
   tradeoff** (degree/quality/inversion/key predicted separately, then
   recombined) that is architecturally close to how Harmonyx's own analyzer
   composes an RN string from separate music21-derived signals (root, key,
   inversion) — the decoherence failure mode RNBert's key-conditioning
   fixes (predicting "I6" when the underlying chord is actually vi in a
   different key) is a plausible bug shape for rule-based decomposition too,
   worth keeping in mind if A1/A2 heuristics ever get restructured into
   separately-scored sub-decisions.
3. **muMoE's interpretability tooling (expert-activation-vs-label
   correlation, piano-roll heatmap overlay)** is a technique, not a
   dependency — if Harmonyx ever wants to *explain* an analyzer decision
   visually (e.g. "why did this get flagged as a NCT" for a future A1
   feature), the piano-roll-heatmap-of-a-per-decision-signal idea is a
   reusable UI pattern independent of whether the underlying model is
   neural or rule-based.

No overlap with the generation/realizer side (`app/generation/`) at all —
both papers are pure analysis-direction (score → RN), same as When-in-Rome
and AugmentedNet.

## Steal / don't-steal

**Steal (ideas only):**
- The "predict sub-components separately, then explicitly measure/fix
  cross-component coherence" framing — useful vocabulary for describing
  Harmonyx's own analyzer failure modes even without any neural component.
- Citing both AugmentedNet's (~46-52%) and RNBert's (~57-62%) full-RN
  composite-accuracy numbers together as bracketing "state of the art" next
  time analyzer eval results are reported, rather than either number alone.
- The general point that RN eval numbers are corpus-dependent (full corpus
  vs. AugmentedNet-v1 subset) and not directly comparable across papers
  without matching splits — a caution to apply to Harmonyx's own ~65% key
  eval number (`docs/START-HERE.md`) if it's ever compared externally.

**Don't steal:**
- The model, training pipeline, or MusicBERT/fairseq dependency itself —
  Harmonyx's analyzer is rule-based by design and there's no open task to
  add a neural path.
- muMoE's CP-decomposition MoE layer technique — it's a general vision-
  model interpretability tool (Oldfield et al. 2024) bolted onto RNBert for
  a research paper's ablation study, not something with a natural home in
  Harmonyx's stack.

## Open questions (not investigated further)

- Whether RNBert's released HuggingFace-ported checkpoints (mentioned in
  `malcolmsailor/musicbert_hf`) could be called as an inference-only API
  without the full fairseq training environment — not checked; would only
  matter if a neural RNA path were ever actually scoped, which it isn't
  today.
- The muMoE thesis's ablation numbers (accuracy delta with/without μMoE
  layers, expert-count sweep 48/256/1024) — gated behind a Google Drive
  link, not fetched; the README's own framing ("without sacrificing
  performance") suggests the delta is small either way.
