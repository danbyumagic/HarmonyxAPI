# Harmony Studio implementation plan

Prepared 2026-10-02 from `HARMONY-STUDIO-REBRAND.md` and the current frontend.
Status: planning complete; implementation has not started.

## Outcome and scope

Harmony Studio is the browser product for creating, hearing, and exploring
classical harmony. The API powers the studio and remains available as a
secondary developer feature. The release is complete when the browser
experience, developer surfaces, and current project documentation agree on
that positioning, and the existing musical workflows still work.

This plan covers the rebrand and frontend promotion end to end. It uses the
existing static frontend and FastAPI backend. It does not require a frontend
framework migration. New musical algorithms, accounts, saved projects, AI
progression generation, and a full notation editor are future product work.

Work one numbered chunk at a time. Each ends with verification, a focused
commit and push, and a user check-in before starting the next chunk, following
AGENTS.md. Do not execute the whole plan as one uninterrupted task.

## Product decisions for this release

- Name: **Harmony Studio**. Developer offering: **Harmony Studio API**.
- Tagline: “Create, hear, and explore classical harmony.”
- `/` opens the working studio directly, with **Create** selected and
  **Analyze** alongside it. A separate marketing homepage is not necessary.
- A secondary **Developers** link leads to `/demo`; `/portfolio` continues
  to serve the same developer showcase. Both offer a return link to `/`.
- `/docs` remains the interactive API reference. Existing API paths,
  request fields, response schemas, and musical defaults remain compatible.
- Keep the GitHub repository URL for this release. Historical notes retain
  the names used at the time; current product descriptions use the new name.
- Claim only implemented capabilities: SATB chorale generation, notation
  preview, basic playback, soprano alternatives, MusicXML export, and
  MusicXML/MIDI harmonic analysis. Do not market AI progression generation.

## 1. Establish the product name and navigation

Files: `app/static/index.html`, `app/static/portfolio.html`, `app/main.py`.

Update titles, visible branding, and introductory copy to Harmony Studio.
Reorder the root workspace tabs to Create then Analyze; select Create on
initial load. Make initial panel visibility and `aria-selected` match the
tab order. Preserve existing element IDs and internal mode values used by
event handlers. Update the mode-switching function only where necessary.

Give the studio a secondary Developers link. Rebrand the showcase as Harmony
Studio API and add a prominent Open Harmony Studio link. Update FastAPI's
OpenAPI title and description to explain its supporting role. Change exported
filenames to `harmony-studio_<key>.musicxml`.

Done: `/` opens Create; both tabs work; `/demo` and `/portfolio` share the new
brand and link back to the studio; `/docs` identifies Harmony Studio API.
Check the initial state, tab switching, all cross-page links, and one export.
No endpoint behavior changes are needed.

## 2. Make Create understandable as a musician's workflow

File: `app/static/index.html`.

Use “Create a four-part score” as the workspace heading. Organize the
existing controls and results around this sequence: choose settings →
suggest progression → edit/lock chords → generate score → audition soprano
options → play and download. Keep the score and listening actions easy to
find after generation, using the existing rendering and playback code.

Rename actions consistently: Suggest progression, Suggest unlocked chords,
and Generate score. Update empty states, loading messages, errors, and help
text to match. Explain SATB and Roman numerals briefly where users first
encounter them. Describe harmonic color musically; remove request-field
instructions from the workspace. Keep seed available as an optional advanced
control. Preserve its value and request behavior when moving or collapsing it.

Done: a first-time visitor can follow the workflow without API knowledge.
Verify chord edits and locks survive regeneration as intended; score preview,
soprano selection, Play/Stop, and export still use the selected progression.
Do not add automatic generation or hidden API calls on page load.

## 3. Polish Analyze and the shared workspace behavior

File: `app/static/index.html`; inspect backend walkthrough availability only
if needed to support accurate copy.

Keep Analyze as a complete studio workspace: clear accepted formats,
upload/drop interaction, musical resolution help, key/Roman-numeral/cadence
results, and readable errors. Replace the LLM-key setup hint with user-facing
availability wording that accurately reflects existing server behavior.
Do not introduce a new backend availability endpoint merely for the rebrand.

Complete keyboard tab navigation with appropriate tab/panel relationships
and visible focus. Verify label associations, loading/disabled actions, mobile
layout, and both supported themes. Check switching workspaces during playback
and pending requests; prevent stale results or controls from misleading users.
Fix only reproduced issues directly affecting these workflows, and record
larger problems as separately scoped follow-ups.

Known soprano seams to reproduce: editing the progression after generating
and then selecting an older option; a failed soprano-options request leaving
an empty heading. If reproduced, invalidate or guard stale options and hide
the unavailable section without hiding the successfully generated score.

Done: upload/results work; keyboard users can switch workspaces; controls and
results remain usable on mobile and in either theme; stale options cannot
silently apply to an edited progression. Add targeted regression coverage
only for actual state/behavior fixes where it meaningfully verifies them.

## 4. Align developer presentation and product documentation

Files: `app/static/portfolio.html`, `README.md`, `docs/START-HERE.md`,
`docs/STATUS.md`, and a new entry in `docs/AI-DIARY.md`.

Bring the developer showcase's typography, colors, and navigation into line
with the studio while retaining endpoint examples and live responses for its
developer audience. Keep authentication and server-status descriptions
accurate. The showcase should explain programmatic access to the studio's
capabilities and make returning to the browser product obvious.

Rewrite the README introduction around Harmony Studio. Put browser setup and
the Create/Analyze workflow before the endpoint reference. Direct quick-start
users to `/`, with `/docs` as the developer next step. Update current project
orientation descriptions and record the release's actual changes and checks.
Do not rewrite historical research or diary entries, or broadly rename every
old reference. Do not change working repository links to a nonexistent URL.

Done: the README teaches people to use the studio first; developer examples
still work; current orientation files describe the same product and release.
Inspect rendered Markdown, link destinations, and both showcase aliases.

## 5. Verify and finish the release

Review the combined changes as one product, with particular attention to
the seams between UI state, requests, playback, export, and navigation.

Manual acceptance checklist:

- Fresh `/` visit: Harmony Studio, Create selected, matching visible panel.
- Create: suggest; edit and lock; regenerate unlocked; generate; preview;
  audition and select soprano; play/stop; download and inspect MusicXML.
- Error paths: invalid chord input, failed request, and stale soprano option
  after editing. Successful prior output must not imply a new request succeeded.
- Analyze: valid MusicXML and MIDI uploads; key/chords/cadences visible;
  unsupported input has a useful error; walkthrough copy is accurate.
- Navigation: Create/Analyze preserves intentional workspace state;
  Developers → showcase → studio/docs works through both showcase aliases.
- Keyboard, narrow viewport, light/dark theme: usable controls and results.

Run `git diff --check` and the existing relevant endpoint tests after backend
edits. At the integrated release boundary, run the existing test suite and
generation evaluation once; run the other existing CI checks as required by
`.github/workflows/ci.yml`. Do not edit `tests/test_partwriting.py`. Avoid
building a new frontend test framework solely for branding changes.

Review current user-facing text for leftover Harmonyx branding, retaining
historical references and correct repository URLs. Record actual verification
results and any limitations in the diary/status handoff. Commit and push the
final verified changes; confirm the local branch matches its remote.

Done: all acceptance checks pass, required checks pass, release documentation
matches shipped behavior, and the work is committed and pushed. Deployment
to a hosted environment is a separate step once its target is identified.

## Subsequent decisions, outside this release

After using the rebranded studio, choose one next product chunk: a larger
score-centered layout, saved projects, guided examples, improved audio, or a
separate marketing page. Scope each independently. Repository/domain renames
and updates to external portfolio links or preview artwork need an inventory
of the actual external destinations before execution.

## Suggested execution order

1 → 2 → 3 → 4 → 5. The first chunk yields a usable rebranded application;
the remaining chunks refine usability, align supporting surfaces, and verify
the combined release. A UI label rename is not complete until dependent help
text and state transitions are checked; a working backend test does not by
itself establish that the browser workflow works.
