# Roman-Numeral Alternatives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user click a single chord slot in the Generate tab's
pre-Realize progression editor and see valid Roman-numeral alternatives for
just that slot, then swap one in — without needing the whole progression to
be invalid first.

**Architecture:** Add a new public function `roman_alternatives_for_slot()`
in `app/generation/fix.py` that reuses the existing (private)
`_alternatives_for_slot()` candidate pool and `_label_for_edit()` labeling,
but additionally confirms each candidate keeps the *whole* progression
passing `validate_progression`'s theory gate (cadence shape + all forbidden
edges, not just the two adjacent to the clicked slot). Expose it via a new
`POST /generate/roman-alternatives` endpoint. Frontend adds a `💡 alts`
button per `.rn-slot` that opens a popover of alternatives fetched from that
endpoint. Roman-numeral logic only — no melody/voicing/engine involvement.

**Tech Stack:** FastAPI + Pydantic (backend), vanilla JS in `app/static/index.html` (frontend), pytest + `fastapi.testclient.TestClient` (tests).

## Global Constraints

- Theory-only: always call `validate_progression(..., check_engine=False)` —
  no realizer/engine/melody involvement anywhere in this feature.
- A locked slot always returns `[]` (nothing to suggest) — both backend and
  frontend must agree on this (frontend disables the button as a UX
  shortcut; backend is the actual source of truth).
- Cap alternatives at `max_alternatives` (default 6, per approved spec).
- Out-of-range `index` is a 422, not a 500 or silent no-op.
- No change to `suggest_fixes()`, `_alternatives_for_slot()`, or
  `_label_for_edit()` — this is a new additive read path over existing
  building blocks, not a rewrite.

---

### Task 1: Backend — `roman_alternatives_for_slot()` in `fix.py`

**Files:**
- Modify: `app/generation/fix.py` (add function after `_alternatives_for_slot`,
  i.e. after line 468, before `_label_for_edit`)
- Test: `tests/test_generation_fix.py` (append new tests at end of file)

**Interfaces:**
- Produces: `roman_alternatives_for_slot(progression: Sequence[str],
  key_like: _chords.KeyLike, index: int, *, locked: Optional[Mapping[int,
  str]] = None, cadence: Optional[str] = None, max_alternatives: int = 6) ->
  List[Dict[str, str]]` — each dict is `{"figure": str, "label": str}`.
  Raises `ValueError` if `index` is out of range. Consumed by Task 2's
  endpoint.
- Consumes (already defined in `fix.py`, unchanged):
  `_alternatives_for_slot(figures, index, key_like) -> List[str]`,
  `_label_for_edit(index, old, new, key_like) -> str`,
  `_safe_locked(locked, length) -> Dict[int, str]`.
- Consumes `validate_progression` from `app/generation/validate.py`
  (already imported in `fix.py`).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generation_fix.py`:

```python
# --- roman_alternatives_for_slot ----------------------------------------

from app.generation.fix import roman_alternatives_for_slot


def test_roman_alternatives_returns_valid_nonempty_swap_for_unlocked_slot():
    prog = ["I", "IV", "V", "I"]
    alts = roman_alternatives_for_slot(prog, KEY, 1)
    assert alts
    figures = [a["figure"] for a in alts]
    assert "IV" not in figures  # never includes the current figure
    assert len(alts) <= 6
    for alt in alts:
        assert alt["label"]
        trial = list(prog)
        trial[1] = alt["figure"]
        result = validate_progression(trial, KEY, check_engine=False, suggest=False)
        assert result.ok, (alt, [i.message for i in result.issues])


def test_roman_alternatives_matches_known_pool_and_order():
    # Locked-in expectation from manual verification against the current
    # textbook pool + forbidden-transition table for ["I", "IV", "V", "I"]
    # at index 1 (IV) in C major.
    prog = ["I", "IV", "V", "I"]
    alts = roman_alternatives_for_slot(prog, KEY, 1, max_alternatives=6)
    figures = [a["figure"] for a in alts]
    assert figures == ["V", "V7", "ii", "vi", "I6", "iii"]


def test_roman_alternatives_locked_slot_returns_empty():
    prog = ["I", "IV", "V", "I"]
    alts = roman_alternatives_for_slot(prog, KEY, 1, locked={1: "IV"})
    assert alts == []


def test_roman_alternatives_out_of_range_index_raises():
    prog = ["I", "IV", "V", "I"]
    try:
        roman_alternatives_for_slot(prog, KEY, 4)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        roman_alternatives_for_slot(prog, KEY, -1)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_roman_alternatives_respects_max_alternatives_cap():
    prog = ["I", "IV", "V", "I"]
    alts = roman_alternatives_for_slot(prog, KEY, 1, max_alternatives=2)
    assert len(alts) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_generation_fix.py -k roman_alternatives -v`

Expected: FAIL with `ImportError: cannot import name 'roman_alternatives_for_slot'`.

- [ ] **Step 3: Implement `roman_alternatives_for_slot`**

In `app/generation/fix.py`, add this function immediately after
`_alternatives_for_slot` (after its closing `return ordered[:_MAX_SINGLE_SLOT_ALTS]`,
before `_label_for_edit`):

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
    """Up to ``max_alternatives`` theory-valid replacement figures for
    ``progression[index]``.

    Each candidate from ``_alternatives_for_slot`` (already filtered for
    forbidden transitions into/out of the immediate neighbors) is swapped in
    and re-checked against the *whole* progression via
    ``validate_progression`` (theory gate only, ``check_engine=False``) --
    this also catches cadence-shape and non-adjacent forbidden-edge
    violations that a neighbor-only check would miss.

    Returns ``[]`` if ``index`` is locked (nothing to suggest) or if no
    candidate keeps the progression valid. Raises ``ValueError`` if
    ``index`` is out of range.
    """
    figures = [str(f).strip() for f in progression]
    if index < 0 or index >= len(figures):
        raise ValueError(
            f"index {index} out of range for progression of length {len(figures)}"
        )

    locked_map = _safe_locked(locked, len(figures))
    if index in locked_map:
        return []

    cadence_arg = cadence
    if cadence is not None:
        c = str(cadence).strip().upper()
        cadence_arg = c if c in ("PAC", "HC") else None

    current = figures[index]
    out: List[Dict[str, str]] = []
    for fig in _alternatives_for_slot(figures, index, key_like):
        if fig == current:
            continue
        trial = list(figures)
        trial[index] = fig
        result = validate_progression(
            trial,
            key_like,
            cadence=cadence_arg,
            locked=locked_map or None,
            check_engine=False,
            suggest=False,
        )
        if not result.ok:
            continue
        out.append(
            {"figure": fig, "label": _label_for_edit(index, current, fig, key_like)}
        )
        if len(out) >= max_alternatives:
            break
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_generation_fix.py -k roman_alternatives -v`

Expected: all 5 new tests PASS.

- [ ] **Step 5: Run the full fix.py test file to check for regressions**

Run: `source .venv/bin/activate && python -m pytest tests/test_generation_fix.py -v`

Expected: all tests PASS (existing `suggest_fixes` tests unaffected — this
task only adds a new function, doesn't modify shared helpers).

- [ ] **Step 6: Commit**

```bash
git add app/generation/fix.py tests/test_generation_fix.py
git commit -m "Add roman_alternatives_for_slot for single-slot RN suggestions"
```

---

### Task 2: Backend — `POST /generate/roman-alternatives` endpoint

**Files:**
- Modify: `app/models.py` (add request/response models after
  `SopranoOptionsResponse`, i.e. after line 213)
- Modify: `app/main.py` (add endpoint after `generate_soprano_options`,
  i.e. after line 241; add import)
- Test: `tests/test_generate_endpoint.py` (append new tests at end of file)

**Interfaces:**
- Consumes: `roman_alternatives_for_slot(...)` from Task 1.
- Produces: `POST /generate/roman-alternatives` — request body
  `{progression: list[str], key: str, index: int, locked?: dict[int,str],
  cadence?: "PAC"|"HC"}`, response `{alternatives: [{figure, label}, ...]}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate_endpoint.py`:

```python
# --- POST /generate/roman-alternatives ----------------------------------


def test_roman_alternatives_happy_path_returns_valid_swaps():
    resp = client.post(
        "/generate/roman-alternatives",
        json={"key": "C major", "progression": ["I", "IV", "V", "I"], "index": 1},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    alts = data["alternatives"]
    assert alts
    assert len(alts) <= 6
    figures = [a["figure"] for a in alts]
    assert "IV" not in figures
    for a in alts:
        assert a["label"]


def test_roman_alternatives_locked_slot_returns_empty_list():
    resp = client.post(
        "/generate/roman-alternatives",
        json={
            "key": "C major",
            "progression": ["I", "IV", "V", "I"],
            "index": 1,
            "locked": {"1": "IV"},
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["alternatives"] == []


def test_roman_alternatives_out_of_range_index_returns_422():
    resp = client.post(
        "/generate/roman-alternatives",
        json={"key": "C major", "progression": ["I", "IV", "V", "I"], "index": 4},
    )
    assert resp.status_code == 422, resp.text


def test_roman_alternatives_chosen_swap_feeds_generate_successfully():
    # The whole point: a returned figure must be a drop-in valid replacement.
    alts_resp = client.post(
        "/generate/roman-alternatives",
        json={"key": "C major", "progression": ["I", "IV", "V", "I"], "index": 1},
    )
    chosen = alts_resp.json()["alternatives"][0]["figure"]
    prog = ["I", chosen, "V", "I"]

    gen_resp = client.post(
        "/generate",
        json={"key": "C major", "progression": prog},
    )
    assert gen_resp.status_code == 200, gen_resp.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_generate_endpoint.py -k roman_alternatives -v`

Expected: FAIL with 404 (endpoint doesn't exist yet).

- [ ] **Step 3: Add request/response models**

In `app/models.py`, the top-of-file import (line 9) is currently:

```python
from typing import List, Optional
```

Change it to:

```python
from typing import List, Literal, Optional
```

(`ProgressionRequest.locked` at line 226 already uses the lowercase builtin
generic `dict[int, str]` without a `typing.Dict` import — `from __future__
import annotations` makes this fine at runtime; follow that same convention
below rather than importing `Dict`.)

Then add, after `SopranoOptionsResponse` (after its closing `}` /
`model_config`, i.e. after line 213):

```python
class RomanAlternativesRequest(BaseModel):
    """Body for ``POST /generate/roman-alternatives``."""

    key: str = Field(..., description="Key, e.g. 'C major' or 'A minor'.", examples=["C major"])
    progression: List[str] = Field(
        ...,
        min_length=1,
        description="Roman-numeral figures in order, e.g. ['I', 'IV', 'V', 'I'].",
    )
    index: int = Field(..., ge=0, description="Index of the slot to suggest alternatives for.")
    locked: Optional[dict[int, str]] = Field(
        None, description="Map of index -> required figure for other slots."
    )
    cadence: Optional[Literal["PAC", "HC"]] = Field(
        None, description="If set, alternatives must preserve this cadence shape."
    )

    @field_validator("progression")
    @classmethod
    def _figures_nonempty(cls, value: List[str]) -> List[str]:
        if any(not (f and str(f).strip()) for f in value):
            raise ValueError("progression figures must be non-empty strings")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "C major",
                "progression": ["I", "IV", "V", "I"],
                "index": 1,
            }
        }
    }


class RomanAlternative(BaseModel):
    figure: str = Field(..., description="Candidate Roman-numeral figure.")
    label: str = Field(..., description="Short human-readable description of the edit.")


class RomanAlternativesResponse(BaseModel):
    """Up to 6 theory-valid replacement figures for one progression slot."""

    alternatives: List[RomanAlternative]

    model_config = {
        "json_schema_extra": {
            "example": {
                "alternatives": [
                    {"figure": "V", "label": "Use dominant"},
                    {"figure": "ii", "label": "Beat 2: IV → ii"},
                ]
            }
        }
    }
```

Check the top of `app/models.py` for existing `Literal`, `Dict`,
`field_validator` imports — `SopranoOptionsRequest` already uses
`field_validator`, `Field`, `List`; confirm `Literal` and `Dict` are
imported (grep for `from typing import` at the top of the file) and add
them to the existing `typing` import line if missing.

- [ ] **Step 4: Add the endpoint**

In `app/main.py`, update the import block (lines 33-42) to add the three
new model names:

```python
from .models import (
    AnalysisResponse,
    GenerateRequest,
    GenerateResponse,
    PlaybackPayload,
    ProgressionRequest,
    ProgressionResponse,
    RomanAlternativesRequest,
    RomanAlternativesResponse,
    SopranoOptionsRequest,
    SopranoOptionsResponse,
)
```

And add the import for the new function in the existing
`from .generation.realize import (...)` block — no, `roman_alternatives_for_slot`
lives in `app/generation/fix.py`, not `realize.py`, so add a new import line
after the `from .generation.chords import midi_to_name` line (line 32):

```python
from .generation.fix import roman_alternatives_for_slot
```

Then add the endpoint after `generate_soprano_options` (after its closing
`)` at line 241, before the `@app.get("/health"...)` block at line 244):

```python
@app.post(
    "/generate/roman-alternatives",
    response_model=RomanAlternativesResponse,
    tags=["generation"],
)
async def generate_roman_alternatives(
    body: RomanAlternativesRequest,
) -> RomanAlternativesResponse:
    """Up to 6 theory-valid replacement Roman numerals for one progression
    slot -- Roman-numeral logic only, no melody/engine involvement.
    """
    if body.index >= len(body.progression):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "index_out_of_range",
                "message": (
                    f"index {body.index} out of range for progression of "
                    f"length {len(body.progression)}"
                ),
            },
        )
    try:
        alts = roman_alternatives_for_slot(
            body.progression,
            body.key,
            body.index,
            locked=body.locked,
            cadence=body.cadence,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "index_out_of_range", "message": str(exc)},
        ) from exc
    except Exception as exc:  # music21 / RN parse failures, etc.
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_progression", "message": str(exc)},
        ) from exc

    return RomanAlternativesResponse(alternatives=alts)
```

Note: the explicit `body.index >= len(body.progression)` check before
calling `roman_alternatives_for_slot` is redundant with that function's own
`ValueError`, but keeps the 422 path direct and documents the constraint at
the API boundary (matches how `RomanAlternativesRequest.index` only
constrains `ge=0`, not the upper bound, since the upper bound depends on
`progression`'s length -- a cross-field constraint pydantic can't express
declaratively).

- [ ] **Step 5: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_generate_endpoint.py -k roman_alternatives -v`

Expected: all 4 new tests PASS.

- [ ] **Step 6: Run the full test suite to check for regressions**

Run: `source .venv/bin/activate && python -m pytest tests/ -q`

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add app/models.py app/main.py tests/test_generate_endpoint.py
git commit -m "Add POST /generate/roman-alternatives endpoint"
```

---

### Task 3: Frontend — `💡 alts` button and popover

**Files:**
- Modify: `app/static/index.html`
  - CSS: near `.rn-slot` rules (line 147-159)
  - JS: `renderSlots()` (lines 640-669)

**Interfaces:**
- Consumes: `POST /generate/roman-alternatives` (Task 2).
- Consumes existing `slots`, `readSlotsFromDom()`, `lockedMapFromSlots()`,
  `genKey()`, `genCadence()`, `$()`, `escapeHtml()`, `escapeAttr()` — all
  already defined elsewhere in this file.

Manual browser verification only (no JS test framework in this repo).

- [ ] **Step 1: Add CSS for the button and popover**

Near line 147-159 (existing `.rn-slot` rules), add:

```css
    .rn-slot { position: relative; }
    .rn-slot .alts-btn {
      font-size: .78rem; padding: .15rem .5rem; margin-top: .3rem;
      border-radius: 6px; border: 1px solid var(--border); background: var(--card);
      color: var(--faint); cursor: pointer;
    }
    .rn-slot .alts-btn:hover:not(:disabled) { color: var(--fg); background: var(--panel); }
    .rn-slot .alts-btn:disabled { opacity: .4; cursor: default; }
    .alts-popover {
      position: absolute; top: 100%; left: 0; z-index: 20; margin-top: .3rem;
      background: var(--card); border: 1px solid var(--border); border-radius: 8px;
      box-shadow: 0 6px 20px rgba(0,0,0,.15); padding: .4rem; min-width: 180px;
    }
    .alts-popover .alt-row {
      display: block; width: 100%; text-align: left; padding: .35rem .5rem;
      border: none; background: none; border-radius: 6px; cursor: pointer; font-size: .85rem;
    }
    .alts-popover .alt-row:hover { background: var(--panel); }
    .alts-popover .alt-empty, .alts-popover .alt-error {
      padding: .35rem .5rem; font-size: .82rem; color: var(--faint);
    }
```

(Check `var(--border)`, `var(--card)`, `var(--panel)`, `var(--faint)`,
`var(--fg)` are already defined in this file's `:root` block near the top —
they're used elsewhere, e.g. `.rn-slot.locked` at line 147 uses
`var(--accent-2)`, so the same CSS-variable convention applies here.)

- [ ] **Step 2: Add the button to `renderSlots()`'s markup**

In `app/static/index.html`, change the `renderSlots()` template (lines
650-657) from:

```javascript
      rnGrid.innerHTML = slots.map((s, i) => `
        <div class="rn-slot ${s.locked ? 'locked' : ''}" data-i="${i}">
          <div class="idx">#${i + 1}</div>
          <input type="text" value="${escapeAttr(s.figure)}" aria-label="Chord ${i + 1}" spellcheck="false" />
          <button type="button" class="lock" data-i="${i}" title="Lock this chord when regenerating">
            ${s.locked ? '🔒 locked' : '🔓 lock'}
          </button>
        </div>`).join('');
```

to:

```javascript
      rnGrid.innerHTML = slots.map((s, i) => `
        <div class="rn-slot ${s.locked ? 'locked' : ''}" data-i="${i}">
          <div class="idx">#${i + 1}</div>
          <input type="text" value="${escapeAttr(s.figure)}" aria-label="Chord ${i + 1}" spellcheck="false" />
          <button type="button" class="lock" data-i="${i}" title="Lock this chord when regenerating">
            ${s.locked ? '🔒 locked' : '🔓 lock'}
          </button>
          <button type="button" class="alts-btn" data-i="${i}" ${s.locked ? 'disabled' : ''} title="Show valid alternatives for this chord">
            💡 alts
          </button>
        </div>`).join('');
```

- [ ] **Step 3: Add the popover open/close logic and fetch**

After the existing `rnGrid.querySelectorAll('.lock').forEach(...)` block
(lines 659-666) in `renderSlots()`, add:

```javascript
      rnGrid.querySelectorAll('.alts-btn').forEach((btn) => {
        btn.addEventListener('click', (ev) => {
          ev.stopPropagation();
          const i = parseInt(btn.dataset.i, 10);
          toggleAltsPopover(i, btn);
        });
      });
```

Add these new functions after `renderSlots()` (after its closing `}` at
line 669):

```javascript
    let openAltsPopover = null;

    function closeAltsPopover() {
      if (openAltsPopover) {
        openAltsPopover.remove();
        openAltsPopover = null;
      }
    }

    async function toggleAltsPopover(index, btn) {
      if (openAltsPopover) {
        const wasForThisSlot = openAltsPopover.dataset.i === String(index);
        closeAltsPopover();
        if (wasForThisSlot) return;
      }

      readSlotsFromDom();
      const progression = slots.map((s) => s.figure.trim());
      const locked = lockedMapFromSlots();

      const pop = document.createElement('div');
      pop.className = 'alts-popover';
      pop.dataset.i = String(index);
      pop.innerHTML = '<div class="alt-empty">Loading…</div>';
      btn.closest('.rn-slot').appendChild(pop);
      openAltsPopover = pop;

      try {
        const body = { key: genKey(), progression, index };
        if (locked) body.locked = locked;
        const cadence = genCadence();
        if (cadence) body.cadence = cadence;

        const res = await fetch('/generate/roman-alternatives', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(formatDetail(data.detail) || `HTTP ${res.status}`);

        const alts = data.alternatives || [];
        if (!alts.length) {
          pop.innerHTML = '<div class="alt-empty">No valid alternatives for this chord.</div>';
          return;
        }
        pop.innerHTML = alts.map((a) =>
          `<button type="button" class="alt-row" data-figure="${escapeAttr(a.figure)}">${escapeHtml(a.figure)} <span style="color:var(--faint)">— ${escapeHtml(a.label)}</span></button>`
        ).join('');
        pop.querySelectorAll('.alt-row').forEach((row) => {
          row.addEventListener('click', () => {
            slots[index].figure = row.dataset.figure;
            closeAltsPopover();
            renderSlots();
          });
        });
      } catch (err) {
        pop.innerHTML = `<div class="alt-error">Could not load alternatives.</div>`;
      }
    }

    document.addEventListener('click', (ev) => {
      if (openAltsPopover && !openAltsPopover.contains(ev.target) && !ev.target.closest('.alts-btn')) {
        closeAltsPopover();
      }
    });
    document.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape') closeAltsPopover();
    });
```

Note: `closeAltsPopover()` is called at the top of `toggleAltsPopover`
before creating a new one, so clicking a different slot's `💡 alts` button
replaces rather than stacks (per spec). Clicking the same slot's button
twice closes it (toggle). `renderSlots()` (called after picking an
alternative, and also called elsewhere e.g. after `proposeProgression()`)
fully replaces `rnGrid.innerHTML`, which implicitly removes any open
popover's DOM node — reset `openAltsPopover = null` is not strictly needed
there since a stale reference to a removed node is harmless (next
`toggleAltsPopover` call always creates a fresh element), but confirm this
in Step 4 by checking no console errors appear after Regenerate/Propose
clicks while a popover is open.

- [ ] **Step 4: Manual browser verification**

Run: `source .venv/bin/activate && uvicorn app.main:app --reload` (or the
project's existing run command), open the Generate tab:

1. Propose a progression, confirm each unlocked `.rn-slot` shows a
   `💡 alts` button, and locked slots show it disabled.
2. Click `💡 alts` on an unlocked slot — confirm a popover appears below
   it listing alternatives with labels.
3. Click an alternative — confirm the slot's input updates to that figure,
   the popover closes, and Realize still works with the edited progression.
4. Click `💡 alts` on the same slot twice — confirm it toggles closed on
   the second click.
5. Open a popover on slot A, then click `💡 alts` on slot B — confirm A's
   popover closes and B's opens (no stacking).
6. Click outside the popover, and separately press Escape while one is
   open — confirm both close it.
7. Lock a slot, confirm its `💡 alts` button is disabled and unclickable.
8. Trigger a slot with no valid alternatives if possible (e.g. a
   single-chord progression, or a heavily locked short progression) —
   confirm the popover shows "No valid alternatives for this chord"
   rather than an empty box.

Expected: all eight checks pass, no console errors.

- [ ] **Step 5: Commit**

```bash
git add app/static/index.html
git commit -m "Add per-slot Roman-numeral alternatives popover to the RN editor"
```

---

## Self-Review Notes

- **Spec coverage:** `roman_alternatives_for_slot` with full-progression
  theory validation (Task 1), `POST /generate/roman-alternatives` endpoint
  + models + error handling (Task 2), `💡 alts` button/popover/click-to-swap/
  locked-disabled/empty-state/close-on-outside-click-or-Escape (Task 3) —
  matches every requirement in
  `docs/superpowers/specs/2026-07-22-roman-numeral-alternatives-design.md`.
- **Placeholder scan:** none — all steps have concrete code, including the
  exact expected alternative list for the test progression (verified
  against the real codebase during planning, not guessed).
- **Type consistency:** `roman_alternatives_for_slot` returns
  `List[Dict[str, str]]` with `{"figure": str, "label": str}` keys
  end-to-end — matches `RomanAlternative` (Task 2) and the frontend's
  `a.figure` / `a.label` access (Task 3).
- **Non-goals honored:** no engine/melody involvement anywhere (all
  `validate_progression` calls use `check_engine=False`); no auto-Realize
  after picking an alternative (only `renderSlots()` is called, matching
  manual-edit behavior); no multi-slot joint suggestion (one `index` per
  request, repeatable per slot).
