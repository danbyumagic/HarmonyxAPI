# Agent instructions for this repository

Read this before doing any work here. Applies to any AI coding agent
(Claude Code, Codex, or otherwise).

## Rule 1: Ask before big spends

Before starting a large continuous task — implementing a full milestone
end-to-end, running many rounds of iterative debugging, or reading/writing
several large files in one sitting — **stop and explicitly ask the user for
confirmation first.** Do not assume permission to burn a large amount of
token/usage budget in one uninterrupted run. This project already learned
this lesson the expensive way once — see `docs/AI-DIARY.md` for the story.
Don't repeat it.

## Rule 2: Work in small, self-contained chunks

Prefer narrow, well-specified tasks with a clear "done" condition (e.g. "this
specific test file passes," "this specific function is implemented") over
broad, open-ended ones like "continue the plan." If a task naturally spans
multiple pieces, stop between pieces and check in with the user rather than
running straight through.

An implementer working one narrow chunk does not need — and should not read —
the full project history to do that chunk correctly. But the person or agent
assigning chunks (the one with full context) is responsible for explicitly
thinking through where chunks touch each other ("the seams"), because bugs at
a seam are invisible to any agent that only ever sees one side of it. Don't
assume "my piece passed its own tests" means the integration is correct.

## Rule 3: Read before you write

Before touching code, read (in this order):

1. `docs/START-HERE.md` — plain-language project status (fastest orientation,
   read this first even as an AI)
2. `docs/STATUS.md` — technical current-state snapshot
3. `docs/IMPLEMENTATION-PLAN.md` — the build plan
4. `docs/PARTWRITING-RULES.md` — the locked rule spec for the generator (if
   working on generation)
5. `docs/AI-DIARY.md` — chronological log with reasoning and gotchas (at
   least the most recent entries)

## Rule 4: Don't edit locked fixtures

`tests/test_partwriting.py` is a locked spec — implement code to satisfy it,
never edit it to match an implementation. See `docs/PARTWRITING-RULES.md` for
why this matters (agent-independent correctness).

## Rule 5: Commit discipline

This project runs in an ephemeral environment — uncommitted work can be lost
if a session ends. Commit and push at natural stopping points along the way,
not only at the very end of a long task.
