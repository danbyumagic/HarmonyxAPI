# Research #11 — `napulen/AugmentedNet`

**Repo:** github.com/napulen/AugmentedNet (MIT, 50★, 11 forks, Jupyter
Notebook + Python). Last push seen at review time: 2024-02-11 (the
2026-07-21 "actively maintained" note in `RESEARCH-QUEUE.md` was stale —
worth a correction there).

**What it is:** the neural Roman-numeral-analysis (RNA) network from Néstor
Nápoles López's PhD dissertation (McGill, 2022) and the ISMIR 2021 paper
*"AugmentedNet: A Roman Numeral Analysis Network with Synthetic Training
Examples and Additional Tonal Tasks"* (with M. Gotham and I. Fujinaga). It is
the tool that produced the `analysis_automatic.rntxt` files sitting inside
When-in-Rome's corpus (research #06) — this deep-dive reads that upstream
tool directly rather than just its output.

Used in production by Sibelius, Vimu.app, and MusicLang (per README).

## Architecture

CRNN (Convolutional Recurrent Neural Network), defined in `models.py`:

- Per-input-representation stack: several `Conv1D` blocks (dilating kernel
  sizes `2^i`, shrinking filter counts `2^(blocks-1-i)`) each followed by
  `BatchNorm` + `ReLU`, concatenated back onto the running tensor
  (DenseNet-style skip connections) — 6 blocks by default.
- Multiple input streams (one score-derived feature per stream) get
  concatenated after their conv stacks.
- Shared trunk: `Dense(64)` → `Dense(32)` → two stacked `Bidirectional GRU`
  layers (30 units each), all with `BatchNorm`.
- Multi-task output heads: one `Dense` layer per task, named after the task
  (`RomanNumeral31`, `LocalKey38`, etc.), all reading the same shared GRU
  output — classic hard-parameter-sharing multi-task learning.

A second, older architecture (`Micchi2020`) is included for comparison —
DenseNet + pooling + a single BiGRU + `TimeDistributed(Dense)`, single-input,
single shared tanh layer before the multi-task heads.

## The "additional tonal tasks" (the paper's actual contribution)

This is the core idea worth remembering: instead of training the network to
predict a Roman numeral *string* directly (a huge, sparse label space), it
decomposes the analysis into **11–14 simultaneous multi-task output heads**,
defined in `output_representations.py`, each with its own one-hot vocabulary
and its own `Dense` head sharing the same GRU trunk:

| Head | Vocab size | What it predicts |
|---|---|---|
| `LocalKey38` / `TonicizedKey38` | 38 | key context, including secondary tonicization |
| `PitchClassSet121` | 121 | the raw pcset sounding, transposition-invariant |
| `RomanNumeral31` | 31 | the *common* RN token only (see below) |
| `PrimaryDegree22` / `SecondaryDegree22` | 22 | scale-degree numerator/denominator (for `/V` style secondary chords) |
| `Bass35` / `Tenor35` / `Alto35` / `Soprano35` | 35 | actual predicted pitch spelling per voice |
| `Inversion4` | 4 | inversion figure |
| `HarmonicRhythm7` | 7 | chord-change timing/duration bucket |
| `ChordRoot35` / `ChordQuality11` | 35 / 11 | (optional heads, off by default in `cli.py` `DefaultArguments.npz`) |

At **inference time** the network doesn't just decode `RomanNumeral31`
directly — `inference.py`'s `resolveRomanNumeralCosine()` reconstructs the
final RN by combining several heads: it builds a pitch-class-set vector from
the four predicted SATB voice heads *plus* the raw pcset head *plus* the
tonicized-key numerator, does a **cosine-similarity match against a
precomputed `frompcset` chord-vocabulary table** (`chord_vocabulary.py`) to
find the best-fitting chord/RN/quality combination for that key, and only
then appends the inversion figure and secondary-key denominator
(`getTonicizationScaleDegree`). In other words: the "31-class" head is a
coarse/common-case shortcut, and the real answer at inference is a **learned
ensemble vote reconciled by geometry (pcset cosine similarity)**, not any
single softmax argmax. That's a deliberately different pattern from either
"one huge classifier" or "code enforces after LLM proposes."

## Data pipeline

- Multiple named training-corpus collections in `AugmentedNet/data/`: `bps`
  (Beethoven piano sonatas), `wir` (When-in-Rome — confirmed the direct
  corpus link: `wir.py` pulls `rawdata/When-in-Rome/Corpus/.../analysis.txt`
  paired against `music21_corpus` `.mxl` files, including the same Bach
  chorale set research #06 studied), `haydnsun`, `tavern`, `abc_dcml`,
  `keymodt`, `mps`, `wirwtc`.
- Score+RomanText pairs → flattened to `.tsv` (`dataset_tsv_generator.py`) →
  encoded to `.npz` numpy arrays for training (`dataset_npz_generator.py`).
- **Synthetic data augmentation** is a first-class strategy: RN-labeled
  "block chord" templates get **texturized** (`texturizers.py`) into
  plausible-looking note patterns, either once per file or once per
  transposition, and mixed in via `--syntheticDataStrategy
  {syntheticOnly,concatenate}`. Ablations in the README table show this adds
  a real but modest accuracy gain (e.g. RN 43.3→44.6 for the 6-task config,
  45.0 vs 43.1 for the 11-task config) — synthetic data helps, doesn't
  transform results.
- **Transposition augmentation** (`TRANSPOSITIONKEYS`, `TransposeKey` /
  `TransposePitch` / `TransposePcSet` in `cache.py`) is applied at
  encode-time per-key, another standard augmentation for key-invariant tasks.

## Accuracy (from the paper's tables, reproduced in README)

Best full config (`AugmentedNet 11+`, i.e. 11 tasks + synthetic data),
weighted-average accuracy on the paper's combined test set: **Key 82.9%,
Degree 67.0%, Quality 79.7%, Inversion 78.8%, Root 83.0%, common-RN 65.6%,
full-RN (strict) 46.4–51.5%** depending on scoring convention (`RN conv` vs
`RN alt`). Cross-corpus breakdown shows real variance: WTC (Bach
Well-Tempered Clavier) full-RN drops to ~46-47%, TAVERN (variation sets)
key accuracy is highest (88.7%) but full-RN lowest region (42.6-52.9%).
Compared against Micchi et al. 2020 and older CS18/CS19/CS21 baselines,
AugmentedNet wins on every reported axis on the shared BPS test set.

Takeaway for Harmonyx: **full strict Roman-numeral accuracy tops out
around 45-52%** even for this well-engineered, multi-task, synthetic-data-
augmented, purpose-built network trained on a curated multi-corpus dataset.
That's a useful ceiling/sanity-check number — Harmonyx's rule-based analyzer
sits at ~65% key accuracy (per `docs/START-HERE.md`) using a completely
different (deterministic, no training) approach, so on the *key* sub-task
alone the comparison isn't unfavorable, though the two accuracy definitions
aren't directly comparable (this is corpus-eval accuracy against
professional annotations across a 7-corpus mixed dataset, not Harmonyx's own
eval set).

## Steal / don't-steal

**Steal (ideas, not code):**
- **Decomposing "Roman numeral" into independent sub-tasks** (key, degree,
  quality, inversion, bass/voice pitches) that get reconciled at the end,
  rather than treating the RN as one opaque string to classify/generate. If
  Harmonyx ever explores a neural or LLM-assisted analyzer path (A7 eval
  work, Q4), this decomposition — and specifically **reconciling multiple
  weak signals via a small deterministic voting/similarity step** (their
  pcset-cosine match) rather than trusting one head's argmax — is a pattern
  worth reusing even in a non-neural context, e.g. combining several
  heuristic analyzer signals via a scoring function instead of a single
  rule cascade.
- The **corpus-registry pattern** (`data/*.py`, one small file per named
  corpus mapping RomanText annotations to source scores) is a clean way to
  keep multi-corpus training/eval data organized — relevant if Harmonyx's
  own analyzer eval set (`eval/`) ever grows beyond one corpus.
- Their **published accuracy ceiling numbers** are a useful external
  reference point when reporting/contextualizing Harmonyx's own analyzer
  eval numbers (A7, Q4) — "even a trained neural multi-task model tops out
  near 45-52% full-RN accuracy" tempers expectations for what "good"
  looks like on this task.

**Don't steal:**
- The network itself — training a CRNN is a multi-week ML investment
  (TensorFlow/Keras, mlflow tracking, GPU training) totally out of scope for
  Harmonyx's deterministic-analyzer product direction; nothing in
  `AGENTS.md`'s open queue calls for a from-scratch neural model.
- Synthetic block-chord texturization as a training-data strategy — only
  relevant if Harmonyx ever trains something itself; not applicable to a
  rule-based or LLM-prompted approach.
- Their RomanText output format needs no adoption — Harmonyx already has
  its own RN grammar (`docs/RICH-GRAMMAR-SPEC.md`) and doesn't need this
  tool's specific `Cad64`/`/V`-style text serialization; it's compatible in
  spirit with the syntax already validated by research #06, nothing new
  here.

## Open questions / follow-ups

- If Q4 (Analyzer A7 eval) ever wants a second, independent-baseline
  accuracy number to compare Harmonyx's rule-based analyzer against, running
  the **pre-trained `AugmentedNet.hdf5`** checkpoint (shipped in the repo,
  ~50MB, git-lfs or release asset) via `python -m AugmentedNet.inference`
  against Harmonyx's own eval fixtures would be a cheap way to get one —
  no training required, just inference. Not scoped now; flagging for later.
- rnbert / muMoE-RNBERT (Tier 2 #6, still unread) would be the modern
  transformer-era comparison point to this 2021-era CRNN — worth reading
  together if a neural RNA path is ever seriously considered, to see how
  much the field has moved since AugmentedNet.
