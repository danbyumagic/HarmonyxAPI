# Harmony Studio implementation plan

Prepared 2026-10-02 from `HARMONY-STUDIO-REBRAND.md` and the current frontend.
Status: all five chunks complete and verified (2026-10-02).

Chunk 1 verification: browser confirmed Create selected on fresh load,
Analyze/Create switching, progression proposal and score generation with
notation preview, Play/Stop controls, export filename
`harmony-studio_C_major.musicxml`, and Developers → showcase → studio links.
Export naming was checked by intercepting the browser download anchor; an
actual file download/import was not checked in this chunk. Focused TestClient
checks confirmed OpenAPI branding and identical `/demo` and `/portfolio`
responses. Existing generate/progression endpoint tests: **22 passed**.
`git diff --check` passed.

Chunk 2 verification: browser confirmed the revised labels and guidance,
seed `0` retained with Advanced settings collapsed, locked chord preservation
when suggesting unlocked chords, and a fresh suggestion clearing locks.
Actual requests retained numeric spice values and the existing style aliases
(checked Student and Spicy, plus Max with no alias). Generation rendered
notation; previewing and selecting another soprano worked; Play/Stop controls
and export naming passed. No automatic generation was added. Export was
checked through its anchor, not a downloaded-file import. No backend changes
or new test framework; `git diff --check` passed. Next chunk: Analyze and
shared workspace behavior (now completed below).

Chunk 3 verification: reproduced the empty-options heading and old soprano
cards surviving edited harmony, then verified key/chord edits remove old
output. Generation actions now serialize requests and discard stale responses;
Analyze displays only its latest response. Browser checks passed for invalid
and empty chord input, failed options with a successful score, More options
failure/retry, delayed generation after an edit, delayed older analysis,
unavailable walkthrough feedback, keyboard tab navigation and lock/soprano
focus, and stopping playback when leaving Create. Valid MusicXML upload
through the file-input change handler and generated MIDI analysis passed.
The export Blob parsed as MusicXML and round-tripped through Analyze.
Notation-loader failure/reset/retry passed with injected load events.
Narrow viewport checks confirmed contained score/cards and no page overflow;
light/dark appearances were inspected. No musical engine or API contract
changes were made. Frontend JavaScript parsing and diff checks passed.

Chunk 4 verification: developer showcase typography, palette, navigation,
focus states, and mobile layout now align with the studio. Its live progression,
generation, notation, analysis, and soprano-option examples passed browser
checks. `/`, `/demo`, `/portfolio`, `/docs`, and `/openapi.json` returned 200;
showcase aliases returned identical HTML. README now leads with browser setup
and workflows, followed by the developer reference. Its link targets and code
fences were checked. Local START-HERE, STATUS, and a new diary entry were
updated; their existing private/ignored-file policy is retained. The tracked
plan records release verification for the remote handoff. The README rendered
on GitHub with Harmony Studio and the browser quick start/workflows preceding
the API reference.

Chunk 5 release checks:

- `python -m pytest tests/ -q`: **191 passed** (one existing TestClient
  deprecation warning).
- `python -m eval.run_eval --min 0.85`: **18/20 = 90%**, gate passed.
- `python -m eval.run_generation_eval --min-roundtrip 1.0 --max-violations 0`:
  **27/27 = 100%** primary and strict round-trip, **0 hard violations**.
- `python -m eval.run_rn_eval --min 0.0`: **397/949 = 42%** primary and
  **359/949 = 38%** strict; visibility-only check passed.
- Both frontend scripts parsed; `git diff --check` passed; locked
  `tests/test_partwriting.py` was unchanged.
- Integrated browser workflows, keyboard focus/navigation, mobile containment,
  light/dark themes, developer links/aliases and live examples passed as
  recorded above. Failure and delayed-response checks used injected responses
  and load events rather than external provider outages.

Limits: playback controls and scheduled audio state were checked, but audio
quality was not subjectively evaluated. Exported Blob bytes were parsed and
re-analyzed in-browser; no external notation-app import was performed. No
hosted deployment or repository/domain rename was part of this release.

Implementation commits: `0663fb4` (chunk 1), `33f237a` (chunk 2), `2dc86a6`
(chunk 3), and `0495cdb` (chunk 4). This final verification record completes
chunk 5. No unrelated roadmap work remains authorized by this release plan.

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
AGENTS.md. The user explicitly authorized completing chunks 3–5 together on
2026-10-02, so those chunks proceed with separate verification/commit boundaries
without waiting for additional approval. Future work returns to the normal
small-chunk convention.

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
