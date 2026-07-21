# Research #15 — Tier 3 remainder: diatone, mcp-score, Humdrum/**kern tooling

- **diatone**: `owenbush/diatone` — dependency-free, real-time-safe C++17
  music-theory library. 0★, MIT.
- **mcp-score**: `tskovlund/mcp-score` — MCP server + Claude Code skill +
  MuseScore QML plugin for AI-driven notation (generation via music21 script,
  live manipulation via WebSocket bridges to MuseScore/Dorico/Sibelius).
  14★, MIT.
- **Humdrum/**kern tooling**: `craigsapp/humdrum2musicxml` (CGI-backed
  conversion service + Perl client) and `leihua-dev/KernScores-downloader`
  (bulk `.krn` downloader). 0★/2★, unlicensed/MIT (downloader content itself
  is CC BY-NC 4.0 per its README).

Read: diatone's full README + all six `include/diatone/*.hpp` headers
(`roman.hpp`, `suggest.hpp`, `voicing.hpp`, `progression.hpp`, plus
`chord`/`note`/`scale`/`registry`/`interval` skimmed via the file tree) —
did not build/run the C++ or read `.cpp` bodies, the headers plus README
example fully specify the public API and this is a tiny (10-file) library.
mcp-score's README + `docs/architecture.md` + `docs/reference.md` in full —
config/protocol-heavy rather than logic-heavy, so docs sufficed over cloning.
humdrum2musicxml's repo tree, `bin/humdrum2musicxml` (Perl HTTP client) and
`cgi-bin/humdrum2musicxml.pl` (server-side CGI wrapping `converter21`); no
top-level README exists in this repo. KernScores-downloader's full README
(bilingual EN/中文, identical content).

## 1. diatone: what it is

A minimal (~10 header/source pairs), dependency-free C++17 theory engine
explicitly designed to be called from a **real-time audio thread**: no heap
allocation, locks, or exceptions on the hot path, value types throughout.
Four pieces map directly onto Harmonyx concepts:

- `roman::analyse(Chord, Scale) -> optional<RomanNumeral>` /
  `roman::realise(RomanNumeral, Scale) -> Chord` — single-chord,
  given-a-key RN lookup and its inverse. `RomanNumeral` is just
  `{degree: int, quality: ChordQuality}` — no inversion, no seventh
  extension, no secondary-dominant/borrowed-chord marker in the struct
  itself (those may exist in `ChordQuality` internals, not inspected).
  Materially shallower than Harmonyx's RN grammar (`app/generation/grammar.py`)
  or its analyzer output.
- `SuggestionStrategy` (interface) / `FunctionalHarmonyStrategy` (concrete,
  single `float adventurous_` knob 0..1) — `suggestNext(current, scale) ->
  vector<{RomanNumeral, weight}>`. This is diatone's rough equivalent of
  Harmonyx's rule-grammar + `spice` slider: a swappable strategy object
  producing weighted next-chord candidates (README example: V → I at
  weight ~0.96) rather than Harmonyx's decision to hand-write chord-to-chord
  transition tables directly in `grammar.py`.
- `VoiceLeadingStrategy` (interface) / `NearestVoiceLeading` (concrete) —
  `lead(fromNotes, targetChord, maxSemitones) -> vector<Note>`. A strategy
  seam for "smoothest voicing," conceptually parallel to Harmonyx's DP
  realizer (`app/generation/`) but the library ships only the single naive
  nearest-tone strategy, not a DP/beam search.
- **Data-driven registries**: scales and chord qualities are single-line
  entries in `registry.cpp` (`scales.registerType({"Harmonic Minor", {2, 1,
  2, 2, 1, 3, 1}})`), not switch statements — adding a scale or chord quality
  requires zero control-flow changes. Ships only 9 scales (diatonic modes +
  2 pentatonics) and 8 chord qualities (no dim7, sus2/4, or extended chords
  yet — flagged in its own `ROADMAP.md` as wanted contributions).

## 2. mcp-score: what it is

Two complementary AI-notation approaches bundled as one PyPI package
(`pip install mcp-score`), deliberately kept separate because they solve
different problems:

1. **Generation** — a **Claude Code skill** (not an MCP tool) that teaches
   Claude music21 patterns; Claude writes one complete Python script that
   exports MusicXML directly. No MCP round-trips — the author's stated
   reasoning is that one script beats dozens of tool calls, and a skill with
   full music21 API access beats a curated/limited tool surface.
2. **Live manipulation** — an MCP server (`mcp-score serve`, 18 tools across
   connection/analysis/manipulation) that bridges to a *running* notation
   app via WebSocket: a custom QML plugin for MuseScore (port 8765, full
   score-model read access), or the app-native "Remote Control" protocol
   built into Dorico 4+ (port 4560) and Sibelius 2024.3+ Ultimate (port
   1898) — shared handshake/session-token logic factored into one
   `RemoteControlBridge` base class, with `DoricoBridge`/`SibeliusBridge` as
   thin ~2-field subclasses (just port + app name).

The most useful finding is the **documented capability matrix**: Dorico's
and Sibelius's Remote Control APIs can execute ~900+ UI commands and read
*selection properties*, but cannot read arbitrary score content, set key
signatures/tempo/chord symbols (all gated behind text-input popovers with no
programmatic path), or export MusicXML — because those are upstream API
gaps in the host apps, not something mcp-score chose to skip. Only the
MuseScore QML plugin (running code *inside* the app) gets deep read access.
The docs are explicit that this is a **known ceiling**, with app-native
scripting (Sibelius ManuScript, undocumented Dorico Lua) named as the only
future path past it.

## 3. Humdrum2musicxml + KernScores-downloader: what they are

`craigsapp/humdrum2musicxml` is the backend for
`musicxml.humdrum.org`/`verovio.humdrum.org`: a CGI script
(`cgi-bin/humdrum2musicxml.pl`) that shells out to
`python3 -m converter21 -f humdrum -t musicxml` (a separate, not-explored
Python package) piped through a `cleanMusicxml` postprocessor, plus a thin
Perl HTTP client (`bin/humdrum2musicxml`) that POSTs a `.krn` file to that
service and returns the MusicXML response. It is a **format-conversion
utility**, not an analysis or generation tool — no RN logic, no theory
engine, just Humdrum-kern ↔ MusicXML translation via a remote service call.

`leihua-dev/KernScores-downloader` is a bulk-download script
(`kern.py`) for `.krn` files across 50 major composers from
kern.humdrum.org, with resumable/retryable downloads and composer-organized
output. Bilingual README (EN/中文), but no unique technical content beyond
"this scrapes KernScores.org into a local folder."

**License caveat, worth flagging explicitly**: the downloader repo's own
`LICENSE` badge says MIT, but its README states the *downloaded data* is
governed by **CC BY-NC 4.0** (non-commercial) per KernScores' own terms.
If KernScores.org (or Humdrum-kern data generally) is ever pulled in as an
analyzer-eval corpus, the non-commercial restriction on the underlying data
would need explicit legal sign-off before any commercial use of Harmonyx —
distinct from When-in-Rome (#06, CC BY-SA — share-alike but not NC-restricted).

**Aside, not a finding about the tool itself**: the Perl client script
(`bin/humdrum2musicxml`) has code comments written in an odd
security-thriller register — "RECONNAISSANCE HANDSHAKE," "EMIT PURE
MULTIPART FILE DATA," "Base address intercepted by your company's SSL proxy
rules" — around otherwise ordinary HTTP-redirect-following logic. No
comment contains an actual instruction (nothing tells a reader to run a
command or exfiltrate anything), so there's nothing to act on, but the
phrasing is unusual enough for plain infra code that it's worth a note in
case this or a similar pattern shows up again in a peer repo scan.

## 4. Comparison to Harmonyx

None of the three lands on Harmonyx's build queue directly:

- **diatone** confirms (a third time, after When-in-Rome #06 and Shimaoka
  #08's data-driven scale/chord tables) that a clean "registry of scales +
  chord qualities as data, not switch statements" design is a recurring,
  independently-arrived-at pattern in this space — Harmonyx's own
  `app/generation/grammar.py`/`rules.py` already lean this direction for
  chord vocabulary but could look at diatone's `registerType`/
  `registerQuality` single-call registration API as a readability reference
  if that code is ever refactored (not urgent — no regression, just a
  possible ergonomics win). The `SuggestionStrategy`/`VoiceLeadingStrategy`
  interface-seam pattern (swap implementations without touching callers) is
  the same idea Harmonyx already gets implicitly from keeping `validate.py`/
  `fix.py`/`grammar.py` as separate modules; not a gap.
- **mcp-score** is the closest of the three to something Harmonyx *could*
  eventually offer (an MCP surface over the analyzer/generator, per research
  #10's thiri-mcp/music21-mcp precedent), but the live-app-bridge half is
  irrelevant — Harmonyx has no live MuseScore/Dorico/Sibelius integration
  and OSMD-in-browser already solves score *display*; the score-generate
  *skill* half is a different tactic (teach Claude music21 directly) than
  Harmonyx's own architecture (a hosted rule engine + typed API), not a
  drop-in pattern. The capability-matrix documentation approach (explicit
  per-app support/limitation table, framed as "upstream API gap, not our
  bug") is a good documentation habit to imitate if Harmonyx ever ships
  integrations with variable per-target capability.
- **Humdrum tooling** is a corpus/format question, not an architecture one:
  if analyzer-eval corpus expansion (Q4-adjacent, not currently scoped) ever
  needs more real scores beyond When-in-Rome's ~1,300, KernScores.org is a
  viable *additional* source in principle — but the CC BY-NC 4.0 restriction
  on that specific downloader's target data is a real gate, and
  `humdrum2musicxml` would only be needed as a format bridge if Harmonyx's
  ingestion pipeline ever needs to accept raw `.krn` (it currently only
  accepts MusicXML/MIDI) — no immediate need either way.

## Steal / don't-steal

**Steal (ideas only):**
- diatone's single-line data-registration pattern for scales/chord
  qualities, as a readability reference for `rules.py`/`grammar.py` if that
  code is ever refactored for maintainability.
- mcp-score's explicit per-target capability matrix + "upstream API
  constraint, not our limitation" framing, as a documentation pattern for
  any future Harmonyx integration with uneven third-party capabilities.

**Don't steal:**
- diatone's actual C++ engine — different language/deployment target,
  no product need for real-time-thread safety in a web API.
- mcp-score's live-app WebSocket bridges — no live MuseScore/Dorico/Sibelius
  integration is scoped; OSMD already covers score display.
- KernScores.org as a corpus source, until/unless the CC BY-NC 4.0 gate is
  explicitly cleared by a human decision; don't vendor `kern.py` or its
  output.

## Open questions (not investigated further)

- Whether `converter21` (the Python package `humdrum2musicxml.pl` shells
  out to) has a usable direct Python API for Humdrum↔MusicXML conversion
  independent of the CGI service — not explored; would matter only if raw
  `.krn` ingestion is ever scoped for Harmonyx.
- diatone's `.cpp` implementation bodies (roman.cpp's actual RN-analysis
  algorithm, suggest.cpp's transition-weight table contents) were not read
  — the headers fully specify the public surface, which was enough to judge
  scope/depth, but the *scoring logic* inside `FunctionalHarmonyStrategy`
  wasn't inspected.

This closes Tier 3 of `docs/RESEARCH-QUEUE.md` in full (#8 diatone, #9
mcp-score, #10 Humdrum/**kern tooling all done — done as one combined chunk
per the human's choice this session). Tier 4 (OMR: Audiveris, homr) remains
explicitly parked per `docs/AI-DIARY.md` Entry 4's product decision, not
picked up here.
