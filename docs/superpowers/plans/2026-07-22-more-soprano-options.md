# More Soprano Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user fetch more than the default 3 soprano-line options for
the same progression via a "More options" action in the Generate tab, instead
of being stuck with only 3.

**Architecture:** Parameterize the already-deterministic
`soprano_alternatives()` search with an existing-but-unexposed `n` argument
via a new bounded `count` field on `SopranoOptionsRequest`. No new endpoint,
no algorithm change. The frontend re-fetches with a larger `count` and
appends the new options, using the function's documented prefix-stability
guarantee (same progression/key → first N options are always a prefix of a
larger-N request) to safely replace the in-memory list wholesale.

**Tech Stack:** FastAPI + Pydantic (backend), vanilla JS in `app/static/index.html` (frontend), pytest + `fastapi.testclient.TestClient` (tests).

## Global Constraints

- `count` must be bounded `ge=1, le=10` (spec: 10 is a sane ceiling, well
  past what the UI shows, guarding against unbounded `_best_path` re-runs).
- Default `count` is `3` — do not change the default number of options shown
  when "More options" isn't clicked.
- No change to `soprano_alternatives()` itself (`app/generation/realize.py`)
  or to the candidate-pruning algorithm.
- No new endpoint — reuse `POST /generate/soprano-options`.

---

### Task 1: Backend — `count` field on the request model

**Files:**
- Modify: `app/models.py:170-192` (`SopranoOptionsRequest`)
- Test: `tests/test_generate_endpoint.py` (append near line 131, after
  `test_soprano_options_chosen_option_feeds_generate_successfully`)

**Interfaces:**
- Produces: `SopranoOptionsRequest.count: int` (default `3`, `ge=1`, `le=10`),
  consumed by Task 2's endpoint change.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate_endpoint.py`:

```python
def test_soprano_options_count_returns_more_options():
    # This progression has enough chord-tone variety that count=6 finds
    # more distinct soprano lines than the count=3 default.
    prog = ["I", "IV", "V", "I", "vi", "IV", "V", "I"]
    resp3 = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": prog, "count": 3},
    )
    resp6 = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": prog, "count": 6},
    )
    assert resp3.status_code == 200, resp3.text
    assert resp6.status_code == 200, resp6.text
    opts3 = resp3.json()["options"]
    opts6 = resp6.json()["options"]
    assert len(opts6) >= len(opts3)
    # Prefix guarantee: the first len(opts3) entries of the count=6
    # response must equal the count=3 response exactly.
    assert opts6[: len(opts3)] == opts3


def test_soprano_options_default_count_is_three():
    resp = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": ["I", "IV", "V", "I"]},
    )
    assert resp.status_code == 200, resp.text
    assert 0 < len(resp.json()["options"]) <= 3


def test_soprano_options_count_out_of_bounds_returns_422():
    resp_zero = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": ["I", "V", "I"], "count": 0},
    )
    assert resp_zero.status_code == 422, resp_zero.text

    resp_high = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": ["I", "V", "I"], "count": 11},
    )
    assert resp_high.status_code == 422, resp_high.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_generate_endpoint.py -k "count" -v`

Expected: `test_soprano_options_count_out_of_bounds_returns_422` and
`test_soprano_options_default_count_is_three` PASS already (default
behavior unaffected), but `test_soprano_options_count_returns_more_options`
FAILS with a 422 (`count` is not yet a recognized field, so pydantic will
either ignore it silently — check actual behavior) — run this first to
confirm the exact failure mode before writing the implementation.

- [ ] **Step 3: Add the `count` field**

In `app/models.py`, inside `SopranoOptionsRequest` (currently lines
170–191), add the field after the `progression` field/validator and before
`model_config`:

```python
    count: int = Field(
        3,
        ge=1,
        le=10,
        description=(
            "Number of distinct soprano-line options to return "
            "(default 3, max 10)."
        ),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_generate_endpoint.py -k "count" -v`

Expected: all three PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_generate_endpoint.py
git commit -m "Add bounded count field to SopranoOptionsRequest"
```

---

### Task 2: Backend — wire `count` through the endpoint

**Files:**
- Modify: `app/main.py:217-241` (`generate_soprano_options`)

**Interfaces:**
- Consumes: `SopranoOptionsRequest.count` from Task 1.
- Consumes: `soprano_alternatives(progression, key, n=...)` from
  `app/generation/realize.py:120` (already exists, unchanged).

- [ ] **Step 1: Update the endpoint body**

In `app/main.py`, inside `generate_soprano_options` (line 223-224), change:

```python
        options = soprano_alternatives(body.progression, body.key, n=3)
```

to:

```python
        options = soprano_alternatives(body.progression, body.key, n=body.count)
```

- [ ] **Step 2: Run the full endpoint test file**

Run: `source .venv/bin/activate && python -m pytest tests/test_generate_endpoint.py -v`

Expected: all tests PASS, including the three from Task 1 (this task makes
`test_soprano_options_count_returns_more_options` actually exercise the
real `n=6` search path rather than a hardcoded `n=3`).

- [ ] **Step 3: Run the full test suite to check for regressions**

Run: `source .venv/bin/activate && python -m pytest tests/ -q`

Expected: all tests PASS (same count as before this plan, plus the 3 new
ones from Task 1).

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "Pass count through to soprano_alternatives in the endpoint"
```

---

### Task 3: Frontend — "More options" button and state

**Files:**
- Modify: `app/static/index.html`
  - CSS: near `.soprano-options` rule (line 236)
  - JS state: near `let sopranoOptions = [];` (line 566)
  - JS: `renderSopranoOptions()` (lines 731-760)
  - JS: `realizeProgression()` (lines 762-791) — reset the new state
  - JS: `finalizeRealization()` template (lines 815-836) — add the button's
    container markup

**Interfaces:**
- Consumes: `POST /generate/soprano-options` with `count` (Tasks 1-2).
- Consumes existing `sopranoOptions` array, `selectedSopranoIndex`, `genKey()`,
  `$()` helper, `escapeHtml()`, `setGenStatus()` — all already defined
  elsewhere in this file.

No backend/JS test framework exists for this file (per `AGENT-START-HERE.md`
— "Needs Python 3.11+" and pytest is the only test runner in this repo), so
this task is verified manually in a browser per Step 5.

- [ ] **Step 1: Add CSS for the button/note**

Near line 236 (`.soprano-options { ... }`), add:

```css
    .soprano-more { margin: 0 0 1rem; display: flex; align-items: center; gap: .6rem; }
    .soprano-more-note { color: var(--faint); font-size: .85rem; }
```

- [ ] **Step 2: Add state variables**

Near line 566-567 (`let sopranoOptions = [];` / `let selectedSopranoIndex = 0;`), add:

```javascript
    let sopranoOptionsExhausted = false;
```

- [ ] **Step 3: Add the button/note markup and fetch-more logic**

In `finalizeRealization()`'s template (around line 825-826), change:

```html
          <div class="section-title"><h2>Soprano options</h2><span class="count">${sopranoOptions.length}</span></div>
          <div class="soprano-options" id="sopranoOptions"></div>
```

to:

```html
          <div class="section-title"><h2>Soprano options</h2><span class="count">${sopranoOptions.length}</span></div>
          <div class="soprano-options" id="sopranoOptions"></div>
          <div class="soprano-more">
            <button type="button" class="btn" id="btnMoreSoprano">More options</button>
            <span class="soprano-more-note" id="sopranoMoreNote" hidden>No more distinct soprano lines for this progression.</span>
          </div>
```

After the existing `renderSopranoOptions();` call in `finalizeRealization()`
(line 838), add the button's click handler (re-attached each render, since
`genResults.innerHTML` is replaced wholesale on every `finalizeRealization()`
call — same pattern already used for `btnDownload`/`btnPlay`/`btnStop` at
lines 839-841):

```javascript
        $('btnMoreSoprano').addEventListener('click', fetchMoreSopranoOptions);
        $('btnMoreSoprano').disabled = sopranoOptionsExhausted;
        $('sopranoMoreNote').hidden = !sopranoOptionsExhausted;
```

Add a new function, placed directly after `renderSopranoOptions()` (after
line 760):

```javascript
    async function fetchMoreSopranoOptions() {
      const progression = slots.map((s) => s.figure.trim()).filter(Boolean);
      const nextCount = sopranoOptions.length + 3;
      const btn = $('btnMoreSoprano');
      const note = $('sopranoMoreNote');
      if (btn) btn.disabled = true;

      try {
        const res = await fetch('/generate/soprano-options', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: genKey(), progression, count: nextCount }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(formatDetail(data.detail) || `HTTP ${res.status}`);

        const newOptions = data.options || [];
        if (newOptions.length > sopranoOptions.length) {
          sopranoOptions = newOptions;
          $('genResults').querySelector('.count').textContent = String(sopranoOptions.length);
          renderSopranoOptions();
          if (btn) btn.disabled = false;
          if (note) note.hidden = true;
        } else {
          sopranoOptionsExhausted = true;
          if (btn) btn.disabled = true;
          if (note) note.hidden = false;
        }
      } catch (err) {
        setGenStatus(`Error: ${err.message}`, true);
        if (btn) btn.disabled = sopranoOptionsExhausted;
      }
    }
```

Note: `$('genResults').querySelector('.count')` targets the "Soprano
options" section's count badge specifically — `finalizeRealization()`'s
template has two `.count` spans (Progression and Soprano options); confirm
in Step 5 that the selector needs scoping to the correct one (e.g. give the
soprano count badge an `id="sopranoOptionsCount"` instead, to avoid
ambiguity — see Step 4).

- [ ] **Step 4: Disambiguate the count badge**

Since `genResults.innerHTML` has two `<span class="count">` elements
(Progression's and Soprano options'), replace the plain class selector with
an id. In the template from Step 3, change:

```html
          <div class="section-title"><h2>Soprano options</h2><span class="count">${sopranoOptions.length}</span></div>
```

to:

```html
          <div class="section-title"><h2>Soprano options</h2><span class="count" id="sopranoOptionsCount">${sopranoOptions.length}</span></div>
```

and in `fetchMoreSopranoOptions()`, change:

```javascript
          $('genResults').querySelector('.count').textContent = String(sopranoOptions.length);
```

to:

```javascript
          $('sopranoOptionsCount').textContent = String(sopranoOptions.length);
```

- [ ] **Step 5: Reset state on fresh Realize**

In `realizeProgression()` (lines 762-791), next to the existing
`sopranoOptions = []; selectedSopranoIndex = 0;` (lines 772-773), add:

```javascript
      sopranoOptionsExhausted = false;
```

- [ ] **Step 6: Manual browser verification**

Run: `source .venv/bin/activate && uvicorn app.main:app --reload` (or the
project's existing run command — check `docs/AGENT-START-HERE.md` /
`README.md` if `uvicorn` isn't it), then open the Generate tab in a browser:

1. Propose a progression of length 8 (enough chord-tone variety), Realize.
2. Confirm the default 3 soprano-option cards render, with a "More
   options" button beneath them.
3. Click "More options" — confirm the card row grows (more cards appended,
   existing 3 unchanged/still in the same order) and the section's count
   badge updates.
4. Click "More options" repeatedly until the search is exhausted — confirm
   the button becomes disabled and the "No more distinct soprano lines for
   this progression" note appears.
5. Click a card (selection), confirm re-finalize still works as before.
6. Click "Propose progression" again (fresh progression) and Realize —
   confirm the button re-enables and the note disappears (state reset).

Expected: all six checks pass. If step 3's card append looks wrong (e.g.
duplicate cards, wrong count), re-check Step 4's id disambiguation and the
`renderSopranoOptions()` full-replace logic (it already does
`container.innerHTML = sopranoOptions.map(...)`, so a full re-render from
the new full list is correct and doesn't need diffing).

- [ ] **Step 7: Commit**

```bash
git add app/static/index.html
git commit -m "Add More options button to fetch additional soprano-line alternatives"
```

---

## Self-Review Notes

- **Spec coverage:** backend `count` field + bound (Task 1), endpoint
  pass-through (Task 2), frontend button/fetch/replace/exhaustion/reset
  (Task 3) all covered — matches every requirement in
  `docs/superpowers/specs/2026-07-22-more-soprano-options-design.md`.
- **Placeholder scan:** none — all steps have concrete code.
- **Type consistency:** `count` is `int` end-to-end (Pydantic field →
  JS `nextCount` integer → JSON body); `sopranoOptions` stays
  `{soprano: number[], pitches: string[]}[]` throughout, matching the
  existing declared shape at line 565-566.
