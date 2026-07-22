# Soprano alternatives (Generate tab)

## Problem

The Generate tab's realizer (`app/generation/realize.py`) picks voicings via
an exact Viterbi/DP search (`_best_path`) that minimizes total
`rules.transition_cost` across the whole progression. This is a single
deterministic global optimum: for a given progression + key, the soprano
line is always the same. Users have noticed the soprano melody often looks
the same across different realizations and want to see other reasonable
options, not just the one the DP happens to minimize cost on.

## Goals

- After clicking **Realize**, show up to 3 distinct soprano-line options for
  the current progression, ranked by voice-leading cost (best first).
- Picking a different option re-realizes the full SATB score with that
  soprano, using machinery that already exists (`POST /generate` already
  accepts an explicit `soprano` array).
- Zero behavior change for anyone who ignores the new options: the default
  (option 1) must be identical to what `_best_path` returns today.

## Non-goals (this iteration)

- Manual per-note soprano editing (clicking/dragging individual notes to a
  different chord tone). That's a heavier UI feature; today's ask is "show
  me a few good options," not "let me hand-edit."
- True k-best Viterbi (provably cost-ranked k-best distinct paths). See
  "Alternatives considered."
- A configurable option count. Hardcoded at 3 for this iteration (YAGNI);
  trivial to parameterize later if wanted.
- Full MusicXML for every option up front. Only the chosen option gets
  fully realized.

## Design

### Backend: `soprano_alternatives`

New function in `app/generation/realize.py`:

```python
def soprano_alternatives(
    progression: List[str], key_like: _chords.KeyLike, n: int = 3
) -> List[List[int]]:
    """Up to n distinct soprano lines (MIDI ints, one per chord), ranked by
    voice-leading cost, most preferred first. The first entry is always
    identical to what realize()'s internal _best_path produces today.
    """
```

Algorithm: candidate pruning + re-run, not true k-best Viterbi.

1. Run `_best_path` once, using the full `candidate_voicings()` pool at each
   beat, exactly as `realize()` does today. This is option 1.
2. Record the soprano pitch used at each beat index.
3. To generate the next option: rebuild each beat's candidate pool via
   `candidate_voicings(figure, key_like)`, then filter out any voicing whose
   `.soprano` matches a pitch already used at that beat index by a prior
   option -- **only if** that filtering leaves at least one candidate at
   that beat (a beat with just one legal chord-tone soprano is never
   starved out). Re-run `_best_path` over the filtered pools.
4. If the resulting soprano tuple is identical to one already found, stop
   early and return what's been found so far (no artificial padding, no
   infinite loop -- there's a hard cap of `n` attempts regardless).
5. Repeat until `n` distinct options are found or the search is exhausted.

This reuses `_best_path` and `rules.transition_cost` completely unchanged;
the only new logic is the per-beat pitch-exclusion filter between runs.

### API: `POST /generate/soprano-options`

New endpoint alongside `/generate`. Request body: same shape as
`GenerateRequest` minus `soprano` (`key`, `progression`, `time_signature`).

Response:

```json
{
  "options": [
    { "soprano": [72, 72, 71, 72], "pitches": ["C5", "C5", "B4", "C5"] },
    { "soprano": [76, 69, 74, 72], "pitches": ["E5", "A4", "D5", "C5"] },
    { "soprano": [67, 65, 67, 72], "pitches": ["G4", "F4", "G4", "C5"] }
  ]
}
```

`pitches` is `soprano` rendered as note names (music21 `Pitch(midi=...).nameWithOctave`)
so the frontend doesn't need MIDI-to-name logic of its own.

Errors: reuses whatever `realize()` already raises for an unrealizable
progression (e.g. a figure with no legal candidate voicings at all) --
surfaced the same way `/generate` surfaces it today (422), no new failure
mode.

`POST /generate` itself is unchanged -- it already accepts an explicit
`soprano: Optional[List[Optional[int]]]`, which is exactly how a chosen
alternative gets finalized into a full score.

### Frontend (`app/static/index.html`)

Clicking **Realize**:

1. `POST /generate/soprano-options` (cheap, no MusicXML).
2. Immediately finalize with option 1 via `POST /generate` -- today's exact
   flow (render OSMD, playback, download), unchanged.
3. Additionally render up to 3 small option cards below/alongside the
   result: each shows the pitch-name text (e.g. "C5 · C5 · B4 · C5") and a
   small ▶ button that plays just that soprano line through the existing
   Web Audio synth (reuses the playback code already used for the full
   realized score, just fed a shorter note list).
4. Clicking a non-selected card re-calls `POST /generate` with that card's
   `soprano` array and swaps the displayed score/playback/download in
   place. Locked RNs, key, and tempo are untouched.

If `/generate/soprano-options` returns fewer than 3 options (constrained
progression), the frontend just renders however many came back -- no
placeholder cards, no error state.

## Data flow

```
Propose → lock/edit RNs → click Realize
    → POST /generate/soprano-options   (3 previews, cheap)
    → POST /generate (soprano = option 1)   (today's flow, unchanged)
    → [user clicks a different preview card]
    → POST /generate (soprano = chosen option)   (re-finalize in place)
```

## Testing

- `soprano_alternatives`: option 1 is byte-for-byte the same as today's
  `_best_path` result on existing fixtures (no regression). A progression
  with genuine chord-tone choice at multiple beats produces ≥2 distinct
  soprano tuples. A maximally-constrained progression (e.g. a single triad
  repeated, where only one soprano chord-tone is ever legal at each beat)
  degrades gracefully to fewer than 3 options without erroring.
- API test for `/generate/soprano-options`: valid response shape, correct
  option count bound (`len(options) <= 3`), 422 on an unrealizable
  progression. Existing `/generate` tests are untouched -- no signature or
  behavior change there.
- Frontend: manual browser check (no JS test suite exists in this project;
  matches how the Generate tab's Q3 spice/style controls were verified).

## Alternatives considered

- **True k-best Viterbi** (extend the DP table to track the top-K
  cost/backpointer at every cell, reconstruct K distinct paths). More
  principled -- options would be *provably* the K lowest-cost distinct
  paths, not just "lowest cost among what pruning left available." Rejected
  for this iteration: real new algorithm to build and verify correctly
  against the existing single-best DP, versus candidate pruning's few lines
  reusing `_best_path` unchanged. Worth revisiting if pruned alternatives
  turn out to feel arbitrarily worse than a true 2nd/3rd-best.
- **Randomized sampling** (softmax over transition cost, sample N times,
  dedupe, keep best 3). Simplest code, but non-deterministic -- the same
  progression could return a different option set on different calls, and
  there's no guarantee of finding 3 distinct good options in a fixed sample
  budget. Rejected: determinism matters more here than implementation
  simplicity, and pruning is only marginally more code.
- **Return all 3 full realizations up front** (3x MusicXML + playback in
  one response). Simpler frontend (no second round-trip), but 3x the
  realization work and payload size for options the user will mostly not
  pick. Rejected in favor of lightweight-preview-then-finalize.
