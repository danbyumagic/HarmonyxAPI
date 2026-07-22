# Roman-numeral alternatives for a single slot (Generate tab)

## Problem

In the Generate tab's progression editor (`#rnGrid`, pre-Realize), a user who
wants to change one or two chords has to guess a valid replacement figure by
hand and re-type it, or lean on the fixer (`suggest_fixes`) which only
activates when the *whole* progression is already invalid. There's no way to
ask "what else could go here?" for a single slot on a progression that's
already valid. This is Roman-numeral logic only — no melody/voicing/soprano
involvement (that's the separate soprano-alternatives feature).

## Design

### Backend

New public function `roman_alternatives_for_slot()` in
`app/generation/fix.py`, next to the existing (private)
`_alternatives_for_slot`:

```python
def roman_alternatives_for_slot(
    progression: Sequence[str],
    key_like: _chords.KeyLike,
    index: int,
    *,
    locked: Optional[Mapping[int, str]] = None,
    cadence: Optional[str] = None,
    max_alternatives: int = 6,
) -> List[Dict[str, str]]:
```

Behavior:

1. If `index` is out of range, raise `ValueError` (endpoint maps this to 422).
2. If `index` is in `locked`, return `[]` — a locked slot has nothing to
   suggest.
3. Use the existing `_alternatives_for_slot(figures, index, key_like)` pool
   as a cheap first pass (it already excludes candidates that create a
   forbidden transition into/out of the immediate neighbors).
4. For each surviving candidate (skipping the slot's current figure), build
   the trial progression with that slot swapped in, and confirm the **whole**
   progression still passes `validate_progression(trial, key_like,
   cadence=cadence, locked=locked, check_engine=False, suggest=False).ok` —
   this covers cadence shape and all forbidden edges, not just the two
   adjacent to `index`. `check_engine=False` matches your call to keep this
   theory-only, matching `suggest_fixes`'s default cost profile.
5. Label each surviving candidate with the existing `_label_for_edit(index,
   old_figure, new_figure, key_like)` helper (already used by
   `suggest_fixes`, e.g. "IV → ii").
6. Cap at `max_alternatives` (default 6), preserving `_alternatives_for_slot`'s
   existing ranking order (textbook-pool order — no new ranking logic needed).

Return shape: `[{"figure": "ii", "label": "IV → ii"}, ...]`.

### API

New endpoint `POST /generate/roman-alternatives` in `app/main.py`, with a
small request/response pair in `app/models.py`:

```python
class RomanAlternativesRequest(BaseModel):
    progression: list[str]
    key: str
    index: int
    locked: dict[int, str] | None = None
    cadence: Literal["PAC", "HC"] | None = None

class RomanAlternative(BaseModel):
    figure: str
    label: str

class RomanAlternativesResponse(BaseModel):
    alternatives: list[RomanAlternative]
```

The endpoint validates `0 <= index < len(progression)` itself (422 with a
clear message if not — pydantic won't catch this since it's a cross-field
constraint) and otherwise passes straight through to
`roman_alternatives_for_slot`. No engine/realizer involvement, no new
algorithm — this is a thin read-only query over `fix.py`'s existing
candidate pools and `validate.py`'s existing theory gate.

### Frontend

`app/static/index.html`, in `renderSlots()`'s per-slot markup
(`.rn-slot`, currently index + `<input>` + a `lock` button): add a third
small button, `💡 alts`, next to the lock button. It is disabled when
`s.locked` is true (a locked figure has nothing to suggest — matches the
backend returning `[]` for locked slots, so this is a UX shortcut, not a new
rule).

Click handler for `💡 alts` on slot `i`:

1. `readSlotsFromDom()` (existing helper — picks up any in-progress typed
   edits across all slots before firing the request).
2. `POST /generate/roman-alternatives` with `{ progression: slots.map(s =>
   s.figure), key: genKey(), index: i, locked: lockedMapFromSlots(),
   cadence: genCadence() }`.
3. Open a small popover anchored under slot `i` listing the returned
   `{figure, label}` alternatives as clickable rows, or the text "No valid
   alternatives for this chord" if the list is empty.
4. Clicking an alternative row sets `slots[i].figure` to that figure, calls
   `renderSlots()` (same effect as manually typing + tabbing out), and closes
   the popover. This does **not** auto-Realize — matches how manual RN edits
   already behave; the user still clicks Realize when ready.

Closing the popover: clicking outside it, pressing Escape, or clicking a
different slot's `💡 alts` button (which replaces it with that slot's
popover instead of stacking).

### Error handling

- Out-of-range `index` → 422 from the endpoint (explicit check, not a
  pydantic-level constraint).
- Empty/malformed `progression` or unparseable `key` → existing
  `validate_progression`/`_chords` error paths already used elsewhere in the
  app (no new handling needed — this endpoint sits on the same validation
  stack as `/generate/soprano-options`).
- Frontend: a failed fetch shows a small inline error in the popover ("Could
  not load alternatives") rather than throwing — same pattern as the
  soprano-options fetch-failure handling already in this file.

## Non-goals

- No melody/soprano/voicing involvement — Roman-numeral logic only, per your
  request.
- No multi-slot joint suggestion in one request (rejected during
  brainstorming in favor of one-slot-at-a-time, repeatable for "one or two"
  chords).
- No auto-Realize after picking an alternative.
- No change to `suggest_fixes`'s existing whole-progression-invalid fixer
  path — this is a separate, additive read path over the same candidate
  pools.

## Testing

- Backend: `roman_alternatives_for_slot` on a known-valid progression
  (e.g. `["I", "IV", "V", "I"]`) returns a non-empty list of figures, none
  equal to the slot's current figure, and swapping any returned figure into
  that slot keeps `validate_progression(..., check_engine=False).ok` true.
- Backend: locked slot → `[]`.
- Backend: out-of-range `index` → `ValueError` (unit) / 422 (endpoint test).
- Backend: a slot where no swap keeps the progression valid (e.g. tightly
  cadence-constrained final chord) → `[]`, not an exception.
- Frontend: manual browser check (no JS test suite exists in this project) —
  click `💡 alts` on an unlocked slot, confirm popover shows alternatives,
  click one, confirm the slot updates and Realize still works afterward;
  confirm the button is disabled/no-op on a locked slot.
