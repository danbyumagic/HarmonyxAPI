"""Turn a Roman-numeral progression into a four-part SATB music21 Score.

The search: for each chord, enumerate rule-legal candidate voicings
(``voicing.candidate_voicings``), then run a Viterbi/DP pass across the whole
progression, pruning any transition that has a hard-invariant violation
(``rules.rule_violations``) and minimizing total ``rules.transition_cost``
among what's left. See ``docs/PARTWRITING-RULES.md`` and
``docs/IMPLEMENTATION-PLAN.md`` Milestone 1d/1e for the design.

This module has no FastAPI/HTTP dependency (PARTWRITING-RULES §11 / the
implementation plan's guiding constraints) so it's usable and testable
standalone.
"""

from __future__ import annotations

from typing import List, Optional

from music21 import clef as m21clef
from music21 import key as m21key
from music21 import layout as m21layout
from music21 import meter as m21meter
from music21 import note as m21note
from music21 import stream as m21stream

from . import chords as _chords
from .rules import RuleViolation, rule_violations, transition_cost
from .voicing import Voicing, candidate_voicings

# Grand-staff layout (hymnal style):
#   Treble: Soprano (stem up) + Alto (stem down)
#   Bass:   Tenor   (stem up) + Bass  (stem down)
_STEM_UP = "up"
_STEM_DOWN = "down"


class RealizationError(Exception):
    """Raised when no legal voicing / voice-leading path exists."""


def check_soprano(
    progression: List[str], key_like: _chords.KeyLike, soprano: List[Optional[int]]
) -> List[dict]:
    """Validate a provided soprano line against its chords (§ soprano compatibility).

    Returns ``[]`` if every non-``None`` soprano entry is a chord tone of its
    Roman numeral; otherwise a list of per-index mismatch reports:
    ``{"index": i, "roman": figure, "soprano": pitch, "chord_tones": [...]}``.
    Entries where ``soprano[i] is None`` are skipped (that beat is left free
    for the realizer to choose).
    """
    if len(soprano) != len(progression):
        raise ValueError("soprano list length must match progression length")

    mismatches: List[dict] = []
    for i, (figure, pitch) in enumerate(zip(progression, soprano)):
        if pitch is None:
            continue
        if not _chords.is_chord_tone(pitch, figure, key_like):
            mismatches.append(
                {
                    "index": i,
                    "roman": figure,
                    "soprano": pitch,
                    "chord_tones": _chords.chord_pitch_classes(figure, key_like),
                }
            )
    return mismatches


def realize(
    progression: List[str],
    key_like: _chords.KeyLike,
    *,
    soprano: Optional[List[Optional[int]]] = None,
    time_signature: str = "4/4",
) -> m21stream.Score:
    """Realize a Roman-numeral progression as a 4-voice SATB ``music21.Score``.

    Output is a **grand staff** (piano layout): treble holds soprano+alto as
    separate voices (stems up/down); bass holds tenor+bass (stems up/down).

    ``soprano``, if given, must be the same length as ``progression``; an
    entry may be ``None`` to leave that beat free. Callers should run
    ``check_soprano`` first and surface any mismatches (e.g. as a 422) rather
    than calling this directly with an unchecked soprano -- ``realize`` itself
    still raises ``RealizationError`` if an incompatible soprano leaves no
    candidate voicings, but ``check_soprano`` gives per-beat diagnostics.

    Raises ``RealizationError`` if the progression is empty, or if no
    hard-invariant-clean voice-leading path exists.
    """
    if not progression:
        raise RealizationError("progression must not be empty")
    if soprano is not None and len(soprano) != len(progression):
        raise ValueError("soprano list length must match progression length")

    contexts = [
        {
            "key": key_like,
            "prev_roman": progression[i - 1] if i > 0 else None,
            "cur_roman": figure,
        }
        for i, figure in enumerate(progression)
    ]

    candidate_lists: List[List[Voicing]] = []
    for i, figure in enumerate(progression):
        sop = soprano[i] if soprano is not None else None
        cands = candidate_voicings(figure, key_like, soprano=sop)
        if not cands:
            detail = f" with soprano={sop}" if sop is not None else ""
            raise RealizationError(f"no legal voicings for chord {i} ('{figure}'){detail}")
        candidate_lists.append(cands)

    voicings = _best_path(progression, candidate_lists, contexts)
    return _build_score(voicings, key_like, time_signature)


DEFAULT_PLAYBACK_TEMPO_BPM = 75


def playback_from_voicings(
    voicings: List[Voicing],
    *,
    tempo_bpm: int = DEFAULT_PLAYBACK_TEMPO_BPM,
    beat_duration: float = 1.0,
) -> dict:
    """Build a simple block-chord playback payload for the web player.

    Each chord is one beat: all four voices sound together (no arpeggiation).
    ``events`` entries are ``{beat, midi, duration}`` with ``duration`` in beats.
    """
    events: List[dict] = []
    for i, v in enumerate(voicings):
        beat = float(i)
        for midi in (v.s, v.a, v.t, v.b):
            events.append(
                {"beat": beat, "midi": int(midi), "duration": float(beat_duration)}
            )
    return {"tempo_bpm": int(tempo_bpm), "events": events}


def _best_path(
    progression: List[str],
    candidate_lists: List[List[Voicing]],
    contexts: List[dict],
) -> List[Voicing]:
    """Viterbi/DP over candidate voicings, minimizing summed transition_cost
    while excluding any transition with a hard-invariant violation."""
    n = len(progression)
    inf = float("inf")

    dp_cost: List[List[float]] = [[inf] * len(candidate_lists[i]) for i in range(n)]
    dp_back: List[List[int]] = [[-1] * len(candidate_lists[i]) for i in range(n)]

    for j, v in enumerate(candidate_lists[0]):
        if rule_violations(None, v, contexts[0]):
            continue
        dp_cost[0][j] = transition_cost(None, v, contexts[0])

    for i in range(1, n):
        if all(c == inf for c in dp_cost[i - 1]):
            raise RealizationError(
                f"no rule-legal voicing reaches chord {i - 1} ('{progression[i - 1]}') "
                f"from chord {i - 2 if i >= 2 else 'start'}"
            )
        for j, v in enumerate(candidate_lists[i]):
            best_cost, best_k = inf, -1
            for k, pv in enumerate(candidate_lists[i - 1]):
                if dp_cost[i - 1][k] == inf:
                    continue
                if rule_violations(pv, v, contexts[i]):
                    continue
                cost = dp_cost[i - 1][k] + transition_cost(pv, v, contexts[i])
                if cost < best_cost:
                    best_cost, best_k = cost, k
            dp_cost[i][j] = best_cost
            dp_back[i][j] = best_k

    last = dp_cost[-1]
    if all(c == inf for c in last):
        raise RealizationError(
            f"no rule-legal voice-leading path found for this progression "
            f"(dead end at chord {n - 1}, '{progression[-1]}')"
        )

    best_j = min(range(len(last)), key=lambda j: last[j])
    path_idx = [0] * n
    path_idx[-1] = best_j
    for i in range(n - 1, 0, -1):
        path_idx[i - 1] = dp_back[i][path_idx[i]]

    return [candidate_lists[i][path_idx[i]] for i in range(n)]


def path_violations(voicings: List[Voicing], progression: List[str], key_like: _chords.KeyLike) -> List[RuleViolation]:
    """Every hard-invariant violation across an already-realized path.

    Used by the M2 eval and by tests to assert a realized progression is
    clean, independent of how it was constructed.
    """
    contexts = [
        {
            "key": key_like,
            "prev_roman": progression[i - 1] if i > 0 else None,
            "cur_roman": figure,
        }
        for i, figure in enumerate(progression)
    ]
    out: List[RuleViolation] = []
    for i, v in enumerate(voicings):
        prev = voicings[i - 1] if i > 0 else None
        out += rule_violations(prev, v, contexts[i])
    return out


def _build_score(voicings: List[Voicing], key_like: _chords.KeyLike, time_signature: str) -> m21stream.Score:
    """Pack SATB into a braced grand staff with correct stem directions."""
    k = _chords.to_key(key_like)

    treble = m21stream.PartStaff(id="Treble")
    treble.partName = "Soprano / Alto"
    bass_staff = m21stream.PartStaff(id="Bass")
    bass_staff.partName = "Tenor / Bass"

    v_s = m21stream.Voice(id="Soprano")
    v_a = m21stream.Voice(id="Alto")
    v_t = m21stream.Voice(id="Tenor")
    v_b = m21stream.Voice(id="Bass")

    for v in voicings:
        v_s.append(_note(v.s, _STEM_UP))
        v_a.append(_note(v.a, _STEM_DOWN))
        v_t.append(_note(v.t, _STEM_UP))
        v_b.append(_note(v.b, _STEM_DOWN))

    treble.append(m21clef.TrebleClef())
    treble.append(m21meter.TimeSignature(time_signature))
    treble.append(m21key.Key(k.tonic.name, k.mode))
    treble.insert(0, v_s)
    treble.insert(0, v_a)

    bass_staff.append(m21clef.BassClef())
    bass_staff.append(m21meter.TimeSignature(time_signature))
    bass_staff.append(m21key.Key(k.tonic.name, k.mode))
    bass_staff.insert(0, v_t)
    bass_staff.insert(0, v_b)

    score = m21stream.Score()
    score.insert(0, treble)
    score.insert(0, bass_staff)
    score.insert(
        0,
        m21layout.StaffGroup(
            [treble, bass_staff],
            name="SATB",
            symbol="brace",
            barTogether=True,
        ),
    )
    return score.makeMeasures(inPlace=False)


def _note(midi: int, stem_direction: str) -> m21note.Note:
    n = m21note.Note()
    n.pitch.midi = midi
    n.quarterLength = 1.0
    n.stemDirection = stem_direction
    return n


def satb_voicings_from_score(score: m21stream.Score) -> List[Voicing]:
    """Recover the SATB MIDI path from a grand-staff (or legacy 4-part) score.

    Grand staff: Treble staff voice 0 = S (stems up), voice 1 = A (stems down);
    Bass staff voice 0 = T (stems up), voice 1 = B (stems down). Legacy four
    ``Part`` scores keyed by Soprano/Alto/Tenor/Bass ids are also supported.
    """
    by_id = {p.id: p for p in score.parts}

    if {"Soprano", "Alto", "Tenor", "Bass"}.issubset(by_id):
        s = [n.pitch.midi for n in by_id["Soprano"].recurse().notes]
        a = [n.pitch.midi for n in by_id["Alto"].recurse().notes]
        t = [n.pitch.midi for n in by_id["Tenor"].recurse().notes]
        b = [n.pitch.midi for n in by_id["Bass"].recurse().notes]
        return [Voicing(s[i], a[i], t[i], b[i]) for i in range(len(s))]

    treble = by_id.get("Treble")
    bass = by_id.get("Bass")
    if treble is None or bass is None:
        # MusicXML reparse may rename parts; fall back to first two parts.
        parts = list(score.parts)
        if len(parts) < 2:
            raise ValueError("score does not look like SATB grand staff or 4-part")
        treble, bass = parts[0], parts[1]

    s_midis, a_midis = _staff_voice_midis(treble)
    t_midis, b_midis = _staff_voice_midis(bass)
    n = len(s_midis)
    if not (n == len(a_midis) == len(t_midis) == len(b_midis)):
        raise ValueError(
            f"uneven SATB lengths: S={n} A={len(a_midis)} T={len(t_midis)} B={len(b_midis)}"
        )
    return [Voicing(s_midis[i], a_midis[i], t_midis[i], b_midis[i]) for i in range(n)]


def _staff_voice_midis(part: m21stream.Part) -> tuple[List[int], List[int]]:
    """Return (stem-up midis, stem-down midis) for a two-voice staff.

    After ``makeMeasures``, each measure has its own Voice pair, so we collect
    every note on the staff and split by stem direction (S/T up, A/B down),
    ordered by score offset.
    """
    notes = list(part.recurse().notes)
    if not notes:
        raise ValueError(f"staff {part.id!r} has no notes")

    # (offset, midi) per stem direction — offset from the Part for stable order.
    up_pairs: List[tuple[float, int]] = []
    down_pairs: List[tuple[float, int]] = []
    for n in notes:
        # Absolute-ish order: offset relative to part (works across measures).
        off = float(n.getOffsetInHierarchy(part))
        midi = n.pitch.midi
        if n.stemDirection == _STEM_DOWN:
            down_pairs.append((off, midi))
        else:
            # Default / "up" / "unspecified" treated as the upper voice on the staff.
            up_pairs.append((off, midi))

    up_pairs.sort(key=lambda x: x[0])
    down_pairs.sort(key=lambda x: x[0])
    up = [m for _, m in up_pairs]
    down = [m for _, m in down_pairs]
    if up and down and len(up) == len(down):
        return up, down
    raise ValueError(
        f"could not split staff {part.id!r} into two equal voices "
        f"(up={len(up)} down={len(down)})"
    )
