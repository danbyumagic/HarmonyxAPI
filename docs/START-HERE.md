# Start here (read this first)

You're picking this project back up. This file exists because the AI works
fast and it's easy to lose track of where things stand. No jargon, no code —
just the facts, kept short on purpose.

## What is this project?

**Harmonyx API** — a tool that does two things:
1. **Analyze** — feed it sheet music, it tells you the chords / Roman numerals.
2. **Generate** *(being built now)* — feed it a chord progression, it writes
   an actual four-part hymn (like a Bach chorale) that follows the real rules
   of harmony.

## Where things stand right now

- **Part 1 (analyze) is done and deployed.** Working API, tests passing, a
  live pull request (#1) open on GitHub, CI green.
- **Part 2 (generate) is in progress, NOT done.** We're building the
  "part-writing engine" — the piece that turns a chord progression into real
  four-voice music that obeys the actual rules (no parallel fifths, the
  leading tone resolves correctly, etc.).

## What got built this session

- The real rules of good four-part writing were turned into a **locked,
  do-not-edit test file** (`tests/test_partwriting.py`) — think of it as an
  answer key. Any code has to match it; nothing (AI or human) gets to cut
  corners on the music theory.
- Code that spells out chords, builds valid four-voice arrangements, checks
  the rules, and generates a working four-part piece — **and it works.** A
  live test produced a genuinely good-sounding I–IV–V–I progression with
  zero rule violations, on its own, without hand-tuning.
- This is now **committed and pushed to GitHub** (that just happened, as a
  safety step, since this working environment can disappear between
  sessions).

## What's broken / not done

- **One known, small bug:** when you hand the generator a specific top
  melody note, it doesn't always check that note actually belongs to the
  chord. It's isolated and already understood — just not fixed yet.
- Nothing else is broken. Everything else that was tested, passed.

## Why this session burned so much budget

Building this in one long, continuous sitting made the conversation very
long — and long conversations get expensive to keep talking in, because
every new message re-reads the *entire* history so far. That's the main
lesson, and it's why things changed for what happens next.

## What happens next

1. This chat **stops here** — no more new work in this conversation.
2. The next session should start **fresh**, with a **short, specific task**
   handed to it — not "continue the whole plan."
3. There's now a rule file, `AGENTS.md`, at the repo root that requires any
   AI working on this project to check in with you before doing a large
   chunk of work — specifically to stop this from happening again.

## If you're starting a new chat, paste this in

> Read `docs/START-HERE.md`, `AGENTS.md`, and the most recent entry in
> `docs/AI-DIARY.md` first. Then stop and wait for my instructions — do not
> start implementing anything yet.

## Where to look for more detail (optional, not required reading)

- `docs/STATUS.md` — technical snapshot of the whole project
- `docs/IMPLEMENTATION-PLAN.md` — the build plan, milestone by milestone
- `docs/PARTWRITING-RULES.md` — the locked rule spec for the generator
- `docs/AI-DIARY.md` — full chronological log, written by/for AI assistants
