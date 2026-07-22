# More soprano options (Generate tab)

## Problem

The Generate tab shows up to 3 soprano-line options after Realize
(`docs/superpowers/specs/2026-07-22-soprano-alternatives-design.md`). If none
of the 3 fit, there's no way to see more without re-proposing a whole new
progression. Users want a "More options" action that fetches additional
distinct soprano lines for the same progression.

## Design

### Backend

`soprano_alternatives()` (`app/generation/realize.py`) is already
deterministic: for the same progression/key, requesting a larger `n` always
reproduces the same first-N options as a prefix, then continues the search
for more. No algorithm change needed.

Add an optional `count: int = 3` field to `SopranoOptionsRequest`
(`app/models.py`), bounded `ge=1, le=10` (10 is a sane ceiling — well past
what the UI would ever show, just a guard against an unbounded value driving
unbounded `_best_path` re-runs). The endpoint
(`POST /generate/soprano-options`, `app/main.py`) passes it straight through:
`soprano_alternatives(body.progression, body.key, n=body.count)`.

This is a pure parameterization of an existing, already-tested code path —
no new endpoint, no change to `soprano_alternatives` itself.

### Frontend

A "More options" button/link below the soprano-options card row
(`app/static/index.html`). On click:

1. Re-fetch `POST /generate/soprano-options` with
   `count = sopranoOptions.length + 3`.
2. If the response has more options than before, replace `sopranoOptions`
   wholesale with the new list and re-render the cards (existing selection
   index stays valid -- indices 0..N-1 never change, only new ones get
   appended).
3. If the response is not longer than before (the search is exhausted),
   disable the "More options" button and show a small note: "No more
   distinct soprano lines for this progression."

The button re-enables (and the note clears) the next time a fresh Realize
happens (new progression -> `sopranoOptions` and any exhausted-state flag
both reset, matching how `realizeProgression()` already resets
`sopranoOptions` today).

## Non-goals

- Mixing/splicing measures from different options into one hybrid soprano
  line -- a separate, larger feature, explicitly deferred (see conversation
  history; this is the "manual per-note/per-measure soprano editing" idea
  already flagged as out of scope in the original soprano-alternatives spec).
- Any change to how many options are shown by default (still 3) or to the
  candidate-pruning algorithm itself.

## Testing

- Backend: a test that `count=6` on a progression with enough chord-tone
  variety returns more options than `count=3` did, and that the first 3
  entries of the `count=6` response equal the `count=3` response exactly
  (the determinism/prefix guarantee this whole feature depends on).
- Backend: `count` out of bounds (0, 11) returns a 422 (pydantic validation).
- Frontend: manual browser check (no JS test suite exists in this project).
