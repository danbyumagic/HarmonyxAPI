# Soprano Alternatives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After clicking Realize in the Generate tab, show up to 3 distinct soprano-line options for the current progression, so users aren't stuck with a single deterministic melody.

**Architecture:** A new `soprano_alternatives()` function re-runs the existing Viterbi/DP search (`_best_path` in `app/generation/realize.py`) up to 3 times, excluding previously-used soprano pitches per beat between runs. A new lightweight `POST /generate/soprano-options` endpoint exposes this (pitch lists only, no MusicXML). The frontend fetches previews, auto-finalizes option 1 via the existing `POST /generate` (unchanged), and lets the user swap to a different option by re-calling `POST /generate` with that option's `soprano` array (an existing, already-supported parameter).

**Tech Stack:** Python 3.12 / FastAPI / music21 / pydantic (backend, unchanged); vanilla JS + Web Audio (frontend, unchanged).

## Global Constraints

- Python 3.11+ required (`.python-version` pins 3.12.12) — music21 10.5.0's floor.
- `tests/test_partwriting.py` is locked — never edit it. This plan doesn't touch it, but `Voicing`'s field order/constructor (`Voicing(s, a, t, b)`) is fixed by it and must not change.
- Reuse `_best_path` and `rules.transition_cost` unchanged — no new cost model, per the approved spec's "candidate pruning + re-run" decision (not true k-best Viterbi, not randomized sampling).
- Option count is hardcoded at 3 for this iteration (YAGNI, per spec) — no new config surface.
- `app/generation/*` modules must stay FastAPI/HTTP-free (existing convention, stated in `realize.py`'s module docstring) — HTTP-facing conversions (MIDI→pitch name, request/response shaping) belong in `app/models.py` / `app/main.py`, not in `app/generation/`.
- Run `source .venv/bin/activate` before any `python`/`pytest` command in this repo (the project venv; created at `.venv/` in the repo root).

---

### Task 1: `soprano_alternatives()` core function

**Files:**
- Modify: `app/generation/realize.py` — insert new function after `realize()` (currently ends at line 117 with `return _build_score(voicings, key_like, time_signature)`, followed by two blank lines then `DEFAULT_PLAYBACK_TEMPO_BPM = 75` at line 120). Insert the new function between the blank lines and that constant.
- Modify: `tests/test_generation_realize.py` — add `soprano_alternatives` to the existing `from app.generation.realize import (...)` block (currently lines 13-19), append new tests at the end of the file (currently ends at line 132 with `test_check_soprano_length_mismatch_raises`).
- Test: `tests/test_generation_realize.py`

**Interfaces:**
- Consumes: `_best_path(progression, candidate_lists, contexts)` (existing, `app/generation/realize.py:144`), `candidate_voicings(figure, key_like)` (existing, `app/generation/voicing.py:59`), `Voicing` (existing, has `.s .a .t .b` int fields), `RealizationError` (existing exception class).
- Produces: `soprano_alternatives(progression: List[str], key_like: _chords.KeyLike, n: int = 3) -> List[List[int]]` — later tasks (the API endpoint) call this directly.

- [ ] **Step 1: Write the failing tests**

Add `soprano_alternatives` to the import block at the top of `tests/test_generation_realize.py`:

```python
from app.generation.realize import (
    RealizationError,
    check_soprano,
    path_violations,
    realize,
    satb_voicings_from_score,
    soprano_alternatives,
)
```

Append these tests at the end of `tests/test_generation_realize.py`:

```python
# --- soprano_alternatives -----------------------------------------------


def test_soprano_alternatives_first_option_matches_realize_default():
    # Option 1 must be byte-for-byte what realize() already produces today
    # -- anyone who ignores the new options sees no behavior change.
    progression = ["I", "IV", "V", "I"]
    score = realize(progression, KEY)
    expected_soprano = [v.s for v in satb_voicings_from_score(score)]

    options = soprano_alternatives(progression, KEY)

    assert options[0] == expected_soprano


def test_soprano_alternatives_returns_distinct_options():
    progression = ["I", "IV", "V", "I"]
    options = soprano_alternatives(progression, KEY, n=3)

    assert len(options) >= 2
    assert all(len(o) == len(progression) for o in options)
    assert len(set(tuple(o) for o in options)) == len(options)  # all distinct


def test_soprano_alternatives_degrades_gracefully_past_available_options():
    # Requesting far more options than actually exist must never error or
    # loop forever -- it should just stop once no new distinct line is found.
    progression = ["I", "IV", "V", "I"]
    options = soprano_alternatives(progression, KEY, n=50)

    assert 0 < len(options) <= 50
    assert len(set(tuple(o) for o in options)) == len(options)


def test_soprano_alternatives_raises_on_empty_progression():
    with pytest.raises(RealizationError):
        soprano_alternatives([], KEY)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_generation_realize.py -k soprano_alternatives -v`

Expected: `ImportError: cannot import name 'soprano_alternatives'` (collection error) — confirms the tests exercise code that doesn't exist yet, not a typo.

- [ ] **Step 3: Implement `soprano_alternatives`**

Insert into `app/generation/realize.py`, between `realize()`'s closing `return _build_score(...)` line and the `DEFAULT_PLAYBACK_TEMPO_BPM = 75` constant:

```python
def soprano_alternatives(
    progression: List[str], key_like: _chords.KeyLike, n: int = 3
) -> List[List[int]]:
    """Up to ``n`` distinct soprano lines (MIDI ints, one per chord) for
    ``progression``, ranked by voice-leading cost, most preferred first.

    Generated by candidate pruning + re-run, not true k-best Viterbi: the
    first entry is exactly what ``realize()``'s own best-path search
    produces. Each subsequent entry re-runs the same Viterbi search after
    excluding, at each beat, any soprano pitch already used by an earlier
    entry -- unless that would leave a beat with zero candidates, in which
    case that beat's full pool is kept instead. Stops early (returning
    fewer than ``n``) if a re-run reproduces an already-found soprano line,
    or if pruning makes no rule-legal path exist at all -- both are
    expected outcomes on short or harmonically constrained progressions,
    not errors.

    Raises ``RealizationError`` if ``progression`` is empty, or if the
    *first* (unpruned) search fails -- i.e. under exactly the same
    conditions ``realize()`` itself would raise.
    """
    if not progression:
        raise RealizationError("progression must not be empty")

    contexts = [
        {
            "key": key_like,
            "prev_roman": progression[i - 1] if i > 0 else None,
            "cur_roman": figure,
        }
        for i, figure in enumerate(progression)
    ]

    full_pools: List[List[Voicing]] = []
    for i, figure in enumerate(progression):
        pool = candidate_voicings(figure, key_like)
        if not pool:
            raise RealizationError(f"no legal voicings for chord {i} ('{figure}')")
        full_pools.append(pool)

    excluded: List[set] = [set() for _ in progression]
    seen: set = set()
    results: List[List[int]] = []

    for attempt in range(n):
        candidate_lists = [
            [v for v in full_pools[i] if v.s not in excluded[i]] or full_pools[i]
            for i in range(len(progression))
        ]
        try:
            path = _best_path(progression, candidate_lists, contexts)
        except RealizationError:
            if attempt == 0:
                raise
            break

        soprano_line = tuple(v.s for v in path)
        if soprano_line in seen:
            break
        seen.add(soprano_line)
        results.append(list(soprano_line))
        for i, v in enumerate(path):
            excluded[i].add(v.s)

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_generation_realize.py -v`

Expected: all tests in the file PASS (existing tests plus the 4 new ones), no regressions.

- [ ] **Step 5: Run the full suite and commit**

Run: `source .venv/bin/activate && python -m pytest tests/ -q`

Expected: all tests pass (171 existing + 4 new = 175; count may drift slightly, that's fine as long as none fail).

```bash
git add app/generation/realize.py tests/test_generation_realize.py
git commit -m "Add soprano_alternatives: N distinct soprano lines via candidate pruning + re-run"
```

---

### Task 2: `midi_to_name` helper

**Files:**
- Modify: `app/generation/chords.py` — add helper function after `to_key()` (currently ends at line 26 with `return m21key.Key(tonic, mode)`, followed by a blank line then `def tonic_pitch_class` at line 29).
- Modify: `tests/test_generation_chords.py` — add `midi_to_name` to the existing import block (currently lines 5-13), append one test at the end of the file.
- Test: `tests/test_generation_chords.py`

**Interfaces:**
- Consumes: `music21.pitch` (already imported in `chords.py` as `m21pitch`).
- Produces: `midi_to_name(midi: int) -> str` — Task 3 (the API endpoint) imports and calls this to build the `pitches` field in the response.

- [ ] **Step 1: Write the failing test**

Add `midi_to_name` to the import block at the top of `tests/test_generation_chords.py`:

```python
from app.generation.chords import (
    chord_members,
    chord_pitch_classes,
    is_chord_tone,
    leading_tone_pitch_class,
    midi_to_name,
    normalize_rn,
    rn_agreement,
    tonic_pitch_class,
)
```

Append at the end of `tests/test_generation_chords.py`:

```python
def test_midi_to_name_returns_pitch_name_with_octave():
    assert midi_to_name(72) == "C5"
    assert midi_to_name(61) == "C#4"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/test_generation_chords.py -k midi_to_name -v`

Expected: `ImportError: cannot import name 'midi_to_name'`.

- [ ] **Step 3: Implement `midi_to_name`**

Insert into `app/generation/chords.py`, right after `to_key()`'s closing `return m21key.Key(tonic, mode)` line:

```python
def midi_to_name(midi: int) -> str:
    """MIDI pitch number -> spelled pitch name with octave (e.g. 72 -> 'C5')."""
    return m21pitch.Pitch(midi=midi).nameWithOctave
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest tests/test_generation_chords.py -v`

Expected: all tests in the file PASS.

- [ ] **Step 5: Commit**

```bash
git add app/generation/chords.py tests/test_generation_chords.py
git commit -m "Add midi_to_name helper for MIDI-to-pitch-name conversion"
```

---

### Task 3: `POST /generate/soprano-options` endpoint

**Files:**
- Modify: `app/models.py` — add 3 new pydantic models after `GenerateResponse` (currently ends at line 167 with the closing `}` of its `model_config`, immediately followed by `class ProgressionRequest` at line 170). Insert the new models between them.
- Modify: `app/main.py` — add `soprano_alternatives` to the `from .generation.realize import (...)` block (currently lines 23-30); add `from .generation.chords import midi_to_name` as a new import line; add `SopranoOptionsRequest, SopranoOptionsResponse` to the `from .models import (...)` block (currently lines 31-38); add the new endpoint function after `generate()` (currently ends at line 205 with `return GenerateResponse(...)`, followed by a blank line then `@app.get("/health", ...)` at line 208).
- Test: `tests/test_generate_endpoint.py`

**Interfaces:**
- Consumes: `soprano_alternatives(progression, key_like, n=3)` (Task 1), `midi_to_name(midi)` (Task 2), `RealizationError` (existing).
- Produces: `POST /generate/soprano-options` HTTP endpoint — Task 4 (frontend) calls this by URL, no Python-level interface.

- [ ] **Step 1: Write the failing tests**

Append at the end of `tests/test_generate_endpoint.py`:

```python
# --- POST /generate/soprano-options -----------------------------------


def test_soprano_options_happy_path_returns_up_to_three_options():
    resp = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": ["I", "IV", "V", "I"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    options = data["options"]
    assert 0 < len(options) <= 3
    for opt in options:
        assert len(opt["soprano"]) == 4
        assert len(opt["pitches"]) == 4
        assert all(isinstance(p, int) for p in opt["soprano"])
        assert all(isinstance(p, str) for p in opt["pitches"])


def test_soprano_options_first_option_pitches_match_soprano_midis():
    resp = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": ["I", "V", "I"]},
    )
    assert resp.status_code == 200, resp.text
    first = resp.json()["options"][0]
    # e.g. soprano=[72, 71, 72] -> pitches=["C5", "B4", "C5"]
    assert first["pitches"][0] in ("C5",)  # tonic-triad soprano options include C5
    assert len(first["pitches"]) == len(first["soprano"])


def test_soprano_options_chosen_option_feeds_generate_successfully():
    # The whole point of the split endpoint: an option's soprano array must
    # be directly usable as POST /generate's soprano param.
    options_resp = client.post(
        "/generate/soprano-options",
        json={"key": "C major", "progression": ["I", "IV", "V", "I"]},
    )
    chosen = options_resp.json()["options"][-1]["soprano"]

    gen_resp = client.post(
        "/generate",
        json={
            "key": "C major",
            "progression": ["I", "IV", "V", "I"],
            "soprano": chosen,
        },
    )
    assert gen_resp.status_code == 200, gen_resp.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_generate_endpoint.py -k soprano_options -v`

Expected: FAIL with `404 Not Found` for the new endpoint (route doesn't exist yet).

- [ ] **Step 3: Add the pydantic models**

Insert into `app/models.py`, between `GenerateResponse`'s closing `model_config` brace (line 167) and `class ProgressionRequest` (line 170):

```python
class SopranoOptionsRequest(BaseModel):
    """Body for ``POST /generate/soprano-options``."""

    key: str = Field(..., description="Key, e.g. 'C major' or 'A minor'.", examples=["C major"])
    progression: List[str] = Field(
        ...,
        min_length=1,
        description="Roman-numeral figures in order, e.g. ['I', 'IV', 'V', 'I'].",
    )

    @field_validator("progression")
    @classmethod
    def _figures_nonempty(cls, value: List[str]) -> List[str]:
        if any(not (f and str(f).strip()) for f in value):
            raise ValueError("progression figures must be non-empty strings")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {"key": "C major", "progression": ["I", "IV", "V", "I"]}
        }
    }


class SopranoOption(BaseModel):
    soprano: List[int] = Field(..., description="MIDI pitches, one per chord.")
    pitches: List[str] = Field(..., description="Same pitches as spelled names, e.g. 'C5'.")


class SopranoOptionsResponse(BaseModel):
    """Up to 3 distinct soprano-line options, best (lowest-cost) first."""

    options: List[SopranoOption]

    model_config = {
        "json_schema_extra": {
            "example": {
                "options": [
                    {"soprano": [72, 72, 71, 72], "pitches": ["C5", "C5", "B4", "C5"]},
                    {"soprano": [64, 65, 62, 64], "pitches": ["E4", "F4", "D4", "E4"]},
                ]
            }
        }
    }
```

- [ ] **Step 4: Add the endpoint**

In `app/main.py`, update the `from .generation.realize import (...)` block (lines 23-30) to add `soprano_alternatives`:

```python
from .generation.realize import (
    DEFAULT_PLAYBACK_TEMPO_BPM,
    RealizationError,
    check_soprano,
    playback_from_voicings,
    realize,
    satb_voicings_from_score,
    soprano_alternatives,
)
```

Add a new import line right after it:

```python
from .generation.chords import midi_to_name
```

Update the `from .models import (...)` block (lines 31-38) to add the two new response/request models:

```python
from .models import (
    AnalysisResponse,
    GenerateRequest,
    GenerateResponse,
    PlaybackPayload,
    ProgressionRequest,
    ProgressionResponse,
    SopranoOptionsRequest,
    SopranoOptionsResponse,
)
```

Insert the new endpoint after `generate()`'s closing `return GenerateResponse(...)` (line 205), before `@app.get("/health", ...)` (line 208):

```python
@app.post(
    "/generate/soprano-options",
    response_model=SopranoOptionsResponse,
    tags=["generation"],
)
async def generate_soprano_options(body: SopranoOptionsRequest) -> SopranoOptionsResponse:
    """Up to 3 distinct soprano-line options for a progression, best first.

    Lightweight preview (pitches only, no MusicXML) -- finalize a chosen
    option into a full score via ``POST /generate``'s ``soprano`` param.
    """
    try:
        options = soprano_alternatives(body.progression, body.key, n=3)
    except RealizationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "realization_failed", "message": str(exc)},
        ) from exc
    except Exception as exc:  # music21 / RN parse failures, etc.
        raise HTTPException(
            status_code=422,
            detail={"error": "realization_failed", "message": str(exc)},
        ) from exc

    return SopranoOptionsResponse(
        options=[
            {"soprano": s, "pitches": [midi_to_name(m) for m in s]}
            for s in options
        ]
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_generate_endpoint.py -v`

Expected: all tests in the file PASS, including the 3 new ones.

- [ ] **Step 6: Run the full suite, eval gates, and commit**

Run:
```bash
source .venv/bin/activate
python -m pytest tests/ -q
python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0
```

Expected: all tests pass; generation eval still 100% round-trip / 0 violations (this task doesn't touch the DP cost model, so no regression is expected there).

```bash
git add app/models.py app/main.py tests/test_generate_endpoint.py
git commit -m "Add POST /generate/soprano-options endpoint"
```

---

### Task 4: Frontend — show soprano options after Realize

**Files:**
- Modify: `app/static/index.html` — CSS additions near the existing `.rn-slot` rules (around line 147-159); JS changes inside `realizeProgression()` (currently lines 715-774) and a few new small functions near it.

**Interfaces:**
- Consumes: `POST /generate/soprano-options` (Task 3, returns `{options: [{soprano: [int], pitches: [str]}]}`), `POST /generate` (existing, unchanged).
- Produces: nothing consumed elsewhere — this is the final, user-facing task.

This task has no automated test (the project has no JS test suite; existing frontend features like the Q3 spice/style controls were verified manually in-browser, and this follows the same convention). Steps end in a manual verification checklist instead of a pytest run.

- [ ] **Step 1: Add CSS for the option cards**

In `app/static/index.html`, add this block right after the existing `.cad.deceptive .dot { background: #c9922e; }` rule (added in a previous session; search for `.cad.deceptive` to find it) -- or anywhere in the `<style>` block near `.rn-slot`:

```css
.soprano-options { display: flex; gap: .6rem; flex-wrap: wrap; margin: .6rem 0 1rem; }
.soprano-option {
  display: inline-flex; align-items: center; gap: .5rem; border-radius: 10px;
  padding: .5rem .75rem; border: 1px solid var(--border); background: var(--card);
  cursor: pointer; font-size: .82rem;
}
.soprano-option.selected { border-color: var(--accent-2); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent-2) 40%, transparent); }
.soprano-option .notes { color: var(--faint); font-variant-numeric: tabular-nums; }
.soprano-option .play-mini {
  border: none; background: none; color: inherit; cursor: pointer; font-size: 1rem;
  line-height: 1; padding: 0;
}
```

- [ ] **Step 2: Extract a reusable `playNotes` helper from `playPlayback`**

In `app/static/index.html`, find `playPlayback()` (currently around line 810). Replace it with two functions: a generic `playNotes(events, tempoBpm)` that does the actual Web Audio work, and a thin `playPlayback()` that calls it with `lastPlayback`'s events. This is a pure refactor -- `playPlayback()`'s behavior must be identical after this step.

Replace:

```javascript
    async function playPlayback() {
      if (!lastPlayback || !lastPlayback.events || !lastPlayback.events.length) return;
      stopPlayback();

      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) {
        setGenStatus('Web Audio is not supported in this browser.', true);
        return;
      }
      if (!audioCtx) audioCtx = new AC();
      if (audioCtx.state === 'suspended') await audioCtx.resume();

      const tempo = lastPlayback.tempo_bpm || 75;
      const beatSec = 60 / tempo;
      const t0 = audioCtx.currentTime + 0.05;
      const master = audioCtx.createGain();
      master.gain.value = 0.12; // keep four voices from clipping
      master.connect(audioCtx.destination);

      let maxEnd = 0;
      for (const ev of lastPlayback.events) {
        const start = t0 + ev.beat * beatSec;
        const dur = Math.max(0.05, (ev.duration || 1) * beatSec * 0.92);
        const end = start + dur;
        if (end > maxEnd) maxEnd = end;

        const osc = audioCtx.createOscillator();
        const g = audioCtx.createGain();
        osc.type = 'triangle';
        osc.frequency.value = midiToHz(ev.midi);
        // Soft attack / release to reduce clicks
        g.gain.setValueAtTime(0, start);
        g.gain.linearRampToValueAtTime(0.9, start + 0.02);
        g.gain.setValueAtTime(0.9, end - 0.04);
        g.gain.linearRampToValueAtTime(0, end);
        osc.connect(g);
        g.connect(master);
        osc.start(start);
        osc.stop(end + 0.01);
        activeOscs.push(osc);
      }

      setPlayUi(true);
      const ms = Math.ceil((maxEnd - audioCtx.currentTime) * 1000) + 50;
      playStopTimer = setTimeout(() => {
        activeOscs = [];
        setPlayUi(false);
        playStopTimer = null;
      }, ms);
    }
```

With:

```javascript
    async function playNotes(events, tempoBpm) {
      if (!events || !events.length) return;
      stopPlayback();

      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) {
        setGenStatus('Web Audio is not supported in this browser.', true);
        return;
      }
      if (!audioCtx) audioCtx = new AC();
      if (audioCtx.state === 'suspended') await audioCtx.resume();

      const tempo = tempoBpm || 75;
      const beatSec = 60 / tempo;
      const t0 = audioCtx.currentTime + 0.05;
      const master = audioCtx.createGain();
      master.gain.value = 0.12; // keep four voices from clipping
      master.connect(audioCtx.destination);

      let maxEnd = 0;
      for (const ev of events) {
        const start = t0 + ev.beat * beatSec;
        const dur = Math.max(0.05, (ev.duration || 1) * beatSec * 0.92);
        const end = start + dur;
        if (end > maxEnd) maxEnd = end;

        const osc = audioCtx.createOscillator();
        const g = audioCtx.createGain();
        osc.type = 'triangle';
        osc.frequency.value = midiToHz(ev.midi);
        // Soft attack / release to reduce clicks
        g.gain.setValueAtTime(0, start);
        g.gain.linearRampToValueAtTime(0.9, start + 0.02);
        g.gain.setValueAtTime(0.9, end - 0.04);
        g.gain.linearRampToValueAtTime(0, end);
        osc.connect(g);
        g.connect(master);
        osc.start(start);
        osc.stop(end + 0.01);
        activeOscs.push(osc);
      }

      setPlayUi(true);
      const ms = Math.ceil((maxEnd - audioCtx.currentTime) * 1000) + 50;
      playStopTimer = setTimeout(() => {
        activeOscs = [];
        setPlayUi(false);
        playStopTimer = null;
      }, ms);
    }

    async function playPlayback() {
      if (!lastPlayback || !lastPlayback.events) return;
      await playNotes(lastPlayback.events, lastPlayback.tempo_bpm);
    }

    function playSopranoPreview(sopranoMidis, tempoBpm) {
      const events = sopranoMidis.map((midi, i) => ({ beat: i, midi, duration: 1 }));
      playNotes(events, tempoBpm);
    }
```

Note `setPlayUi` reads `!lastPlayback` to decide whether the main Play button should be enabled -- previewing a soprano-only line via `playSopranoPreview` still leaves `lastPlayback` pointing at the full realized score, so the main Play/Stop buttons keep working correctly; no change needed there.

- [ ] **Step 3: Add state for the soprano options and a render function**

Near the other `let` declarations at the top of the Generate section (around line 549-556, right after `let lastPlayback = null;`), add:

```javascript
    /** @type {{ soprano: number[], pitches: string[] }[]} */
    let sopranoOptions = [];
    let selectedSopranoIndex = 0;
```

Add a new function anywhere near `realizeProgression` (e.g. right before it):

```javascript
    function renderSopranoOptions() {
      const container = $('sopranoOptions');
      if (!container) return;
      if (!sopranoOptions.length) {
        container.innerHTML = '';
        return;
      }
      container.innerHTML = sopranoOptions.map((opt, i) => `
        <div class="soprano-option ${i === selectedSopranoIndex ? 'selected' : ''}" data-i="${i}">
          <button type="button" class="play-mini" data-i="${i}" title="Preview this soprano line" aria-label="Preview option ${i + 1}">▶</button>
          <span class="notes">${opt.pitches.map(escapeHtml).join(' · ')}</span>
        </div>`).join('');

      container.querySelectorAll('.play-mini').forEach((btn) => {
        btn.addEventListener('click', (ev) => {
          ev.stopPropagation();
          const i = parseInt(btn.dataset.i, 10);
          playSopranoPreview(sopranoOptions[i].soprano, (lastPlayback && lastPlayback.tempo_bpm) || 75);
        });
      });
      container.querySelectorAll('.soprano-option').forEach((card) => {
        card.addEventListener('click', () => {
          const i = parseInt(card.dataset.i, 10);
          if (i === selectedSopranoIndex) return;
          selectedSopranoIndex = i;
          renderSopranoOptions();
          finalizeRealization(sopranoOptions[i].soprano);
        });
      });
    }
```

- [ ] **Step 4: Split `realizeProgression` into fetch-options + finalize**

Replace the existing `realizeProgression` function (currently lines 715-774) with:

```javascript
    async function realizeProgression() {
      readSlotsFromDom();
      const progression = slots.map((s) => s.figure.trim()).filter(Boolean);
      if (!progression.length) {
        setGenStatus('Add at least one Roman numeral first.', true);
        return;
      }

      setGenStatus(`<span class="spinner"></span> Realizing four-part hymn…`);
      genResults.className = '';
      sopranoOptions = [];
      selectedSopranoIndex = 0;

      try {
        const optRes = await fetch('/generate/soprano-options', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: genKey(), progression }),
        });
        const optData = await optRes.json();
        if (optRes.ok) sopranoOptions = optData.options || [];
        // A soprano-options failure isn't fatal -- fall through and let
        // /generate below report the real error (or succeed without
        // showing alternatives).
      } catch (_) {
        sopranoOptions = [];
      }

      await finalizeRealization(sopranoOptions.length ? sopranoOptions[0].soprano : null, progression);
    }

    async function finalizeRealization(soprano, progressionOverride) {
      const progression = progressionOverride || slots.map((s) => s.figure.trim()).filter(Boolean);
      setGenStatus(`<span class="spinner"></span> Realizing four-part hymn…`);

      try {
        const body = { key: genKey(), progression, time_signature: '4/4' };
        if (soprano) body.soprano = soprano;

        const res = await fetch('/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(formatDetail(data.detail) || `HTTP ${res.status}`);

        lastMusicXml = data.musicxml;
        lastPlayback = data.playback || null;
        const chips = progression.map((f) =>
          `<span class="chip">${escapeHtml(f)}</span>`).join('');
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
          <div class="section-title"><h2>Soprano options</h2><span class="count">${sopranoOptions.length}</span></div>
          <div class="soprano-options" id="sopranoOptions"></div>
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
        $('btnDownload').addEventListener('click', downloadMusicXml);
        $('btnPlay').addEventListener('click', () => playPlayback());
        $('btnStop').addEventListener('click', () => stopPlayback());
        setGenStatus('');
        await renderOsmdPreview(lastMusicXml);
      } catch (err) {
        setGenStatus(`Error: ${err.message}`, true);
      }
    }
```

- [ ] **Step 5: Manual verification**

Start the dev server:

```bash
source .venv/bin/activate
pkill -f "uvicorn app.main:app" 2>/dev/null; sleep 1
(uvicorn app.main:app --port 8811 >/tmp/uvicorn.log 2>&1 &)
sleep 2
open -a "Google Chrome" "http://127.0.0.1:8811/"
```

In the browser, on the Generate tab:

1. Click **Propose progression**, then **Realize**.
2. Confirm the result renders exactly as before (hero, progression chips, score, Play/Stop/Download) -- no regression.
3. Confirm a new **"Soprano options"** row appears with up to 3 cards, each showing a pitch-name sequence (e.g. "C5 · C5 · B4 · C5") and a ▶ button.
4. Click a ▶ on a non-selected card: confirm you hear a short single-line melody (not the full four-voice chord).
5. Click a non-selected card itself (not the ▶): confirm the card becomes visually "selected," the score/playback/download update to match the new soprano, and the RN chips / key / tempo stay the same.
6. Click **Regenerate unlocked** / **Propose** again and re-**Realize**: confirm the soprano options refresh (don't get stuck showing the previous progression's options).
7. Open the browser console: confirm no JS errors during any of the above.

If `/generate/soprano-options` ever returns fewer than 3 options (e.g. a very short progression), confirm the UI just shows however many came back, with no broken layout or placeholder cards.

- [ ] **Step 6: Commit**

```bash
git add app/static/index.html
git commit -m "Frontend: show soprano-option previews after Realize, pick to re-finalize"
```

---

## Post-implementation

After Task 4, update `docs/START-HERE.md` / `docs/AGENT-START-HERE.md` per `AGENTS.md` Rule 2b: mark this feature done in the "Done" section, and note the docs are a good point to suggest a chat reset. This isn't a separate task -- fold it into Task 4's commit or a follow-up doc-only commit, whichever the implementer finds natural.
