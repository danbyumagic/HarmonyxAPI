# Custom soprano melody editor (Generate tab)

## Problem

Harmonyx can already generate several complete soprano alternatives and can
realize alto, tenor, and bass beneath an explicit soprano MIDI array. The
Generate tab does not expose the second capability directly: a user may choose
one generated line, but cannot change individual soprano pitches.

The first version of melody customization should bridge that existing seam. It
should start from a generated, realizable soprano line; let the user replace one
pitch per Roman-numeral slot; and continue using the current SATB realizer as
the final authority.

## Goals

- Start editing from any generated soprano option.
- Present an inline note tile for every Roman-numeral slot.
- Offer every locally legal chord-tone pitch in the supported soprano range
  (`C4` through `G5`) for each tile.
- Let the user edit several pitches locally, preview the draft soprano alone,
  and explicitly apply the complete draft.
- Preserve the exact applied soprano pitches in the realized score and
  MusicXML.
- Keep a successful custom line alongside the generated alternatives so the
  user can switch back without losing it.
- Reconcile a saved draft safely after the key or progression changes.
- Eliminate the existing stale-soprano-card failure path by tying editor and
  option state to an exact key/progression snapshot.

## Non-goals

- Multiple soprano notes per chord, rests, ties, or custom rhythm.
- Non-chord tones, suspensions, passing tones, appoggiaturas, or chromatic
  melody notes.
- Dragging notation, piano-roll editing, piano-keyboard entry, or MIDI
  input/import.
- Persisting a custom melody across browser sessions.
- Editing alto, tenor, or bass.
- Relaxing any locked part-writing fixture or hard invariant.
- Guaranteeing that every combination of individually legal pitches has a
  complete SATB solution before the user clicks **Apply melody**.

## Product decisions

- One soprano note remains aligned with one Roman-numeral chord.
- Editing begins only after an initial realization, using the selected
  generated soprano as the starting line.
- The chosen layout is inline note tiles, not dropdown rows or a notation
  staff.
- Each tile offers all legal pitches across the full soprano range, not only
  nearby pitches.
- Edits are batched. Changing a tile does not re-realize the SATB score.
- **Preview melody** plays the local soprano draft through the existing Web
  Audio preview path.
- **Apply melody** performs full validation and realization.
- **Reset** restores the generated option from which the current edit session
  began.
- The first version enforces chord-tone legality. There is no warning-only
  non-chord-tone mode.

## User experience

### Entry point

After a successful realization, the selected generated soprano option displays
a **Customize melody** action. Activating it opens an editor directly above the
score. The current option becomes both the initial draft and the Reset target.
The editor stays open after a successful Apply so the same Custom line can be
revised and applied again without creating another card.

The editor does not open until its legal-pitch data has loaded successfully.
The existing score remains visible and usable during loading or if loading
fails.

### Inline note tiles

There is one tile per progression slot. Each tile displays:

- the one-based slot number;
- the Roman numeral;
- the selected pitch name;
- an expanded list of every legal pitch name for that slot; and
- an accessible selected state.

Pitch choices are buttons or equivalent keyboard-operable controls, not a
free-form text field. The UI never offers an out-of-range pitch or a pitch that
has no locally valid SATB voicing for the current chord.

Long progressions wrap or scroll without changing the one-to-one visual
alignment between Roman numerals and note tiles. The editor must remain usable
at the Generate tab's existing mobile breakpoint.

### Editor actions

- **Preview melody** calls the existing soprano-only Web Audio preview with the
  current draft. It does not call the backend or mutate the displayed score.
- **Apply melody** submits the complete draft to the existing `POST /generate`
  endpoint. The button is disabled while that request is in flight.
- **Reset** restores the edit session's starting generated option and clears
  any automatic-replacement markers.

### Successful application

On success:

1. Replace the displayed score, full playback payload, and MusicXML download
   with the response from `POST /generate`.
2. Store the applied draft separately from the generated options.
3. Render it as the selected **Custom** soprano card alongside the generated
   cards.
4. Keep **More options** behavior based only on the generated-option count;
   fetching more generated options must not discard or duplicate the Custom
   card.
5. Use a stable selection identity such as `custom` or `generated:<index>`
   instead of making Custom participate in the backend option index.

Applying again updates the single Custom card rather than creating multiple
Custom cards.

## Backend design

### Pure generation helper

Add a FastAPI-independent helper near the realizer/voicing code:

```python
def soprano_pitch_choices(
    progression: list[str],
    key_like: _chords.KeyLike,
) -> list[list[int]]:
    """Distinct locally legal soprano MIDI pitches for each RN slot."""
```

For every Roman numeral:

1. Call the existing `candidate_voicings(figure, key_like)` with no fixed
   soprano.
2. Collect each candidate's `s` value.
3. Deduplicate and sort the MIDI pitches from low to high.
4. Raise `RealizationError` with the slot index and figure if the candidate pool
   is empty.

Using `candidate_voicings` rather than raw chord pitch classes makes the engine
the single source of truth. A returned pitch is a chord tone, lies within the
locked `C4`–`G5` soprano range, and participates in at least one statically
legal voicing for that chord. This is local legality only; transition rules
across the complete progression remain the responsibility of `realize()`.

The helper must not import FastAPI and must not alter candidate generation,
transition costs, or part-writing rules.

### API models

Add focused request/response models:

```python
class SopranoChoicesRequest(BaseModel):
    key: str
    progression: list[str]  # at least one non-empty figure

class SopranoPitchChoice(BaseModel):
    midi: int
    pitch: str

class SopranoSlotChoices(BaseModel):
    index: int
    roman: str
    choices: list[SopranoPitchChoice]

class SopranoChoicesResponse(BaseModel):
    slots: list[SopranoSlotChoices]
```

Progression validation should follow the existing generation request models;
it must not introduce a conflicting Roman-numeral contract.

### Endpoint

Add:

```http
POST /generate/soprano-choices
```

Request:

```json
{
  "key": "C major",
  "progression": ["I", "IV", "V", "I"]
}
```

Response:

```json
{
  "slots": [
    {
      "index": 0,
      "roman": "I",
      "choices": [
        {"midi": 60, "pitch": "C4"},
        {"midi": 64, "pitch": "E4"},
        {"midi": 67, "pitch": "G4"},
        {"midi": 72, "pitch": "C5"},
        {"midi": 76, "pitch": "E5"},
        {"midi": 79, "pitch": "G5"}
      ]
    }
  ]
}
```

Convert MIDI values to display names with the existing `midi_to_name` helper.
Malformed keys, figures, or empty candidate pools return structured `422`
responses following the existing generation endpoints' error style.

The existing `POST /generate` request and response contracts remain unchanged.
It continues to validate chord membership and perform the complete
hard-invariant-clean DP realization.

## Frontend state and data flow

Keep generated and custom state separate:

- generated soprano options from `POST /generate/soprano-options`;
- a single optional custom soprano array;
- the editor's starting array;
- the current draft array;
- legal choice slots;
- automatic-replacement indices; and
- an exact snapshot of the key and unfiltered progression array.

The snapshot should be derived consistently from normalized key and progression
values. Each asynchronous request captures its snapshot. A response is ignored
if the current snapshot no longer matches.

### Initial flow

```text
Propose/edit RNs
  -> Realize
  -> POST /generate/soprano-options
  -> POST /generate with generated option 1
  -> select any generated soprano card
  -> Customize melody
  -> POST /generate/soprano-choices (lazy)
  -> edit draft locally
  -> Preview melody (local Web Audio)
  -> Apply melody
  -> POST /generate with draft soprano
  -> render score and selected Custom card
```

The choices response may be cached only for its exact snapshot.

### Key or progression changes

Any key or RN edit marks the rendered result and all soprano-card actions as
stale. Old cards must not be allowed to call `POST /generate` against the new
progression.

On the next explicit **Realize**:

1. Fetch fresh generated options and render the fresh default score using the
   existing flow.
2. If a prior custom draft exists, fetch fresh legal choices for reconciliation
   during this flow. If there is no custom draft, continue to fetch choices
   lazily only when Customize opens.
3. If a prior custom draft exists, reconcile it by index:
   - keep an overlapping pitch when its MIDI value appears in the fresh slot's
     choices;
   - use the fresh default soprano pitch when the old pitch is no longer legal;
   - append fresh default pitches for newly added slots; and
   - discard pitches for removed slots.
4. Record every substituted or appended index for an “updated for new chord”
   marker.
5. Preserve the reconciled line as an unapplied draft. Do not silently replace
   the newly rendered default score; the user must open Customize and click
   **Apply melody** again.

This preserves safe work while retaining the explicitly approved batch-Apply
behavior.

## Validation and error behavior

### Choice loading failure

- Do not open a half-populated editor.
- Leave the last successfully rendered score and playback intact.
- Show the endpoint's readable error through the existing Generate status
  surface.
- Allow the user to retry Customize.

### Apply failure

Individually legal pitches can still form a line for which no complete legal
SATB path exists. If `POST /generate` rejects the draft:

- keep the editor open;
- preserve every draft pitch;
- retain the last successful score, playback, download, and Custom card;
- show that the complete melody could not be harmonized under the current
  part-writing rules; and
- allow further editing, preview, Reset, and retry.

The first version does not attempt to identify a single “bad” note when the
failure is caused by a transition or combination of notes.

### Stale responses

Ignore any choices, options, or realization response whose captured snapshot
does not match the current key and progression. A stale response must not
overwrite editor state, selection state, score output, or status for a newer
request.

## Testing

### Pure helper tests

- Empty progression raises `RealizationError`.
- Major and minor triads return deduplicated, ascending MIDI pitches with the
  expected chord-tone pitch classes.
- Inversions and seventh chords return the correct legal soprano members.
- Every returned pitch lies within `C4`–`G5`.
- Passing each returned pitch back to `candidate_voicings(..., soprano=pitch)`
  yields at least one candidate.
- A figure with no candidate pool reports the correct index and Roman numeral.

### API tests

- Valid request returns one ordered slot per progression figure.
- Each slot echoes its zero-based index and Roman numeral.
- MIDI values and `midi_to_name` display names agree.
- Empty progression fails model validation.
- Malformed key/Roman numeral and empty-candidate failures return structured
  `422` responses.
- Existing `/generate/soprano-options` and `/generate` behavior remains
  unchanged.

### Realization regression

- Apply a legal custom soprano array through `POST /generate`.
- Parse the resulting MusicXML/score and verify the soprano voice contains the
  exact requested MIDI pitches in order.
- Keep all existing part-writing and generation tests passing.
- Do not edit `tests/test_partwriting.py`.

### Frontend verification

- Run JavaScript syntax validation.
- Perform a real-browser walkthrough:
  1. Propose and realize a progression.
  2. Select a generated soprano and open Customize.
  3. Confirm each tile offers only the endpoint's legal pitches.
  4. Change multiple notes.
  5. Preview and confirm the displayed score does not change.
  6. Apply and confirm the score, full playback, MusicXML soprano, and selected
     Custom card all update.
  7. Apply a second edit and confirm the existing Custom card updates rather
     than duplicates.
  8. Fetch More options and confirm the Custom card survives.
  9. Reset and confirm the starting generated line returns.
  10. Change an RN, confirm stale cards cannot apply, Realize again, and verify
      legal notes are preserved while illegal notes are replaced and marked.
  11. Exercise an Apply failure and confirm the draft and last successful score
      remain intact.

## Acceptance criteria

The feature is complete when:

- a user can start from a generated soprano, change multiple individual pitches
  using inline legal-choice tiles, preview the draft, and explicitly apply it;
- the exported score preserves the selected soprano exactly;
- the successful line remains available as one Custom option alongside
  generated alternatives;
- key/RN changes cannot apply stale soprano arrays and reconcile prior custom
  work as specified;
- failure paths preserve both the draft and the last successful score;
- locked part-writing fixtures are unchanged;
- the full automated suite passes; and
- the browser walkthrough succeeds in a real browser.
