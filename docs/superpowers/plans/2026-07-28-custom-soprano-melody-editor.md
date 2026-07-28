# Custom Soprano Melody Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user start from any generated soprano option, edit one legal
pitch per Roman-numeral slot, preview the draft, and explicitly realize the
complete custom line while preserving safe work across failures and
key/progression changes.

**Architecture:** Add a FastAPI-independent
`soprano_pitch_choices()` helper that projects every statically legal soprano
pitch from the existing SATB candidate engine, then expose those pitches
through `POST /generate/soprano-choices`. Keep deterministic snapshot and
reconciliation helpers in a small browser/Node-compatible JavaScript module;
leave DOM and Web Audio integration in the existing Generate-tab script.
Generated options and the single Custom option remain separate, and all
asynchronous state commits require both an exact key/progression snapshot and a
latest-request token.

**Tech Stack:** Python 3.12, music21, FastAPI, Pydantic v2, vanilla browser
JavaScript, Web Audio, OpenSheetMusicDisplay, pytest,
`fastapi.testclient.TestClient`, and Node's built-in `node:test`.

## Global Constraints

- The approved design is
  `docs/superpowers/specs/2026-07-28-custom-soprano-melody-editor-design.md`;
  implementation must not broaden its v1 scope.
- V1 accepts exactly one complete soprano MIDI pitch per Roman-numeral slot;
  there are no rests, custom rhythms, non-chord tones, warning-only notes, or
  edits to alto/tenor/bass.
- Legal choices come only from `candidate_voicings()` and must remain inside
  the locked soprano range `C4`–`G5` (`60..79` inclusive).
- Choice generation proves local/static legality only. `POST /generate` and
  `realize()` remain the authority for whole-line transition legality.
- `POST /generate` and `POST /generate/soprano-options` contracts remain
  unchanged.
- The exact snapshot is the normalized key plus the complete, unfiltered
  progression array. Never use `.filter(Boolean)` on a progression that is
  paired with soprano indices; reject blank slots instead.
- Snapshot equality prevents cross-progression writes; a monotonically
  increasing token per request kind prevents older same-snapshot requests from
  winning a race.
- A failed or stale request must not overwrite the last successful score,
  playback payload, MusicXML download, selected card, Custom card, or editor
  draft.
- The Custom card has stable identity `custom`; generated cards use
  `generated:<zero-based-index>`. Custom never participates in the backend
  option count.
- `tests/test_partwriting.py` is locked. Do not edit it.
- Add no frontend package manager or third-party JavaScript dependency.
- Preserve the named stash
  `codex: preserve pre-cleanup work 2026-07-28`; do not drop, pop, or overwrite
  it. It contains a separate MuseScore voice-numbering fix and preserved
  pre-cleanup files. That fix is not part of this feature plan.

## File Map

- Modify `app/generation/realize.py`: add the pure local-choice projection.
- Modify `tests/test_generation_realize.py`: lock the helper's engine-derived
  legality contract.
- Modify `app/models.py`: add focused soprano-choice request/response models.
- Modify `app/main.py`: add `POST /generate/soprano-choices`.
- Modify `tests/test_generate_endpoint.py`: cover the route, structured errors,
  and exact custom-soprano MusicXML round-trip.
- Create `app/static/soprano-editor.js`: pure snapshot, choice-validation,
  pitch-label, and reconciliation helpers usable by both browser and Node.
- Create `tests/test_soprano_editor.js`: Node unit tests for those pure helpers.
- Create `tests/test_static_generate_ui.py`: dependency-free structural
  regression checks for the inline Generate UI.
- Modify `app/static/index.html`: load the helper module and implement
  snapshot-safe cards, inline tiles, preview, Reset, Apply, Custom, staleness,
  and reconciliation.

---

### Task 1: Engine — project every locally legal soprano pitch

**Files:**
- Modify: `app/generation/realize.py:120` (insert immediately before
  `soprano_alternatives`)
- Modify: `tests/test_generation_realize.py:13-21,135` (import the helper and
  add a dedicated section before the soprano-alternatives tests)

**Interfaces:**
- Consumes: `candidate_voicings(figure, key_like, soprano=None, limit=None) ->
  list[Voicing]` from `app/generation/voicing.py`.
- Produces: `soprano_pitch_choices(progression: list[str],
  key_like: _chords.KeyLike) -> list[list[int]]`.
- Raises: `RealizationError("progression must not be empty")` for `[]`, or
  `RealizationError("no legal voicings for chord <index> ('<figure>')")` when
  one slot has no static candidate.
- Consumed by: Task 2's endpoint.

- [ ] **Step 1: Write the failing helper tests**

In `tests/test_generation_realize.py`, add `soprano_pitch_choices` to the
existing import from `app.generation.realize`, change the voicing import to
`from app.generation.voicing import S_RANGE, Voicing, candidate_voicings`, and
insert:

```python
# --- soprano_pitch_choices ----------------------------------------------


def test_soprano_pitch_choices_empty_progression_raises():
    with pytest.raises(RealizationError, match="progression must not be empty"):
        soprano_pitch_choices([], KEY)


def test_soprano_pitch_choices_major_and_minor_triads_are_sorted_and_distinct():
    assert soprano_pitch_choices(["I"], "C major") == [
        [60, 64, 67, 72, 76, 79]
    ]
    assert soprano_pitch_choices(["i"], "A minor") == [
        [60, 64, 69, 72, 76]
    ]


def test_soprano_pitch_choices_inversion_and_seventh_match_static_candidates():
    assert soprano_pitch_choices(["V6", "V7"], KEY) == [
        [62, 67, 74, 79],
        [62, 65, 71, 74, 77],
    ]


def test_soprano_pitch_choices_stay_in_range_and_round_trip_to_candidates():
    progression = ["I", "IV", "V7", "I6"]
    choices = soprano_pitch_choices(progression, KEY)

    assert len(choices) == len(progression)
    for figure, pitches in zip(progression, choices):
        assert pitches == sorted(set(pitches))
        assert all(S_RANGE[0] <= pitch <= S_RANGE[1] for pitch in pitches)
        for pitch in pitches:
            assert candidate_voicings(figure, KEY, soprano=pitch)


def test_soprano_pitch_choices_reports_empty_pool_index_and_figure(monkeypatch):
    def fake_candidate_voicings(figure, key_like, *, soprano=None, limit=200):
        if figure == "I":
            return [Voicing(60, 60, 55, 48)]
        return []

    monkeypatch.setattr(
        "app.generation.realize.candidate_voicings",
        fake_candidate_voicings,
    )

    with pytest.raises(
        RealizationError,
        match=r"no legal voicings for chord 1 \('V'\)",
    ):
        soprano_pitch_choices(["I", "V"], KEY)
```

- [ ] **Step 2: Run the focused tests and verify the expected failure**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/test_generation_realize.py -k soprano_pitch_choices -v
```

Expected: collection fails because
`app.generation.realize.soprano_pitch_choices` does not exist.

- [ ] **Step 3: Add the minimal pure helper**

Insert in `app/generation/realize.py` immediately before
`soprano_alternatives`:

```python
def soprano_pitch_choices(
    progression: list[str],
    key_like: _chords.KeyLike,
) -> list[list[int]]:
    """Distinct locally legal soprano MIDI pitches for each RN slot.

    Choices are projected from complete static-rule-legal SATB candidates.
    Passing ``limit=None`` is intentional: the public contract promises every
    legal soprano pitch, so a future growth in the voicing pool must not let
    the candidate function's default count cap hide a pitch.
    """
    if not progression:
        raise RealizationError("progression must not be empty")

    out: list[list[int]] = []
    for i, figure in enumerate(progression):
        pool = candidate_voicings(figure, key_like, limit=None)
        if not pool:
            raise RealizationError(
                f"no legal voicings for chord {i} ('{figure}')"
            )
        out.append(sorted({voicing.s for voicing in pool}))
    return out
```

- [ ] **Step 4: Run the focused tests**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/test_generation_realize.py -k soprano_pitch_choices -v
```

Expected: all five new helper tests pass.

- [ ] **Step 5: Run the complete realization and voicing test files**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/test_generation_realize.py tests/test_generation_voicing.py -v
```

Expected: exit code 0; existing realization, alternative, and candidate
behavior remains green.

- [ ] **Step 6: Commit the engine slice**

```bash
git add app/generation/realize.py tests/test_generation_realize.py
git commit -m "Add legal soprano pitch choices helper"
```

---

### Task 2: API — expose legal choices without changing realization

**Files:**
- Modify: `app/models.py:170-224` (add models after
  `SopranoOptionsResponse`)
- Modify: `app/main.py:23-45,215-247` (imports and route beside the existing
  soprano-options route)
- Modify: `tests/test_generate_endpoint.py:1-10,37-48,178` (imports,
  MusicXML regression, and new endpoint section)

**Interfaces:**
- Consumes: `soprano_pitch_choices()` from Task 1 and existing
  `midi_to_name()`.
- Produces: `POST /generate/soprano-choices`.
- Request: `SopranoChoicesRequest(key: str, progression: List[str])`.
- Response: `SopranoChoicesResponse(slots: List[SopranoSlotChoices])`, where
  each slot has zero-based `index`, echoed `roman`, and ascending
  `choices: List[SopranoPitchChoice]`.
- Error contract: malformed key/RN or an empty candidate pool returns HTTP 422
  with `detail.error == "realization_failed"` and a readable `message`;
  Pydantic handles empty/blank progression input with its normal HTTP 422
  validation list.
- Leaves unchanged: `GenerateRequest`, `GenerateResponse`,
  `SopranoOptionsRequest`, and `SopranoOptionsResponse`.

- [ ] **Step 1: Write failing route and round-trip tests**

At the top of `tests/test_generate_endpoint.py`, add:

```python
import pytest
from music21 import converter as m21converter

from app.generation.chords import midi_to_name
from app.generation.realize import RealizationError, satb_voicings_from_score
```

Add this regression immediately after
`test_generate_with_compatible_soprano_returns_200`:

```python
def test_generate_custom_soprano_survives_musicxml_round_trip():
    requested = [72, 71, 72]
    resp = client.post(
        "/generate",
        json={
            "key": "C major",
            "progression": ["I", "V", "I"],
            "soprano": requested,
        },
    )

    assert resp.status_code == 200, resp.text
    score = m21converter.parseData(
        resp.json()["musicxml"],
        format="musicxml",
    )
    assert [v.s for v in satb_voicings_from_score(score)] == requested
```

Add a new endpoint section after the existing soprano-options tests and before
the Roman-alternatives tests:

```python
# --- POST /generate/soprano-choices -----------------------------------


def test_soprano_choices_returns_ordered_slots_and_legal_midis():
    progression = ["I", "V7", "I6"]
    resp = client.post(
        "/generate/soprano-choices",
        json={"key": "C major", "progression": progression},
    )

    assert resp.status_code == 200, resp.text
    slots = resp.json()["slots"]
    assert [slot["index"] for slot in slots] == [0, 1, 2]
    assert [slot["roman"] for slot in slots] == progression
    assert [choice["midi"] for choice in slots[0]["choices"]] == [
        60,
        64,
        67,
        72,
        76,
        79,
    ]
    for slot in slots:
        midis = [choice["midi"] for choice in slot["choices"]]
        assert midis == sorted(set(midis))
        assert all(60 <= midi <= 79 for midi in midis)
        assert [choice["pitch"] for choice in slot["choices"]] == [
            midi_to_name(midi) for midi in midis
        ]


@pytest.mark.parametrize("progression", [[], ["I", " "]])
def test_soprano_choices_rejects_empty_or_blank_progression(progression):
    resp = client.post(
        "/generate/soprano-choices",
        json={"key": "C major", "progression": progression},
    )

    assert resp.status_code == 422, resp.text
    assert isinstance(resp.json()["detail"], list)


@pytest.mark.parametrize(
    "payload",
    [
        {"key": "", "progression": ["I"]},
        {"key": "C major", "progression": ["not-a-roman"]},
    ],
)
def test_soprano_choices_malformed_key_or_roman_is_structured_422(payload):
    resp = client.post("/generate/soprano-choices", json=payload)

    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "realization_failed"
    assert detail["message"]


def test_soprano_choices_empty_candidate_pool_is_structured_422(monkeypatch):
    def fail_choices(progression, key_like):
        raise RealizationError("no legal voicings for chord 1 ('V')")

    monkeypatch.setattr("app.main.soprano_pitch_choices", fail_choices)
    resp = client.post(
        "/generate/soprano-choices",
        json={"key": "C major", "progression": ["I", "V"]},
    )

    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == {
        "error": "realization_failed",
        "message": "no legal voicings for chord 1 ('V')",
    }
```

- [ ] **Step 2: Run the endpoint subset and verify the expected failure**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/test_generate_endpoint.py \
  -k "soprano_choices or custom_soprano_survives" -v
```

Expected: the MusicXML regression passes and each soprano-choices request gets
404 because the route is not defined.

- [ ] **Step 3: Add the four focused Pydantic models**

Insert after `SopranoOptionsResponse` in `app/models.py`:

```python
class SopranoChoicesRequest(BaseModel):
    """Body for ``POST /generate/soprano-choices``."""

    key: str = Field(
        ...,
        description="Key, e.g. 'C major' or 'A minor'.",
        examples=["C major"],
    )
    progression: List[str] = Field(
        ...,
        min_length=1,
        description="Roman-numeral figures in order, e.g. ['I', 'IV', 'V', 'I'].",
    )

    @field_validator("progression")
    @classmethod
    def _figures_nonempty(cls, value: List[str]) -> List[str]:
        if any(not (figure and str(figure).strip()) for figure in value):
            raise ValueError("progression figures must be non-empty strings")
        return value


class SopranoPitchChoice(BaseModel):
    midi: int
    pitch: str


class SopranoSlotChoices(BaseModel):
    index: int
    roman: str
    choices: List[SopranoPitchChoice]


class SopranoChoicesResponse(BaseModel):
    slots: List[SopranoSlotChoices]
```

- [ ] **Step 4: Add the route**

Add `soprano_pitch_choices` to the import from
`.generation.realize`. Add these model imports from `.models`:

```python
    SopranoChoicesRequest,
    SopranoChoicesResponse,
```

Insert the route after `generate_soprano_options` and before
`generate_roman_alternatives`:

```python
@app.post(
    "/generate/soprano-choices",
    response_model=SopranoChoicesResponse,
    tags=["generation"],
)
async def generate_soprano_choices(
    body: SopranoChoicesRequest,
) -> SopranoChoicesResponse:
    """Every locally legal soprano pitch for each progression slot."""
    try:
        pitch_lists = soprano_pitch_choices(body.progression, body.key)
    except RealizationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "realization_failed", "message": str(exc)},
        ) from exc
    except Exception as exc:  # music21 key / Roman-numeral parse failures
        raise HTTPException(
            status_code=422,
            detail={"error": "realization_failed", "message": str(exc)},
        ) from exc

    return SopranoChoicesResponse(
        slots=[
            {
                "index": index,
                "roman": figure,
                "choices": [
                    {"midi": midi, "pitch": midi_to_name(midi)}
                    for midi in pitches
                ],
            }
            for index, (figure, pitches) in enumerate(
                zip(body.progression, pitch_lists)
            )
        ]
    )
```

- [ ] **Step 5: Run focused and neighboring endpoint tests**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/test_generate_endpoint.py \
  -k "generate or soprano" -v
```

Expected: exit code 0. This includes the unchanged `/generate` and
`/generate/soprano-options` coverage as well as the new route.

- [ ] **Step 6: Commit the API slice**

```bash
git add app/models.py app/main.py tests/test_generate_endpoint.py
git commit -m "Add soprano pitch choices endpoint"
```

---

### Task 3: Frontend core — make snapshots and reconciliation testable

**Files:**
- Create: `app/static/soprano-editor.js`
- Create: `tests/test_soprano_editor.js`

**Interfaces:**
- Produces browser global and CommonJS export
  `HarmonyxSopranoEditor`.
- Produces:
  - `makeGenerationSnapshot(key, progression) -> string`
  - `snapshotMatches(snapshot, key, progression) -> boolean`
  - `choiceSlotsMatchProgression(slots, progression) -> boolean`
  - `reconcileSopranoDraft(previousDraft, slots, defaultSoprano) ->
    {draft: number[], updatedIndices: number[]}`
  - `pitchNamesForLine(line, slots) -> string[]`
  - `sameMidiLine(left, right) -> boolean`
- Consumed by: Tasks 4–6's inline browser integration.

- [ ] **Step 1: Write the failing Node unit tests**

Create `tests/test_soprano_editor.js`:

```javascript
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  makeGenerationSnapshot,
  snapshotMatches,
  choiceSlotsMatchProgression,
  reconcileSopranoDraft,
  pitchNamesForLine,
  sameMidiLine,
} = require('../app/static/soprano-editor.js');

const slots = [
  {
    index: 0,
    roman: 'I',
    choices: [
      { midi: 60, pitch: 'C4' },
      { midi: 64, pitch: 'E4' },
    ],
  },
  {
    index: 1,
    roman: 'V',
    choices: [
      { midi: 62, pitch: 'D4' },
      { midi: 67, pitch: 'G4' },
    ],
  },
  {
    index: 2,
    roman: 'I',
    choices: [{ midi: 67, pitch: 'G4' }],
  },
  {
    index: 3,
    roman: 'I6',
    choices: [{ midi: 72, pitch: 'C5' }],
  },
];

test('snapshot normalizes whitespace without dropping blank slots', () => {
  const snapshot = makeGenerationSnapshot(
    '  C   major ',
    [' I ', ' ', ' V '],
  );

  assert.equal(
    snapshot,
    JSON.stringify({
      key: 'C major',
      progression: ['I', '', 'V'],
    }),
  );
  assert.equal(
    snapshotMatches(snapshot, 'C major', ['I', '', 'V']),
    true,
  );
  assert.equal(
    snapshotMatches(snapshot, 'C major', ['I', 'V']),
    false,
  );
});

test('choice slots must preserve exact index and Roman alignment', () => {
  assert.equal(
    choiceSlotsMatchProgression(slots, ['I', 'V', 'I', 'I6']),
    true,
  );
  assert.equal(
    choiceSlotsMatchProgression(slots, ['I', 'IV', 'I', 'I6']),
    false,
  );
  assert.equal(
    choiceSlotsMatchProgression(slots.slice(0, 3), ['I', 'V', 'I', 'I6']),
    false,
  );
});

test('reconciliation preserves legal notes and replaces invalid or new slots', () => {
  const result = reconcileSopranoDraft(
    [64, 64, 67],
    slots,
    [60, 62, 67, 72],
  );

  assert.deepEqual(result.draft, [64, 62, 67, 72]);
  assert.deepEqual(result.updatedIndices, [1, 3]);
});

test('reconciliation discards removed slots', () => {
  const result = reconcileSopranoDraft(
    [64, 62, 67, 72],
    slots.slice(0, 2),
    [60, 62],
  );

  assert.deepEqual(result.draft, [64, 62]);
  assert.deepEqual(result.updatedIndices, []);
});

test('reconciliation rejects a default pitch not present in legal choices', () => {
  assert.throws(
    () => reconcileSopranoDraft([64], slots.slice(0, 1), [61]),
    /default soprano pitch 61 is not legal for slot 0/,
  );
});

test('pitch labels and exact MIDI-line equality are deterministic', () => {
  assert.deepEqual(
    pitchNamesForLine([64, 62, 67, 72], slots),
    ['E4', 'D4', 'G4', 'C5'],
  );
  assert.equal(sameMidiLine([64, 62], [64, 62]), true);
  assert.equal(sameMidiLine([64, 62], [64, 67]), false);
  assert.equal(sameMidiLine([64, 62], [64]), false);
});
```

- [ ] **Step 2: Run the Node tests and verify the expected failure**

Run:

```bash
node --test tests/test_soprano_editor.js
```

Expected: FAIL with `MODULE_NOT_FOUND` for
`app/static/soprano-editor.js`.

- [ ] **Step 3: Implement the dependency-free helper module**

Create `app/static/soprano-editor.js`:

```javascript
(function exposeSopranoEditor(root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.HarmonyxSopranoEditor = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function buildApi() {
  'use strict';

  function normalizeKey(key) {
    return String(key == null ? '' : key).trim().replace(/\s+/g, ' ');
  }

  function normalizeProgression(progression) {
    if (!Array.isArray(progression)) return [];
    return progression.map((figure) =>
      String(figure == null ? '' : figure).trim());
  }

  function makeGenerationSnapshot(key, progression) {
    return JSON.stringify({
      key: normalizeKey(key),
      progression: normalizeProgression(progression),
    });
  }

  function snapshotMatches(snapshot, key, progression) {
    return snapshot === makeGenerationSnapshot(key, progression);
  }

  function choiceSlotsMatchProgression(slots, progression) {
    const figures = normalizeProgression(progression);
    if (!Array.isArray(slots) || slots.length !== figures.length) return false;
    return slots.every((slot, index) =>
      slot
      && slot.index === index
      && String(slot.roman).trim() === figures[index]
      && Array.isArray(slot.choices)
      && slot.choices.length > 0);
  }

  function reconcileSopranoDraft(previousDraft, slots, defaultSoprano) {
    if (!Array.isArray(slots) || !Array.isArray(defaultSoprano)
        || slots.length !== defaultSoprano.length) {
      throw new Error('choice slots and default soprano must have equal length');
    }

    const previous = Array.isArray(previousDraft) ? previousDraft : [];
    const draft = [];
    const updatedIndices = [];

    slots.forEach((slot, index) => {
      const legal = new Set(
        (slot.choices || []).map((choice) => Number(choice.midi)),
      );
      const fallback = defaultSoprano[index];
      if (!legal.has(fallback)) {
        throw new Error(
          `default soprano pitch ${fallback} is not legal for slot ${index}`,
        );
      }
      if (index < previous.length && legal.has(previous[index])) {
        draft.push(previous[index]);
      } else {
        draft.push(fallback);
        updatedIndices.push(index);
      }
    });

    return { draft, updatedIndices };
  }

  function pitchNamesForLine(line, slots) {
    if (!Array.isArray(line) || !Array.isArray(slots)
        || line.length !== slots.length) {
      throw new Error('soprano line and choice slots must have equal length');
    }
    return line.map((midi, index) => {
      const match = (slots[index].choices || []).find(
        (choice) => Number(choice.midi) === midi,
      );
      if (!match) {
        throw new Error(`pitch ${midi} is not legal for slot ${index}`);
      }
      return match.pitch;
    });
  }

  function sameMidiLine(left, right) {
    return Array.isArray(left)
      && Array.isArray(right)
      && left.length === right.length
      && left.every((midi, index) => midi === right[index]);
  }

  return {
    makeGenerationSnapshot,
    snapshotMatches,
    choiceSlotsMatchProgression,
    reconcileSopranoDraft,
    pitchNamesForLine,
    sameMidiLine,
  };
}));
```

- [ ] **Step 4: Run unit and syntax checks**

Run:

```bash
node --test tests/test_soprano_editor.js
node --check app/static/soprano-editor.js
```

Expected: both commands exit 0.

- [ ] **Step 5: Commit the pure frontend core**

```bash
git add app/static/soprano-editor.js tests/test_soprano_editor.js
git commit -m "Add tested soprano editor state helpers"
```

---

### Task 4: Frontend foundation — snapshot-safe cards and realization

**Files:**
- Create: `tests/test_static_generate_ui.py`
- Modify: `app/static/index.html:262-276,472,589-1008`

**Interfaces:**
- Consumes: `window.HarmonyxSopranoEditor.makeGenerationSnapshot()` from
  Task 3.
- Produces state:
  - `sopranoOptions` and `sopranoOptionsSnapshot`
  - `selectedSopranoId: null | "custom" | "generated:<index>"`
  - `customSoprano: null | {soprano: number[], pitches: string[],
    snapshot: string}`
  - `renderedSnapshot`, `renderedKey`, `renderedProgression`
  - `generatedResultStale`
  - request serials for `proposal`, `options`, `choices`, and `realization`
- Produces:
  - `requestSopranoOptions({key, progression, count, snapshot})`
  - `finalizeRealization(soprano, context) -> Promise<boolean>`
  - `renderGenerationResult(data, progression)`
  - stable, keyboard-operable generated/Custom cards.
- Consumed by: Tasks 5–6.

- [ ] **Step 1: Add failing structural regression tests**

Create `tests/test_static_generate_ui.py`:

```python
from pathlib import Path


INDEX = Path(__file__).parents[1] / "app" / "static" / "index.html"


def _html() -> str:
    return INDEX.read_text(encoding="utf-8")


def _generate_script() -> str:
    html = _html()
    return html[html.index("// ---- Generate ----") :]


def test_generate_ui_loads_soprano_helpers_before_inline_script():
    html = _html()
    helper = html.index('<script src="/static/soprano-editor.js"></script>')
    inline = html.index("<script>", helper)
    assert helper < inline


def test_generate_ui_uses_stable_selection_and_stale_hooks():
    script = _generate_script()
    assert "selectedSopranoId" in script
    assert "generated:${i}" in script
    assert "selectedSopranoIndex" not in script
    assert "$('genKey').addEventListener('change', markGeneratedResultStale)" in script
    assert "rnGrid.addEventListener('input', markGeneratedResultStale)" in script
    assert "requestIsCurrent" in script
```

- [ ] **Step 2: Run the structural tests and verify the expected failure**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/test_static_generate_ui.py -v
```

Expected: both tests fail because the helper script and stable snapshot state
are not integrated yet.

- [ ] **Step 3: Load the tested helper and replace numeric selection state**

Immediately before the existing inline `<script>` tag, add:

```html
  <script src="/static/soprano-editor.js"></script>
```

At the beginning of the Generate section, replace the soprano state declarations
with:

```javascript
    const SopranoEditor = window.HarmonyxSopranoEditor;
    /** @type {{ figure: string, locked: boolean }[]} */
    let slots = [];
    let lastMusicXml = null;
    let lastPlayback = null;
    /** @type {{ soprano: number[], pitches: string[] }[]} */
    let sopranoOptions = [];
    let sopranoOptionsSnapshot = null;
    let selectedSopranoId = null;
    let customSoprano = null;
    let renderedSnapshot = null;
    let renderedKey = null;
    let renderedProgression = [];
    let generatedResultStale = false;
    let sopranoOptionsExhausted = false;
    const requestSerial = {
      proposal: 0,
      options: 0,
      choices: 0,
      realization: 0,
    };
```

Keep the existing audio state declarations immediately after this block.

- [ ] **Step 4: Add exact progression, snapshot, request-token, and staleness helpers**

After `genSpice()`, add:

```javascript
    function progressionFromSlots() {
      return slots.map((slot) => String(slot.figure || '').trim());
    }

    function currentGenerationSnapshot() {
      return SopranoEditor.makeGenerationSnapshot(genKey(), progressionFromSlots());
    }

    function beginRequest(kind, snapshot) {
      requestSerial[kind] += 1;
      return { kind, snapshot, token: requestSerial[kind] };
    }

    function requestIsCurrent(request) {
      return request.token === requestSerial[request.kind]
        && request.snapshot === currentGenerationSnapshot();
    }

    function invalidateGenerationRequests() {
      Object.keys(requestSerial).forEach((kind) => {
        requestSerial[kind] += 1;
      });
    }

    function markGeneratedResultStale() {
      readSlotsFromDom();
      invalidateGenerationRequests();
      if (!renderedSnapshot || currentGenerationSnapshot() === renderedSnapshot) {
        return;
      }
      generatedResultStale = true;
      renderSopranoOptions();
      const more = $('btnMoreSoprano');
      if (more) more.disabled = true;
      setGenStatus('Progression changed · click Realize MusicXML to refresh the score and soprano choices.');
    }

    function checkedProgression() {
      readSlotsFromDom();
      const progression = progressionFromSlots();
      if (!progression.length || progression.some((figure) => !figure)) {
        setGenStatus('Every Roman-numeral slot needs a figure before realization.', true);
        return null;
      }
      return progression;
    }
```

Wire the stable invalidation hooks once, beside the existing Generate button
listeners:

```javascript
    $('genKey').addEventListener('change', markGeneratedResultStale);
    rnGrid.addEventListener('input', markGeneratedResultStale);
```

After an RN alternative is selected (`slots[index].figure =
row.dataset.figure`), call `renderSlots()` first and then
`markGeneratedResultStale()`. The order matters: the stale helper reads the
current RN inputs, so the DOM must already contain the replacement figure.

- [ ] **Step 5: Add transactional option and realization requests**

Add:

```javascript
    async function requestSopranoOptions({
      key,
      progression,
      count,
      snapshot,
    }) {
      const request = beginRequest('options', snapshot);
      try {
        const res = await fetch('/generate/soprano-options', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key, progression, count }),
        });
        const data = await res.json();
        if (!requestIsCurrent(request)) {
          return { ok: false, stale: true, options: [] };
        }
        if (!res.ok) {
          throw new Error(formatDetail(data.detail) || `HTTP ${res.status}`);
        }
        return { ok: true, stale: false, options: data.options || [] };
      } catch (err) {
        if (!requestIsCurrent(request)) {
          return { ok: false, stale: true, options: [] };
        }
        return {
          ok: false,
          stale: false,
          options: [],
          error: err.message,
        };
      }
    }

    async function finalizeRealization(soprano, {
      key,
      progression,
      snapshot,
      selectionId,
      onSuccess = null,
      failureMessage = 'Could not realize this progression',
    }) {
      const request = beginRequest('realization', snapshot);
      setGenStatus(`<span class="spinner"></span> Realizing four-part hymn…`);
      try {
        const body = { key, progression, time_signature: '4/4' };
        if (soprano) body.soprano = soprano;
        const res = await fetch('/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!requestIsCurrent(request)) return false;
        if (!res.ok) {
          throw new Error(formatDetail(data.detail) || `HTTP ${res.status}`);
        }

        lastMusicXml = data.musicxml;
        lastPlayback = data.playback || null;
        renderedSnapshot = snapshot;
        renderedKey = key;
        renderedProgression = progression.slice();
        generatedResultStale = false;
        selectedSopranoId = selectionId;
        if (onSuccess) onSuccess(data);
        renderGenerationResult(data, progression);
        setGenStatus('');
        await renderOsmdPreview(lastMusicXml);
        return requestIsCurrent(request);
      } catch (err) {
        if (!requestIsCurrent(request)) return false;
        setGenStatus(`${failureMessage}: ${err.message}`, true);
        return false;
      }
    }
```

- [ ] **Step 6: Render stable generated/Custom cards and a reusable result shell**

Replace `renderSopranoOptions()` with:

```javascript
    function visibleSopranoEntries() {
      const entries = sopranoOptions.map((option, i) => ({
        id: `generated:${i}`,
        label: `Option ${i + 1}`,
        option,
      }));
      if (customSoprano && customSoprano.snapshot === renderedSnapshot) {
        entries.push({ id: 'custom', label: 'Custom', option: customSoprano });
      }
      return entries;
    }

    function renderSopranoOptions() {
      const container = $('sopranoOptions');
      if (!container) return;
      const entries = visibleSopranoEntries();
      container.innerHTML = entries.map((entry) => `
        <div class="soprano-option ${entry.id === selectedSopranoId ? 'selected' : ''}" data-id="${escapeAttr(entry.id)}">
          <button type="button" class="play-mini" data-id="${escapeAttr(entry.id)}"
            ${generatedResultStale ? 'disabled' : ''}
            title="Preview ${escapeAttr(entry.label)} soprano"
            aria-label="Preview ${escapeAttr(entry.label)} soprano">▶</button>
          <button type="button" class="select-soprano" data-id="${escapeAttr(entry.id)}"
            ${generatedResultStale ? 'disabled' : ''}
            aria-pressed="${entry.id === selectedSopranoId ? 'true' : 'false'}">
            <strong>${escapeHtml(entry.label)}</strong>
            <span class="notes">${entry.option.pitches.map(escapeHtml).join(' · ')}</span>
          </button>
        </div>`).join('');

      const byId = new Map(entries.map((entry) => [entry.id, entry]));
      container.querySelectorAll('.play-mini').forEach((button) => {
        button.addEventListener('click', () => {
          if (generatedResultStale) return;
          const entry = byId.get(button.dataset.id);
          if (entry) {
            playSopranoPreview(
              entry.option.soprano,
              (lastPlayback && lastPlayback.tempo_bpm) || 75,
            );
          }
        });
      });
      container.querySelectorAll('.select-soprano').forEach((button) => {
        button.addEventListener('click', async () => {
          if (generatedResultStale) return;
          const entry = byId.get(button.dataset.id);
          if (!entry || entry.id === selectedSopranoId) return;
          await finalizeRealization(entry.option.soprano, {
            key: renderedKey,
            progression: renderedProgression.slice(),
            snapshot: renderedSnapshot,
            selectionId: entry.id,
            failureMessage: 'Could not realize the selected soprano',
          });
        });
      });
    }
```

Add:

```javascript
    function renderGenerationResult(data, progression) {
      const chips = progression.map((figure) =>
        `<span class="chip">${escapeHtml(figure)}</span>`).join('');
      const tempo = (lastPlayback && lastPlayback.tempo_bpm) || 75;
      genResults.innerHTML = `
        <div class="hero">
          <div>
            <div class="keyname">${escapeHtml(data.key)}</div>
            <div class="fname">Four-part SATB · ${progression.length} chords · ${escapeHtml(data.time_signature)} · ${tempo} BPM</div>
          </div>
          <div class="conf"><div class="num">✓</div><div class="lbl">realized</div></div>
        </div>
        <div class="section-title"><h2>Progression</h2><span class="count">${progression.length}</span></div>
        <div class="chip-row">${chips}</div>
        <div class="section-title"><h2>Soprano options</h2><span class="count" id="sopranoOptionsCount">${sopranoOptions.length} generated</span></div>
        <div class="soprano-options" id="sopranoOptions"></div>
        <div class="soprano-more">
          <button type="button" class="btn" id="btnMoreSoprano">More options</button>
          <span class="soprano-more-note" id="sopranoMoreNote" hidden>No more distinct generated soprano lines for this progression.</span>
        </div>
        <div class="section-title"><h2>Score</h2><span class="count">MusicXML preview</span></div>
        <div class="score-panel">
          <div id="osmdContainer"><div class="score-fallback">Loading notation…</div></div>
        </div>
        <div class="gen-done">
          <button type="button" class="btn btn-primary" id="btnPlay" ${lastPlayback ? '' : 'disabled'}>Play</button>
          <button type="button" class="btn" id="btnStop" disabled>Stop</button>
          <button type="button" class="btn" id="btnDownload">Download MusicXML</button>
          <span class="ok-msg">Block chords @ ${tempo} BPM · rough Web Audio synth · download for MuseScore.</span>
        </div>`;
      genResults.className = 'show';
      renderSopranoOptions();
      $('btnMoreSoprano').addEventListener('click', fetchMoreSopranoOptions);
      $('btnMoreSoprano').disabled =
        generatedResultStale || sopranoOptionsExhausted;
      $('sopranoMoreNote').hidden = !sopranoOptionsExhausted;
      $('btnDownload').addEventListener('click', downloadMusicXml);
      $('btnPlay').addEventListener('click', () => playPlayback());
      $('btnStop').addEventListener('click', () => stopPlayback());
    }
```

Update `.soprano-option` CSS so the two inner controls are keyboard-operable:

```css
    .soprano-option { cursor: default; }
    .soprano-option .select-soprano {
      display: inline-flex; align-items: center; gap: .45rem; border: 0;
      background: transparent; color: inherit; cursor: pointer; padding: 0;
      font: inherit;
    }
    .soprano-option button:disabled { cursor: not-allowed; opacity: .55; }
```

- [ ] **Step 7: Replace initial realization with exact-snapshot flow**

Replace `realizeProgression()` with:

```javascript
    async function realizeProgression() {
      const progression = checkedProgression();
      if (!progression) return;
      const key = genKey();
      const snapshot = SopranoEditor.makeGenerationSnapshot(key, progression);
      setGenStatus(`<span class="spinner"></span> Loading soprano options…`);
      const optionResult = await requestSopranoOptions({
        key,
        progression,
        count: 3,
        snapshot,
      });
      if (optionResult.stale) return;

      const freshOptions = optionResult.ok ? optionResult.options : [];
      const defaultSoprano = freshOptions.length
        ? freshOptions[0].soprano
        : null;
      const success = await finalizeRealization(defaultSoprano, {
        key,
        progression,
        snapshot,
        selectionId: defaultSoprano ? 'generated:0' : null,
        onSuccess: () => {
          sopranoOptions = freshOptions;
          sopranoOptionsSnapshot = snapshot;
          sopranoOptionsExhausted = false;
        },
      });
      if (success && !optionResult.ok) {
        setGenStatus(
          `Score realized, but soprano options could not load: ${optionResult.error}`,
          true,
        );
      }
    }
```

Delete the old monolithic body of `finalizeRealization`; the transactional
version from Step 5 plus `renderGenerationResult()` now owns that behavior.

- [ ] **Step 8: Make More options snapshot-safe while keeping its count generated-only**

Replace `fetchMoreSopranoOptions()` with:

```javascript
    async function fetchMoreSopranoOptions() {
      if (generatedResultStale
          || renderedSnapshot !== currentGenerationSnapshot()) {
        markGeneratedResultStale();
        return;
      }
      const nextCount = Math.min(sopranoOptions.length + 3, 10);
      const button = $('btnMoreSoprano');
      const note = $('sopranoMoreNote');
      if (button) button.disabled = true;
      if (nextCount <= sopranoOptions.length) {
        sopranoOptionsExhausted = true;
        if (note) note.hidden = false;
        return;
      }

      const result = await requestSopranoOptions({
        key: renderedKey,
        progression: renderedProgression.slice(),
        count: nextCount,
        snapshot: renderedSnapshot,
      });
      if (result.stale) return;
      if (!result.ok) {
        setGenStatus(`Could not load more soprano options: ${result.error}`, true);
        if (button) button.disabled = sopranoOptionsExhausted;
        return;
      }

      if (result.options.length > sopranoOptions.length) {
        sopranoOptions = result.options;
        sopranoOptionsSnapshot = renderedSnapshot;
        renderSopranoOptions();
        $('sopranoOptionsCount').textContent =
          `${sopranoOptions.length} generated`;
        if (button) button.disabled = false;
        if (note) note.hidden = true;
      } else {
        sopranoOptionsExhausted = true;
        if (button) button.disabled = true;
        if (note) note.hidden = false;
      }
    }
```

- [ ] **Step 9: Run structural, JavaScript, and existing endpoint checks**

Extract the inline script to a temporary file and validate it:

```bash
source .venv/bin/activate
python -m pytest tests/test_static_generate_ui.py -v
python - <<'PY'
from pathlib import Path
import re

html = Path("app/static/index.html").read_text(encoding="utf-8")
scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S)
inline = "\n".join(script for script in scripts if script.strip())
Path("/tmp/harmonyx-index-inline.js").write_text(inline, encoding="utf-8")
PY
node --check /tmp/harmonyx-index-inline.js
python -m pytest tests/test_generate_endpoint.py -k "generate or soprano" -q
```

Expected: all commands exit 0.

- [ ] **Step 10: Commit the snapshot-safe frontend foundation**

```bash
git add app/static/index.html tests/test_static_generate_ui.py
git commit -m "Make soprano option selection snapshot safe"
```

---

### Task 5: Frontend editor — legal tiles, preview, Reset, Apply, and Custom

**Files:**
- Modify: `tests/test_static_generate_ui.py`
- Modify: `app/static/index.html:262-276,841-1008`

**Interfaces:**
- Consumes: `POST /generate/soprano-choices`,
  `SopranoEditor.choiceSlotsMatchProgression()`,
  `SopranoEditor.pitchNamesForLine()`, existing
  `playSopranoPreview()`, and Task 4's transactional
  `finalizeRealization()`.
- Produces editor state:
  - `sopranoChoiceSlots`, `sopranoChoicesSnapshot`
  - `sopranoEditorStart`, `sopranoDraft`, `sopranoDraftSnapshot`
  - `sopranoUpdatedIndices: Set<number>`
  - `sopranoDraftNeedsReview`, `sopranoEditorOpen`,
    `sopranoApplyInFlight`
- Produces `requestSopranoChoices()`, `openSopranoEditor()`,
  `renderSopranoEditor()`, and `applySopranoDraft()`.
- Successful Apply updates exactly one `customSoprano` object and selects
  identity `custom`; it does not mutate `sopranoOptions`.

- [ ] **Step 1: Extend the structural tests so they fail on missing editor controls**

Append to `tests/test_static_generate_ui.py`:

```python
def test_generate_ui_has_legal_tile_editor_and_explicit_actions():
    script = _generate_script()
    for expected in (
        "/generate/soprano-choices",
        'id="sopranoEditorHost"',
        'id="btnCustomizeSoprano"',
        'id="btnPreviewDraft"',
        'id="btnApplySoprano"',
        'id="btnResetSoprano"',
        "aria-pressed=",
        "updated for new chord",
    ):
        assert expected in script


def test_generate_ui_keeps_custom_separate_from_generated_count():
    script = _generate_script()
    assert "id: 'custom'" in script
    assert "sopranoOptions.length + 3" in script
    assert "customSoprano = {" in script
```

- [ ] **Step 2: Run the structural tests and verify the expected failure**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/test_static_generate_ui.py -v
```

Expected: the two new tests fail because the editor DOM and Apply flow do not
exist.

- [ ] **Step 3: Add editor state and the choices request**

Add beside the other soprano state:

```javascript
    let sopranoChoiceSlots = null;
    let sopranoChoicesSnapshot = null;
    let sopranoEditorStart = null;
    let sopranoDraft = null;
    let sopranoDraftSnapshot = null;
    let sopranoUpdatedIndices = new Set();
    let sopranoDraftNeedsReview = false;
    let sopranoEditorOpen = false;
    let sopranoApplyInFlight = false;
```

Add:

```javascript
    async function requestSopranoChoices({
      key,
      progression,
      snapshot,
    }) {
      const request = beginRequest('choices', snapshot);
      try {
        const res = await fetch('/generate/soprano-choices', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key, progression }),
        });
        const data = await res.json();
        if (!requestIsCurrent(request)) {
          return { ok: false, stale: true, slots: [] };
        }
        if (!res.ok) {
          throw new Error(formatDetail(data.detail) || `HTTP ${res.status}`);
        }
        const choiceSlots = data.slots || [];
        if (!SopranoEditor.choiceSlotsMatchProgression(
          choiceSlots,
          progression,
        )) {
          throw new Error('legal pitch choices did not match the progression');
        }
        return { ok: true, stale: false, slots: choiceSlots };
      } catch (err) {
        if (!requestIsCurrent(request)) {
          return { ok: false, stale: true, slots: [] };
        }
        return {
          ok: false,
          stale: false,
          slots: [],
          error: err.message,
        };
      }
    }
```

- [ ] **Step 4: Add the editor host above the score and the Customize action**

In `renderGenerationResult()`, insert immediately after the `.soprano-more`
row and before the Score section:

```html
        <div id="sopranoCustomizeAction"></div>
        <div id="sopranoEditorHost" hidden></div>
```

After `renderSopranoOptions()` in `renderGenerationResult()`, call:

```javascript
      renderSopranoCustomizeAction();
      renderSopranoEditor();
```

Add:

```javascript
    function selectedGeneratedOption() {
      if (!selectedSopranoId
          || !selectedSopranoId.startsWith('generated:')) return null;
      const index = Number(selectedSopranoId.split(':')[1]);
      return Number.isInteger(index) ? sopranoOptions[index] || null : null;
    }

    function renderSopranoCustomizeAction() {
      const host = $('sopranoCustomizeAction');
      if (!host) return;
      const option = selectedGeneratedOption();
      if (!option) {
        host.innerHTML = '';
        return;
      }
      host.innerHTML = `
        <button type="button" class="btn" id="btnCustomizeSoprano"
          ${generatedResultStale ? 'disabled' : ''}>Customize melody</button>`;
      $('btnCustomizeSoprano').addEventListener('click', openSopranoEditor);
    }
```

Also call `renderSopranoCustomizeAction()` at the end of
`renderSopranoOptions()` so switching generated cards updates the action.

- [ ] **Step 5: Implement lazy editor opening and accessible legal tiles**

Add:

```javascript
    async function openSopranoEditor() {
      if (generatedResultStale
          || renderedSnapshot !== currentGenerationSnapshot()) {
        markGeneratedResultStale();
        return;
      }
      const option = selectedGeneratedOption();
      if (!option) return;

      let choiceSlots = sopranoChoicesSnapshot === renderedSnapshot
        ? sopranoChoiceSlots
        : null;
      if (!choiceSlots) {
        setGenStatus(`<span class="spinner"></span> Loading legal soprano pitches…`);
        const result = await requestSopranoChoices({
          key: renderedKey,
          progression: renderedProgression.slice(),
          snapshot: renderedSnapshot,
        });
        if (result.stale) return;
        if (!result.ok) {
          setGenStatus(`Could not load legal soprano pitches: ${result.error}`, true);
          return;
        }
        choiceSlots = result.slots;
        sopranoChoiceSlots = choiceSlots;
        sopranoChoicesSnapshot = renderedSnapshot;
      }

      const preserveReconciledDraft = sopranoDraftNeedsReview
        && sopranoDraftSnapshot === renderedSnapshot
        && Boolean(sopranoDraft);
      const openingLine = preserveReconciledDraft
        ? sopranoDraft
        : option.soprano;
      try {
        SopranoEditor.pitchNamesForLine(openingLine, choiceSlots);
      } catch (err) {
        setGenStatus(`Could not open melody editor: ${err.message}`, true);
        return;
      }

      if (!preserveReconciledDraft) {
        sopranoEditorStart = option.soprano.slice();
        sopranoDraft = option.soprano.slice();
        sopranoDraftSnapshot = renderedSnapshot;
        sopranoUpdatedIndices = new Set();
        sopranoDraftNeedsReview = false;
      }
      sopranoEditorOpen = true;
      setGenStatus('');
      renderSopranoEditor();
    }

    function renderSopranoEditor() {
      const host = $('sopranoEditorHost');
      if (!host) return;
      if (!sopranoEditorOpen
          || !sopranoChoiceSlots
          || !sopranoDraft) {
        host.hidden = true;
        host.innerHTML = '';
        return;
      }

      const tiles = sopranoChoiceSlots.map((slot, index) => {
        const selected = slot.choices.find(
          (choice) => Number(choice.midi) === sopranoDraft[index],
        );
        const updated = sopranoUpdatedIndices.has(index);
        return `
          <section class="melody-tile ${updated ? 'updated' : ''}">
            <div class="melody-tile-head">
              <span>#${index + 1}</span>
              <strong>${escapeHtml(slot.roman)}</strong>
            </div>
            <div class="melody-selected">${escapeHtml(selected.pitch)}</div>
            <div class="melody-pitch-choices" role="group"
              aria-label="Legal soprano pitches for chord ${index + 1}, ${escapeAttr(slot.roman)}">
              ${slot.choices.map((choice) => `
                <button type="button"
                  data-soprano-slot="${index}"
                  data-midi="${choice.midi}"
                  aria-pressed="${Number(choice.midi) === sopranoDraft[index] ? 'true' : 'false'}"
                  ${sopranoApplyInFlight ? 'disabled' : ''}>
                  ${escapeHtml(choice.pitch)}
                </button>`).join('')}
            </div>
            ${updated
              ? '<span class="melody-updated">updated for new chord</span>'
              : ''}
          </section>`;
      }).join('');

      host.hidden = false;
      host.innerHTML = `
        <div class="soprano-editor">
          <div class="section-title">
            <h2>Customize soprano melody</h2>
            <span class="count">one legal pitch per chord</span>
          </div>
          <div class="melody-tiles">${tiles}</div>
          <div class="melody-actions">
            <button type="button" class="btn" id="btnPreviewDraft"
              ${sopranoApplyInFlight ? 'disabled' : ''}>Preview melody</button>
            <button type="button" class="btn" id="btnResetSoprano"
              ${sopranoApplyInFlight ? 'disabled' : ''}>Reset</button>
            <button type="button" class="btn btn-primary" id="btnApplySoprano"
              ${sopranoApplyInFlight ? 'disabled' : ''}>Apply melody</button>
          </div>
        </div>`;

      host.querySelectorAll('[data-soprano-slot][data-midi]').forEach((button) => {
        button.addEventListener('click', () => {
          const index = Number(button.dataset.sopranoSlot);
          sopranoDraft[index] = Number(button.dataset.midi);
          renderSopranoEditor();
        });
      });
      $('btnPreviewDraft').addEventListener('click', () => {
        playSopranoPreview(
          sopranoDraft,
          (lastPlayback && lastPlayback.tempo_bpm) || 75,
        );
      });
      $('btnResetSoprano').addEventListener('click', () => {
        sopranoDraft = sopranoEditorStart.slice();
        sopranoUpdatedIndices = new Set();
        sopranoDraftNeedsReview = false;
        renderSopranoEditor();
      });
      $('btnApplySoprano').addEventListener('click', applySopranoDraft);
    }
```

- [ ] **Step 6: Implement Apply as a transaction that updates one Custom card**

Add:

```javascript
    async function applySopranoDraft() {
      if (sopranoApplyInFlight
          || !sopranoDraft
          || sopranoDraftSnapshot !== renderedSnapshot
          || renderedSnapshot !== currentGenerationSnapshot()) {
        markGeneratedResultStale();
        return;
      }

      const submitted = sopranoDraft.slice();
      const pitches = SopranoEditor.pitchNamesForLine(
        submitted,
        sopranoChoiceSlots,
      );
      sopranoApplyInFlight = true;
      renderSopranoEditor();
      const success = await finalizeRealization(submitted, {
        key: renderedKey,
        progression: renderedProgression.slice(),
        snapshot: renderedSnapshot,
        selectionId: 'custom',
        failureMessage:
          'This complete melody could not be harmonized under the current part-writing rules',
        onSuccess: () => {
          customSoprano = {
            soprano: submitted,
            pitches,
            snapshot: renderedSnapshot,
          };
          sopranoDraft = submitted.slice();
          sopranoDraftSnapshot = renderedSnapshot;
          sopranoDraftNeedsReview = false;
          sopranoEditorOpen = true;
        },
      });
      sopranoApplyInFlight = false;
      if (sopranoEditorOpen) renderSopranoEditor();
    }
```

The call updates `customSoprano` only inside `onSuccess`, after the current
request has succeeded. Therefore a 422 leaves the previous score, Custom card,
download, playback, and draft untouched.

- [ ] **Step 7: Add wrapping/scrolling tile styles**

Add beside the existing soprano-option styles:

```css
    #sopranoCustomizeAction { margin: 0 0 .7rem; }
    .soprano-editor {
      margin: .8rem 0 1.2rem; padding: 1rem; background: var(--card);
      border: 1px solid var(--border); border-radius: 14px; box-shadow: var(--shadow);
    }
    .soprano-editor .section-title { margin-top: 0; }
    .melody-tiles {
      display: flex; gap: .65rem; overflow-x: auto; padding: .1rem 0 .65rem;
      scroll-snap-type: x proximity;
    }
    .melody-tile {
      flex: 0 0 190px; scroll-snap-align: start; padding: .7rem;
      border: 1px solid var(--border); border-radius: 12px; background: var(--card-2);
    }
    .melody-tile.updated { border-color: #c9922e; }
    .melody-tile-head { display: flex; justify-content: space-between; color: var(--faint); }
    .melody-selected {
      margin: .35rem 0; font-family: var(--font-serif); font-size: 1.25rem;
      font-weight: 700; color: var(--accent);
    }
    .melody-pitch-choices { display: flex; flex-wrap: wrap; gap: .3rem; }
    .melody-pitch-choices button {
      border: 1px solid var(--border); border-radius: 999px; padding: .2rem .45rem;
      background: var(--card); color: var(--fg); cursor: pointer;
    }
    .melody-pitch-choices button[aria-pressed="true"] {
      border-color: var(--accent-2); background: var(--accent-2); color: #fff;
    }
    .melody-pitch-choices button:disabled { cursor: not-allowed; opacity: .55; }
    .melody-updated { display: block; margin-top: .45rem; color: #c9922e; font-size: .74rem; }
    .melody-actions { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .7rem; }
    @media (max-width: 560px) {
      .soprano-editor { padding: .75rem; }
      .melody-tile { flex-basis: min(82vw, 190px); }
    }
```

- [ ] **Step 8: Run the frontend unit, structure, and syntax checks**

Run:

```bash
source .venv/bin/activate
node --test tests/test_soprano_editor.js
python -m pytest tests/test_static_generate_ui.py -v
python - <<'PY'
from pathlib import Path
import re

html = Path("app/static/index.html").read_text(encoding="utf-8")
scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S)
Path("/tmp/harmonyx-index-inline.js").write_text(
    "\n".join(script for script in scripts if script.strip()),
    encoding="utf-8",
)
PY
node --check /tmp/harmonyx-index-inline.js
```

Expected: all commands exit 0.

- [ ] **Step 9: Commit the editor slice**

```bash
git add app/static/index.html tests/test_static_generate_ui.py
git commit -m "Add inline custom soprano melody editor"
```

---

### Task 6: Frontend integration — reconcile drafts and close every stale path

**Files:**
- Modify: `tests/test_static_generate_ui.py`
- Modify: `app/static/index.html:662-839,841-1008`

**Interfaces:**
- Consumes: `SopranoEditor.reconcileSopranoDraft()` and Task 5's
  `requestSopranoChoices()`.
- Produces: a final `realizeProgression()` that renders the fresh default
  score first and, when a prior draft exists, commits a reconciled but
  unapplied draft for the same snapshot.
- Invalidation sources: key change, RN typing, RN-alternative selection, and
  successful Propose/Regenerate.
- Fresh reconciliation rules:
  - preserve overlapping legal pitches;
  - replace illegal pitches with the fresh generated default;
  - append the fresh default for new slots;
  - discard removed slots;
  - mark every replacement or append;
  - set Reset target to the fresh generated default;
  - hide the old snapshot's Custom card;
  - never auto-apply the reconciled draft.

- [ ] **Step 1: Add failing integration-shape tests**

Append to `tests/test_static_generate_ui.py`:

```python
def test_generate_ui_never_filters_index_aligned_progressions():
    script = _generate_script()
    realization_area = script[
        script.index("async function fetchMoreSopranoOptions")
        :script.index("function downloadMusicXml")
    ]
    assert ".filter(Boolean)" not in realization_area


def test_generate_ui_reconciles_only_after_fresh_realization():
    script = _generate_script()
    assert "reconcileSopranoDraft" in script
    assert "sopranoUpdatedIndices = new Set(reconciled.updatedIndices)" in script
    assert "sopranoEditorStart = defaultSoprano.slice()" in script
    assert "sopranoDraftNeedsReview = true" in script
    assert "sopranoEditorOpen = false" in script
```

- [ ] **Step 2: Run the structural tests and verify the expected failure**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/test_static_generate_ui.py -v
```

Expected: the reconciliation-shape test fails; if any old
`.filter(Boolean)` remains in realization code, the alignment test fails too.

- [ ] **Step 3: Preserve drafts while closing stale interactions**

Extend `markGeneratedResultStale()` immediately after setting
`generatedResultStale = true`:

```javascript
      sopranoEditorOpen = false;
      renderSopranoEditor();
```

Do not clear `sopranoDraft`, `sopranoDraftSnapshot`, or `customSoprano`.
Snapshot-bound rendering already hides an old Custom card after a fresh score
is committed.

In the generated-card selection handler, pass this callback to
`finalizeRealization()`:

```javascript
            onSuccess: () => {
              if (entry.id.startsWith('generated:')) {
                sopranoDraftNeedsReview = false;
                sopranoEditorOpen = false;
              }
            },
```

This closes the current editor when the user intentionally switches to a
different generated line, without deleting a prior draft.

- [ ] **Step 4: Make Propose/Regenerate mark old output stale instead of deleting it**

In `proposeProgression()`, remove the pre-request assignments that clear
`genResults`, `lastMusicXml`, `lastPlayback`, and `osmdInstance`. Keep
`stopPlayback()`.

Capture a proposal token before `fetch('/progression', ...)`:

```javascript
      const proposalToken = ++requestSerial.proposal;
```

After reading the JSON response, ignore an older proposal:

```javascript
        if (proposalToken !== requestSerial.proposal) return;
```

After assigning the returned figures to `slots`, render and mark the prior
result stale:

```javascript
        renderSlots();
        markGeneratedResultStale();
```

Keep the existing Propose status text after this call so it remains the final
visible message.

- [ ] **Step 5: Replace `realizeProgression()` with reconciliation-aware flow**

Replace the Task 4 version with:

```javascript
    async function realizeProgression() {
      const progression = checkedProgression();
      if (!progression) return;
      const key = genKey();
      const snapshot = SopranoEditor.makeGenerationSnapshot(key, progression);
      const priorDraft = sopranoDraft ? sopranoDraft.slice() : null;

      setGenStatus(`<span class="spinner"></span> Loading soprano choices…`);
      const [optionResult, choiceResult] = await Promise.all([
        requestSopranoOptions({
          key,
          progression,
          count: 3,
          snapshot,
        }),
        priorDraft
          ? requestSopranoChoices({ key, progression, snapshot })
          : Promise.resolve({
              ok: false,
              stale: false,
              skipped: true,
              slots: [],
            }),
      ]);
      if (optionResult.stale || choiceResult.stale) return;

      const freshOptions = optionResult.ok ? optionResult.options : [];
      const defaultSoprano = freshOptions.length
        ? freshOptions[0].soprano
        : null;
      let reconciled = null;
      let reconciliationError = null;
      if (priorDraft && choiceResult.ok && defaultSoprano) {
        try {
          reconciled = SopranoEditor.reconcileSopranoDraft(
            priorDraft,
            choiceResult.slots,
            defaultSoprano,
          );
        } catch (err) {
          reconciliationError = err.message;
        }
      }

      const success = await finalizeRealization(defaultSoprano, {
        key,
        progression,
        snapshot,
        selectionId: defaultSoprano ? 'generated:0' : null,
        onSuccess: () => {
          sopranoOptions = freshOptions;
          sopranoOptionsSnapshot = snapshot;
          sopranoOptionsExhausted = false;
          sopranoEditorOpen = false;

          if (reconciled) {
            sopranoChoiceSlots = choiceResult.slots;
            sopranoChoicesSnapshot = snapshot;
            sopranoEditorStart = defaultSoprano.slice();
            sopranoDraft = reconciled.draft;
            sopranoDraftSnapshot = snapshot;
            sopranoUpdatedIndices = new Set(reconciled.updatedIndices);
            sopranoDraftNeedsReview = true;
          }
        },
      });
      if (!success) return;

      if (!optionResult.ok) {
        setGenStatus(
          `Score realized, but soprano options could not load: ${optionResult.error}`,
          true,
        );
      } else if (priorDraft && !choiceResult.ok) {
        setGenStatus(
          `Score realized, but the previous custom draft could not be reconciled: ${choiceResult.error}`,
          true,
        );
      } else if (reconciliationError) {
        setGenStatus(
          `Score realized, but the previous custom draft could not be reconciled: ${reconciliationError}`,
          true,
        );
      } else if (reconciled) {
        setGenStatus(
          'Previous custom melody updated for this progression · open Customize melody, review marked notes, and Apply melody when ready.',
        );
      }
    }
```

The fresh generated options, legal slots, and reconciled draft become global
only inside `onSuccess`, so a failed fresh realization leaves the previous
successful artifacts intact.

- [ ] **Step 6: Preserve a reconciled draft when Customize reopens**

`openSopranoEditor()` preserves a prior draft only when all three reconciliation
guards are true:

```javascript
      const preserveReconciledDraft = sopranoDraftNeedsReview
        && sopranoDraftSnapshot === renderedSnapshot
        && Boolean(sopranoDraft);
```

Keep those guards exact. They ensure a draft reconciled in Step 5 opens with
its updated markers instead of being overwritten by option 1, while a later
intentional selection of another generated card starts a fresh edit session
from that selected line. Reset still uses `sopranoEditorStart`, which Step 5
sets to the fresh default.

- [ ] **Step 7: Guard the RN-alternatives response with its captured snapshot**

In `toggleAltsPopover()`, after `readSlotsFromDom()` capture:

```javascript
      const snapshot = currentGenerationSnapshot();
```

Immediately after `const data = await res.json();`, add:

```javascript
        if (snapshot !== currentGenerationSnapshot()) {
          closeAltsPopover();
          return;
        }
```

This prevents a response requested for an old key/RN array from presenting a
replacement against the new array.

- [ ] **Step 8: Run all frontend automated checks**

Run:

```bash
source .venv/bin/activate
node --test tests/test_soprano_editor.js
python -m pytest tests/test_static_generate_ui.py -v
python - <<'PY'
from pathlib import Path
import re

html = Path("app/static/index.html").read_text(encoding="utf-8")
scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S)
Path("/tmp/harmonyx-index-inline.js").write_text(
    "\n".join(script for script in scripts if script.strip()),
    encoding="utf-8",
)
PY
node --check /tmp/harmonyx-index-inline.js
```

Expected: all commands exit 0.

- [ ] **Step 9: Commit reconciliation and stale-response closure**

```bash
git add app/static/index.html tests/test_static_generate_ui.py
git commit -m "Reconcile custom soprano drafts safely"
```

---

### Task 7: Integrated verification — automated suite and real browser

**Files:**
- Verify only; do not edit `tests/test_partwriting.py`.
- If verification exposes a defect, return to the smallest owning task, add a
  failing regression there, fix it, rerun that task, and create a focused fix
  commit before repeating this task.

**Interfaces:**
- Consumes every prior task.
- Produces evidence for all acceptance criteria, including actual browser UI,
  Web Audio behavior, score rendering, MusicXML content, stale guards, Custom
  identity, and failure preservation.

- [ ] **Step 1: Run the complete automated suite**

Run:

```bash
source .venv/bin/activate
python -m pytest -q
node --test tests/test_soprano_editor.js
```

Expected: both commands exit 0 with no failures.

- [ ] **Step 2: Prove the locked fixture and preserved stash are untouched**

Run:

```bash
git diff --exit-code -- tests/test_partwriting.py
git stash list --date=iso
```

Expected: the diff command exits 0, and the list still includes
`codex: preserve pre-cleanup work 2026-07-28`.

- [ ] **Step 3: Start the local app for browser verification**

Run in a foreground terminal:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected: Uvicorn reports the app at `http://127.0.0.1:8000`.

- [ ] **Step 4: Use `browser-harness` for the successful editor walkthrough**

Open `http://127.0.0.1:8000`, select Generate, and perform these exact checks:

1. Set Length to 4, Propose, edit the slots to `I`, `IV`, `V`, `I`, then
   Realize.
2. Select a generated option other than option 1 and click **Customize
   melody**.
3. Compare each tile's labels and MIDI-backed buttons with the corresponding
   `POST /generate/soprano-choices` response; confirm only those pitches are
   offered and one button per tile has `aria-pressed="true"`.
4. Change at least two tiles. Click **Preview melody** and confirm the
   displayed score and Download payload do not change.
5. Click **Apply melody**. Confirm the score redraws, full playback and
   Download now use the new response, and one selected **Custom** card appears.
6. Change another pitch and Apply again. Confirm the existing Custom card
   updates rather than a second Custom card appearing.
7. Click **More options**. Confirm generated cards grow or exhaust, the count
   describes generated options only, and the Custom card remains unchanged.
8. Click a generated card, then its **Customize melody** action; edit a pitch
   and click **Reset**. Confirm the exact generated starting line returns.

- [ ] **Step 5: Use `browser-harness` for stale and reconciliation checks**

Continue in the same browser:

1. With a custom draft present, type a different RN in one slot. Confirm
   preview/select/Customize/More controls for the old result are disabled and
   cannot issue `/generate`.
2. Realize again. Confirm the fresh generated default score is selected and
   the old Custom card is absent.
3. Open Customize. Confirm overlapping legal old notes were preserved,
   illegal/replaced or newly appended notes use the fresh default, and every
   replacement/append says **updated for new chord**.
4. Confirm the displayed score is still the fresh generated default until
   **Apply melody** is clicked.
5. Apply, then confirm exactly one Custom card returns for the new snapshot.
6. Change the key and repeat the stale-action check.
7. Trigger two generated-card selections rapidly for the same unchanged
   progression; confirm only the last request controls the selected card,
   score, playback, and download.

- [ ] **Step 6: Use `browser-harness` for the deterministic Apply failure**

Set a three-slot C-major progression to `I`, `V`, `I`, Realize, open
Customize, and choose `C4`, `D4`, `G4` (MIDI `[60, 62, 67]`). Each pitch is
locally legal, but this exact line has no complete hard-invariant-clean SATB
path.

Click **Apply melody** and confirm:

- the editor remains open with `C4 · D4 · G4`;
- the status says the complete melody could not be harmonized under current
  part-writing rules;
- the last successful score, playback, download, selected card, and previous
  Custom card remain unchanged; and
- pitch editing, Preview, Reset, and a later Apply retry work after the failed
  request completes.

- [ ] **Step 7: Verify exported soprano content from the browser response**

Save the successful custom MusicXML download, parse it with music21, and print
the soprano MIDI line:

```bash
source .venv/bin/activate
python - <<'PY'
from pathlib import Path
from music21 import converter
from app.generation.realize import satb_voicings_from_score

downloads = sorted(
    Path.home().joinpath("Downloads").glob("harmonyx_*.musicxml"),
    key=lambda path: path.stat().st_mtime,
)
assert downloads, "no Harmonyx MusicXML download found"
score = converter.parse(str(downloads[-1]))
print([voicing.s for voicing in satb_voicings_from_score(score)])
PY
```

Expected: the printed MIDI array exactly matches the pitches applied in the
successful browser step. This is a read-only verification of the user's
download; do not delete or move it.

- [ ] **Step 8: Stop the local server and inspect final repository state**

Stop Uvicorn with `Ctrl-C`, then run:

```bash
git status --short --branch
git log --oneline --decorate -8
git stash list --date=iso
```

Expected: no uncommitted application/test changes remain; the feature commits
are visible; the preservation stash remains.

- [ ] **Step 9: Run one final whole-suite verification after all fix commits**

Run:

```bash
source .venv/bin/activate
python -m pytest -q
node --test tests/test_soprano_editor.js
```

Expected: both commands exit 0. Record the exact observed pytest total and
browser walkthrough result in the implementation handoff.
