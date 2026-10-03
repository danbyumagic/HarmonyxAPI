# Harmony Studio rebranding proposal

Reviewed 2026-10-02. Direction requested by the user: **Harmony Studio** is
the main product, with the browser frontend as the primary experience and
the API as a supporting feature. This document proposes the first build
chunk; no application changes have been made yet.

## Product positioning

**Harmony Studio**

> Create, hear, and explore classical harmony.

Supporting description:

> Shape a chord progression into a four-part score, explore melodic options,
> or upload a score to understand its harmony.

Describe the current capabilities accurately: generation produces SATB
chorale textures; analysis accepts MusicXML and MIDI. Avoid implying a full
notation editor, saved projects, modulation support, or AI progression
generation, which are not currently implemented.

## What exists today

| Surface | Current presentation | Proposed presentation |
| --- | --- | --- |
| `/` (`app/static/index.html`) | Harmonyx; Analyze opens first; Generate is the second tab | Harmony Studio; Create opens first; Analyze remains a peer workspace |
| `/demo` and `/portfolio` (`app/static/portfolio.html`) | “An API that reads and writes classical harmony”; endpoint badges and response payloads | Harmony Studio API showcase for developers; prominent “Open Harmony Studio” link to `/` |
| `/docs` (`app/main.py` metadata) | Harmonyx API | Harmony Studio API, described as programmatic access to studio capabilities |
| README | FastAPI service; “thin demo UI”; endpoint reference first | Browser product introduction and studio quick start first, followed by developer/API reference |
| Generated download | `harmonyx_<key>.musicxml` | `harmony-studio_<key>.musicxml` |
| Project orientation docs | Harmonyx API as the product name | Harmony Studio direction, with the API supporting the frontend |

The root route already serves the working frontend. A frontend-first launch
does not require changing endpoint paths or replacing the existing backend.
The two HTML pages currently use different visual styles; the developer
showcase should share the product name and clear navigation in the first
chunk, with broader visual consolidation deferred.

## Navigation and workflow

At `/`, use the Harmony Studio brand followed by **Create** and **Analyze**
workspace tabs. Keep a small **Developers** link in the footer, pointing to
the existing API showcase, which in turn links to `/docs` and the studio.

Create should open with “Create a four-part score” and the existing key,
length, cadence, and harmonic-color controls. Keep the current workflow:
propose a progression, edit or lock chords, generate the score, compare
soprano options, listen, and download MusicXML.

Suggested visible action labels:

- “Propose progression” → “Suggest progression”.
- “Regenerate unlocked” → “Suggest unlocked chords”.
- “Realize MusicXML” → “Generate score”.
- Keep Play, Stop, and the MusicXML download explicit.

Analyze keeps its current upload and results workflow. Explain musical
controls in user terms; move request-field details such as “Sent as `spice`
on Propose” to developer documentation. Walkthrough availability copy should
reflect the server configuration rather than instructing musicians to set
an LLM key.

## First implementation chunk

Rebrand the existing product surfaces and make Create the default workspace.
Update the two HTML pages, FastAPI title/description, README introduction
and quick start, and the opening product descriptions in START-HERE and
STATUS. Add a brief diary entry recording the product direction and result.
Keep historical diary entries as history. Keep the current GitHub repository
URL until a repository rename is explicitly chosen.

Check the seams: tab order, initial `aria-selected` values and panel
visibility must agree; renamed buttons must match empty-state instructions;
the API showcase must lead back to the studio; download naming and API docs
must share the product name. Preserve element IDs and request contracts so
copy changes do not disrupt the existing event handlers.

Done means the studio opens in Create, both workspaces function, the
developer path is secondary and reachable, and current product-facing copy
uses Harmony Studio. Verify the create → edit/lock → generate → play/stop →
download flow, Analyze upload/results, and links across `/`, `/demo`,
`/portfolio`, and `/docs`. Run existing relevant checks for any touched
backend metadata or route behavior. Commit and push at this boundary.

Larger workspace redesigns, saved projects, new generation features, and
repository/domain renames are separate decisions after this chunk.
