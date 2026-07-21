# Research note: thiri-mcp + music21-mcp

**Date:** 2026-07-21
**Repos:**
- https://github.com/BluesPrince/thiri-mcp — "THIRI Chord Intelligence" MCP
  server, hosted deterministic theory engine (`chords.thiri.ai`), MIT license,
  JavaScript/TypeScript, 2★, pushed 2026-07-19 (fresh, active).
- https://github.com/SimonsonM/music21-mcp — MCP server wrapping music21
  directly, self-hosted, MIT license, Python, 2★, pushed 2026-04-18.

**Status:** Tier 1 peers #3–4 (per `docs/RESEARCH-QUEUE.md`) — read together
as one chunk: same question ("how should Harmonyx expose theory operations as
agent-facing MCP tools?"), two opposite architectural answers.
**Source:** Both READMEs in full. `music21-mcp`: `server.py` read in full
(288 lines, single file). `thiri-mcp`: `src/index.ts` read in full (~18KB —
API client, response formatters, all 5 tool definitions + 1 resource), repo
file listing (`docs/`, `examples/`, `conformance/`, `vendor/` noted but not
opened — vendor/docs are submission writeups and a bundled Csound
composition/rendering sub-project, out of scope for this comparison).

---

## 1. Two opposite answers to the same question

Both repos expose music-theory operations as MCP tools for Claude/Cursor/any
MCP client, but they diverge completely on **where the theory engine lives**:

| | thiri-mcp | music21-mcp |
|---|---|---|
| Engine location | **Hosted**, closed-source (`chords.thiri.ai`, "v2 grid engine") — the MCP server here is a thin client that POSTs to a remote API and formats the JSON response as markdown | **Local**, open-source — `server.py` calls the `music21` Python library directly, in-process, no network call |
| Auth / cost | Requires an API key (`THIRI_API_KEY`), quota-metered (`x-quota-limit`/`x-quota-used` headers surfaced back to the agent) | None — free, self-hosted, no external dependency beyond `pip install` |
| Install | `npx @bluesprincemedia/thiri-mcp` or hosted connector URL — zero local setup for the *musician* persona; still needs an API key | Clone + venv + `pip install -r requirements.txt`, point Claude Desktop config at a local Python path |
| Domain | Jazz/pop chord-symbol theory (`Dm7`, `Cmaj7/E`, altered dominants, Coltrane changes, drop-2/3 voicings, chord-scale relationships) | Classical/pedagogical (key detection, RN analysis, Fux first-species counterpoint, Bach-style SATB harmonization, cadence generation) |
| Code visible to read | Only the **client/wrapper** (tool schemas, formatting, error handling) — the actual pitch-class-set engine is not in this repo at all | The **entire** implementation — every tool is a ~20–40 line function directly readable start to finish |

This is the single most useful finding: **"agent-native theory server" is not
one design, it's a spectrum from "thin wrapper around a hosted proprietary
engine" to "thin wrapper around a local open-source library."** Harmonyx,
if it ever exposes `/analyze` + `/generate` + (future) `/check` as MCP tools,
sits architecturally far closer to the music21-mcp end: it already *is* the
engine (FastAPI + music21 + a custom realizer), so an MCP layer would be a
thin adapter over existing endpoints — not a hosted-API client, and not a
new engine.

---

## 2. thiri-mcp — hardening lessons from a *deployed* MCP server

Despite the engine being closed-source, the client code is worth reading for
what a **production-hardened** MCP wrapper looks like, since thiri-mcp is
live and metered (unlike most research peers so far, which are
demos/prototypes). Concrete patterns, each tied to a numbered issue in
inline comments (`#15`, `#16`, `#17`, `#18` — evidence of a real bug-tracked
hardening pass):

- **Request timeout** (`AbortSignal.timeout(REQUEST_TIMEOUT_MS)`, `#15`) —
  never let a tool call hang indefinitely; surface a clear timeout error
  instead.
- **Structured error parsing, not raw passthrough** (`#17`) — parses
  `{error, message}` from a failed response and re-throws a clean message;
  explicitly avoids echoing raw internal error detail to the agent.
- **Fail-fast on missing auth** — checks `API_KEY` before making the network
  call at all, with an actionable error message (where to get a key), rather
  than letting a 401 surface confusingly.
- **Quota self-pacing** (`#16`) — reads `x-quota-limit`/`x-quota-used`
  response headers and appends a `_Quota: X / Y this period._` footer to
  every tool response, so the *calling agent* can see it's approaching a
  rate limit without a separate lookup call.
- **Markdown-formatted responses over raw JSON** (`#18`, explicit before/after
  comment: "was raw JSON.stringify") — every tool response is a human/agent-
  readable markdown summary (headers, bullet lists) *followed by* the raw
  JSON in a fenced code block, so both a chat-rendering client and a
  programmatic agent get what they need from one response.
- **MCP tool annotations** (`readOnlyHint`, `destructiveHint`,
  `idempotentHint`, `openWorldHint` on every tool definition) — declares
  side-effect-free/deterministic/no-external-world-dependency properties per
  MCP spec, which lets a client agent reason about safety without a call.

None of this requires the hosted-vs-local architecture choice — all of it
is directly applicable to a hypothetical Harmonyx MCP layer regardless of
which side of the spectrum Harmonyx picks (and per §1, Harmonyx would be on
the local/open side, closer to music21-mcp).

---

## 3. music21-mcp — the direct architecture template if Harmonyx builds this

Because it's fully readable, `server.py` is close to a literal template for
"wrap an existing Python theory stack as MCP tools" — which is exactly
Harmonyx's shape (FastAPI + music21 already in `app/`, per `docs/STATUS.md`).
Notable structural choices:

- **`FastMCP` decorator pattern** (`@mcp.tool()` on a plain typed function
  with a docstring) — the docstring *is* the tool description shown to the
  LLM; no separate schema-writing step like thiri-mcp's manual Zod schemas.
  Much less boilerplate than thiri-mcp's TypeScript tool registrations, at
  the cost of less explicit control over the exposed schema (relies on
  Python type hints + docstring parsing).
- **Each tool is a thin, direct call into music21** — e.g.
  `analyze_chord_progression` is ~15 lines: build a `key.Key`, loop
  `harmony.ChordSymbol` → `roman.romanNumeralFromChord`, done. No caching,
  no queueing, no auth — appropriate for a local stdio server with a single
  trusted client, a genuinely different threat model than thiri-mcp's
  internet-facing hosted API.
- **Cadence detection is a hardcoded last-two-Roman-numerals lookup table**
  (`{("V","I"): "authentic", ...}`) — much shallower than Harmonyx's own
  cadence handling (`Cad64` support, `style` presets) or PartWise's
  evaluate-tier depth (research #03). Not a source of new ideas here, just
  confirms Harmonyx's cadence logic is already ahead of this baseline.
- **`generate_counterpoint`'s first-species implementation is a genuinely
  weak reference** — it picks consonant intervals against a cantus firmus
  via a hardcoded semitone-agnostic interval list and a same-interval
  parallel check, with a fallback (unconditional 3rd) if nothing fits; no
  proper Fux rule set (no beat-1-consonance-only enforcement beyond the
  interval choice itself, no melodic-line quality check, no leap-then-step
  recovery rule). Worth naming precisely because it's *not* a bar to clear —
  Harmonyx's own `rules.py`/`realize.py` (built for the harder SATB case) is
  already far more rigorous than this toy single-voice generator.

---

## 4. What an MCP layer for Harmonyx would look like (synthesis, not a build plan)

Combining §1–3 into one picture, *if* Harmonyx ever scopes an MCP-exposure
chunk (not proposed here — no such chunk exists in the open queue):

- **Architecture:** closer to music21-mcp (thin wrapper directly over
  existing FastAPI logic, self-hosted, no external API/auth/quota needed) —
  Harmonyx already has the engine; there's no "hosted API" to wrap.
- **Tools would map ~1:1 to existing endpoints:** `analyze_score` →
  `POST /analyze`, `generate_satb` → `POST /generate`, `propose_progression`
  → `POST /progression`, and (once built) `check_partwriting` → M4's
  `POST /check`.
- **Hardening patterns worth adopting regardless of hosted/local** (§2):
  MCP tool annotations (`readOnlyHint` etc. — all of Harmonyx's theory
  operations are read-only/idempotent, an easy, honest annotation set),
  markdown-plus-JSON response formatting for readability, and — if ever
  exposed publicly rather than locally — the timeout/structured-error/quota
  patterns.
- **Not urgent:** this isn't on the open queue (Q1/Q2/Q4/Q5) and nothing
  here changes that; filed as a backlog idea only (§11 of the landscape doc
  already has an "agent-native theory" row from the original scan — this
  research just fills in what it would concretely look like).

---

## 5. Steal / don't-steal

**Steal (ideas, MIT-licensed so also fine to reference concrete snippets):**
- thiri-mcp's production-hardening checklist (§2): timeout, structured error
  parsing, fail-fast auth check, quota self-pacing headers, markdown+JSON
  dual-format responses, MCP tool safety annotations — all directly
  applicable to any future Harmonyx MCP layer, independent of hosted-vs-local.
- music21-mcp's `@mcp.tool()`-decorator-with-docstring pattern (§3) as the
  lowest-boilerplate template for wrapping Python functions as MCP tools —
  directly relevant since Harmonyx is also Python/FastAPI.

**Don't steal:**
- music21-mcp's cadence-detection lookup table or first-species
  counterpoint generator (§3) — both are shallower than what Harmonyx
  already has; no regression risk, just noting they're not upgrades.
- The hosted-API-with-auth-and-quota architecture itself (§1) — not
  applicable; Harmonyx isn't wrapping a third-party paid engine, it *is* the
  engine, so that whole design axis doesn't transfer.

## 6. Open questions

- Is an MCP-exposure layer for Harmonyx (`/analyze`, `/generate`,
  `/progression`, future `/check` as agent tool calls) ever worth scoping as
  its own chunk, or does it stay a backlog idea indefinitely? Human call —
  no signal in `docs/START-HERE.md`'s open queue currently points at it.
- If it ever is scoped: does Harmonyx use `FastMCP` (Python, matches
  music21-mcp's low-boilerplate pattern and Harmonyx's existing stack) or a
  different MCP SDK? Deferred until the chunk is actually named.
