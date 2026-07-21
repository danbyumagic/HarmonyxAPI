# Research #12 — `jjazzboss/JJazzLab`

**Repo:** github.com/jjazzboss/JJazzLab (LGPL-2.1, 574★, 46 forks, Java —
Apache NetBeans RCP platform). Actively maintained: last push 2026-07-05.
35,000+ users across 90+ countries per README; ready-to-use Win/Linux/Mac
installers at jjazzlab.org, plus a separate `JJazzLabToolkit` (headless
single-jar core for developers).

**What it is:** a desktop **backing-track generator** — type chord symbols,
pick a rhythm/style, get a full multi-instrument arrangement (drums, bass,
guitar, piano, strings) with a built-in FluidSynth soft-synth or VST output.
Not classical, not RN-based — read per `RESEARCH-QUEUE.md`'s framing as a
**product-completeness study**: what does a finished, polished, actually-
used desktop music app look like, independent of the jazz domain.

## Architecture

Multi-module Maven project on the **Apache NetBeans RCP platform** (65
`pom.xml` files across the tree) — plugin/OSGi-style modularity is the
foundation, not an afterthought:

- **`model/`** — pure domain model modules: `Harmony` (`ChordType`,
  `ChordSymbol`, `Scale`, `Degree`, `TimeSignature` — a full jazz chord-
  symbol theory library independent of any generation code), `Rhythm` (the
  `Rhythm`/`RhythmParameter`/`RhythmVoice` SPI — the plugin contract a
  "style" must implement), `Song`/`SongImpl`, `Phrase`, `Midi`.
- **`core/`** — engine services: `RhythmMusicGenerationSPI` (the
  `MusicGenerator.generateMusic(SongContext, RhythmVoice...) -> Map<RhythmVoice,
  Phrase>` contract every style plugin implements), `RhythmMusicGeneration`
  (shared generation utilities: `AccentProcessor`, `AnticipatedChordProcessor`,
  `SongChordSequence`), `RhythmDatabase`, `RhythmParametersImpl` (the actual
  `RP_SYS_Variation`/`RP_SYS_Intensity`/`RP_SYS_Fill` parameter types),
  `Quantizer`, `Humanizer`, `PhraseTransform`, `OutputSynth`,
  `EmbeddedSynth`, `Importers`, `UndoManager`.
- **`plugins/`** — the actual style engines, each a separate module
  implementing the `Rhythm`/`MusicGenerator` SPI:
  - **`YamJJazz`** — imports **Yamaha `.sty` style files** (a decades-old
    proprietary hardware-keyboard format with a huge pre-existing style
    library) and replays/adapts their pattern data as a rhythm source.
    Pragmatic reuse of an entire existing content ecosystem rather than
    authoring original styles from scratch.
  - **`JJSwing`** — JJazzLab's own original swing/jazz engine, and the more
    interesting one architecturally: `BassGenerator` and `DrumsGenerator`
    are **not** rule-based note synthesis, they're **pattern-retrieval
    engines**. `WbpSourceDatabase` ("Walking Bass Phrase" source database)
    stores 1/2/3/4-bar phrases *pre-recorded as MIDI* (shipped as resource
    files like `WalkingBassMidiDB.mid`), indexed by the chord sequence they
    were played over — including all sub-phrases (a 4-bar Cm7-F7-E7-Em7
    phrase is also indexed as its three 2-bar and four 1-bar sub-phrases).
    At generation time it scores/matches phrases against the song's actual
    chord sequence and current `RP_SYS_Variation`/`RP_SYS_Intensity`
    parameters (`WbpsaScorer`), plus guessed tags (blues/slow/medium/fast/
    modal) from the harmonic context, then stitches the winning phrases
    together and post-processes (accents, anticipated chords, humanization).
    `DrumsGenerator` mirrors this with its own `DpSourceDatabase`.
- **`app/`** — the actual editors/UI: `CL_Editor` (chord-leadsheet editor),
  `SS_Editor` (song-structure/arranger editor), `PianoRoll`, `MixConsole`,
  `Score` (notation view), `InstrumentChooser`, `ImprovisationSupport`,
  `EasyReader`, `ChordInspector`, plus infra modules (`Upgrade`,
  `StartupManager`, `Analytics`, `UISettings`, `YjzCreationWizard`,
  `branding`).

## The generation technique, compared to peers already studied

This is a **third distinct pattern** for "chords in, music out," alongside
what Harmonyx has already read:
- **AccoMontage2** (research #07): DP/Viterbi retrieval over a *learned*
  phrase-embedding space (PianoTree VAE), needs melody + hand-provided
  phrase segmentation, heavy PyTorch stack.
- **music-arranger** (research #09): declarative CP-SAT constraint solving
  — no corpus at all, pure constraint satisfaction over voice/step variables.
- **JJazzLab (JJSwing)**: **concatenative retrieval from a small,
  hand-curated MIDI phrase bank**, matched by chord-sequence + tag +
  parameter similarity — no ML, no constraint solver, just indexed lookup +
  scoring + splice + humanize. Much lighter-weight than either peer, and it
  ships and works for 35k+ real users, which is a useful data point: a
  simple retrieval-and-splice technique is enough for a production-quality
  backing-track experience when the phrase bank is well-curated and the
  matching/tagging is careful.

`YamJJazz`'s move — importing an entire pre-existing proprietary content
format (Yamaha `.sty` files) instead of authoring original content — is a
notable **"don't rebuild content you can adapt"** pattern, distinct from
either of the above.

## Product-completeness observations (the actual point of this study)

- **Domain model is decoupled from generation, which is decoupled from
  UI.** `model/Harmony` has zero dependency on how music actually gets
  generated; `RhythmMusicGenerationSPI` has zero dependency on any specific
  style engine; the `app/` editors depend on the SPI, not on `YamJJazz` or
  `JJSwing` directly. This is what let JJazzLab ship two structurally
  unrelated generation engines (imported-content vs. retrieval-based) behind
  one stable UI/editor layer without either engine leaking into the other.
- **A real plugin SPI, not just internal modularity.** `Rhythm` +
  `MusicGenerator` + `RhythmParameter` is deliberately public/documented
  ("Developers can easily add music generation capabilities... without
  taking care of all the plumbing") and shipped as a standalone
  `JJazzLabToolkit` jar specifically so third parties can write new style
  plugins without embedding the whole NetBeans app. Explicit extensibility
  surface, not an accident of the codebase's shape.
- **System-level concerns are handled centrally, not per-plugin.**
  `MusicGenerator`'s own javadoc lists everything the *framework* already
  handles so a style plugin doesn't have to: instrument/MIDI channel
  assignment, mute/solo rhythm parameters, custom-phrase substitution,
  fade-out, velocity shift, transposition, drum channel rerouting, NC-chord
  silencing. A style plugin only implements the musical generation itself.
  That's the kind of seam discipline `AGENTS.md`'s own "own the seams"
  principle is pointing at, done here as a hard interface contract instead
  of a convention.
- **Real users surface real infrastructure needs that internal-only tools
  never hit:** dedicated `Upgrade` module (migrating a user's saved
  project/settings across versions), `StartupManager`, `Analytics`,
  crowdin-based **community translation** (`crowdin.yml`, README notes
  multiple languages "thanks to the JJazzLab community"), and a public
  `CONTRIBUTING.md`. None of this is generation-engine work; all of it is
  what "actually shipped to 35k users" costs beyond the core algorithm.
- **23 files matching `Test*.java`** across the repo plus a dedicated
  `TestMocks`/`TestPlayerService` module — modest relative to app size but
  present at both the domain-model and generation-engine layers, and there's
  a `RhythmStubs` module purpose-built to let other modules/tests depend on
  a fake `Rhythm` without pulling in a real style engine.

## Vs. Harmonyx

Not an architecture peer in the RN/SATB sense — no overlap with
`rules.py`/`realize.py`/analyzer. The transferable lessons are entirely
about **product shape**, not music theory:

1. Harmonyx's current split (`app/generation/` engine vs. `app/main.py`
   API vs. `app/static/` frontend) is already the right shape at small
   scale; JJazzLab is the "what this looks like at 100x the surface area"
   reference — keep the same discipline (engine has no UI dependency, UI
   has no engine-internals dependency) as Harmonyx grows rather than
   letting `/generate`, `/progression`, and a future `/check` blur together.
2. If Harmonyx ever wants a **second realization strategy** (e.g. a
   "looser"/faster mode alongside the locked DP), JJSwing's pattern is a
   cheap third option worth remembering alongside CP-SAT (#09) and
   VAE-embedding retrieval (#07): a small hand-curated bank of pre-voiced
   SATB fragments indexed by RN-sequence + style tag, matched and stitched
   — no training, no solver, just indexed lookup. Not scoped now; logging
   as a third alternative next to the two already in the backlog.
3. The **explicit plugin SPI as a product decision** (not just internal
   modularity) is only relevant to Harmonyx if/when an MCP-exposure chunk
   (research #10) or a "let others add generation styles" idea is ever
   scoped — a reminder that the interface-vs-implementation seam is worth
   designing deliberately, not discovering by refactor later.

## Steal / don't-steal

**Steal (ideas only):**
- Model/engine/UI strict separation, enforced by public interfaces
  (`Rhythm`, `MusicGenerator`) rather than just file layout — worth
  keeping in mind as Harmonyx's own `app/generation/` surface grows.
- "List everything the framework already does so a plugin doesn't have to"
  as documentation discipline (`MusicGenerator`'s own javadoc) — a good
  model for documenting Harmonyx's own `rules.py`/`realize.py` contract if
  it's ever opened up to alternate realization strategies.
- Small hand-curated pattern-bank + retrieval-and-splice as a third
  lightweight alternative to DP (current) / CP-SAT (#09) / learned-embedding
  retrieval (#07), if a second, faster/looser generation mode is ever
  wanted.
- "Importing an existing proprietary content ecosystem" (`YamJJazz`) as a
  reminder that adapting existing content can beat authoring from scratch —
  not directly applicable to Harmonyx today (no equivalent SATB content
  bank exists to import), but worth remembering if one is ever found.

**Don't steal:**
- The NetBeans RCP platform itself, or any of the desktop-app/plugin
  infrastructure (Upgrade, StartupManager, Analytics, crowdin) — all
  solving problems Harmonyx doesn't have yet as a web API + browser
  frontend; premature to adopt any of it now.
- Jazz-specific content (Yamaha `.sty` styles, walking-bass MIDI banks,
  chord-symbol vocabulary) — different domain, not reusable for
  classical SATB.

## Open questions / follow-ups

- If Harmonyx ever needs a non-classical "generate a full arrangement"
  track (background/accompaniment generation beyond SATB hymns), JJazzLab's
  `RhythmParameter`/`RhythmVoice` model is worth a second, deeper look —
  this pass only covered the SPI shape and one style engine (JJSwing), not
  the full rhythm-parameter type system or the MixConsole/VST integration
  layer.
- Tier 2 #6 (rnbert / muMoE-RNBERT) remains the next queued item if a
  neural-RNA investment is ever made; unrelated to this chunk.
