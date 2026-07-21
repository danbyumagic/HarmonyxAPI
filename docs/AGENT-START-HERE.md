# Start here (for the next AI agent)

Read this file, then `AGENTS.md` at the repo root. That's it — you do not
need the full project history to do this task. This file *is* your task
brief.

## Your task, and only your task

Fix one known, already-diagnosed bug in `app/generation/voicing.py`.

**The problem:** `candidate_voicings()` accepts an optional `soprano` MIDI
pitch. When given, it should only return voicings that are actually legal —
but it never checks whether `soprano` itself is a chord tone of the Roman
numeral before building alto/tenor/bass around it. If the other three voices
can still cover the chord's remaining tones, the function returns a "valid"
voicing with a wrong note sitting in the soprano, and nothing downstream
catches it.

**The fix:** when `soprano is not None`, it must be a member of
`chord_pitch_classes(figure, key_like)` (already implemented in
`app/generation/chords.py`). If it isn't, `candidate_voicings` should behave
exactly like any other "no legal voicings" case for that chord — return `[]`
— consistent with how the rest of the module already handles that.

**Do not touch:**
- `tests/test_partwriting.py` — this is a locked spec (see `AGENTS.md` Rule 4
  and `docs/PARTWRITING-RULES.md`). Never edit it.
- `app/generation/rules.py` — this bug is a `voicing.py` issue, not a rules
  issue. You almost certainly don't need to change this file.
- Anything outside `app/generation/`. If you think you need to, **stop and
  explain why before proceeding** rather than expanding scope on your own.

## How to verify you're done

```
python -m pytest tests/ -q
```

Current state: `62 passed, 1 failed`. Your job is `63 passed, 0 failed`. The
specific test that must go from failing to passing:

```
tests/test_generation_realize.py::test_realize_incompatible_soprano_raises_realization_error
```

Do not edit that test file to make it pass — fix the implementation, not the
test. (Some other tests in that file exercise given-soprano behavior too —
make sure they still pass; the fix should only reject soprano notes that
truly aren't chord tones, not restrict legal cases.)

## When you're done

1. Commit and push with a message that references this fix.
2. **Stop.** Do not continue to the next milestone (endpoint wiring, the
   progression grammar, anything else in `docs/IMPLEMENTATION-PLAN.md`).
   Report back what you changed and wait for the next instruction. This is
   Rule 1 and Rule 2 in `AGENTS.md` — one narrow chunk, then check in.

## If it turns out to be bigger than expected

Stop and report exactly what you found instead of pushing through. If fixing
this cleanly requires touching `rules.py` or something outside
`app/generation/voicing.py`, that's a sign the scope is different than
diagnosed — surface it rather than deciding on your own to expand the task.

## Optional background (only if you want more context)

- `docs/START-HERE.md` — plain-language project overview (written for a
  human, but a quick read)
- `docs/AI-DIARY.md`, Entry 10 — the exact story of how this bug was found
  (it's a "seam bug" between `voicing.py` and `realize.py` — worth reading if
  you want to understand *why* it slipped through each module's own tests)
- `docs/PARTWRITING-RULES.md` — the full rule spec; only needed if this turns
  out to be more than a simple validation gap
