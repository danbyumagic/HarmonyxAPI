"""Roman numeral <-> pitch-class helpers.

Ground rules: see ``docs/PARTWRITING-RULES.md``. All pitch classes are ints
0-11 (C=0 ... B=11). ``key`` throughout this module may be a plain string like
``"C major"`` / ``"a minor"`` or an already-built ``music21.key.Key``.
"""

from __future__ import annotations

from typing import Optional, Union

from music21 import key as m21key
from music21 import pitch as m21pitch
from music21 import roman as m21roman

KeyLike = Union[str, m21key.Key]


def to_key(key_like: KeyLike) -> m21key.Key:
    """Normalize a key string ("C major", "a minor", ...) or Key to a Key."""
    if isinstance(key_like, m21key.Key):
        return key_like
    parts = str(key_like).strip().split()
    tonic = parts[0]
    mode = parts[1].lower() if len(parts) > 1 else "major"
    return m21key.Key(tonic, mode)


def tonic_pitch_class(key_like: KeyLike) -> int:
    return to_key(key_like).tonic.pitchClass


def leading_tone_pitch_class(key_like: KeyLike) -> int:
    """The leading tone: a semitone below the tonic.

    This definition (rather than "the raised 7th scale degree") is what makes
    it mode-agnostic: music21 already raises the 7th in a minor-key V/V7
    (e.g. A minor's V spells G#-B-D), so "semitone below tonic" and "the
    actual leading tone" coincide in both major and minor without special-
    casing the mode here.
    """
    return (tonic_pitch_class(key_like) - 1) % 12


def roman_numeral(figure: str, key_like: KeyLike) -> m21roman.RomanNumeral:
    """Build a music21 RomanNumeral. Raises on an unparseable figure."""
    return m21roman.RomanNumeral(figure, to_key(key_like))


def chord_pitch_classes(figure: str, key_like: KeyLike) -> list[int]:
    """All distinct pitch classes belonging to the chord (root/3rd/5th/[7th])."""
    rn = roman_numeral(figure, key_like)
    return sorted({p.pitchClass for p in rn.pitches})


def chord_members(figure: str, key_like: KeyLike) -> dict:
    """Chord tones by role, as pitch classes.

    Returns ``{"root": pc, "third": pc, "fifth": pc, "seventh": pc|None,
    "bass": pc}``. ``bass`` is the pitch class the chord's inversion figure
    puts in the bass (e.g. ``V6`` -> the third; ``Cad64`` -> the fifth of the
    key, i.e. the dominant bass) -- distinct from ``root``, which is always the
    chord's root regardless of inversion.
    """
    rn = roman_numeral(figure, key_like)
    return {
        "root": rn.root().pitchClass,
        "third": rn.third.pitchClass if rn.third is not None else None,
        "fifth": rn.fifth.pitchClass if rn.fifth is not None else None,
        "seventh": rn.seventh.pitchClass if rn.seventh is not None else None,
        "bass": rn.bass().pitchClass,
    }


def _pitch_class_of(pitch_like) -> int:
    if isinstance(pitch_like, bool):
        raise TypeError("pitch_like must not be a bool")
    if isinstance(pitch_like, int):
        return pitch_like % 12
    if isinstance(pitch_like, m21pitch.Pitch):
        return pitch_like.pitchClass
    return m21pitch.Pitch(str(pitch_like)).pitchClass


def is_chord_tone(pitch_like, figure: str, key_like: KeyLike) -> bool:
    """Is ``pitch_like`` (a note name, MIDI int, or Pitch) part of this chord?

    This is the soprano compatibility check from PARTWRITING-RULES: a given
    soprano note must be a chord tone of the Roman numeral it's paired with.
    """
    pc = _pitch_class_of(pitch_like)
    return pc in chord_pitch_classes(figure, key_like)


def normalize_rn(figure: str, key_like: Optional[KeyLike] = None) -> tuple:
    """Reduce a Roman-numeral figure to ``(degree, quality, inversion, seventh)``
    for the round-trip eval (PARTWRITING-RULES §10).

    ``degree`` is accidental-insensitive (``bVII`` and ``VII`` both -> 7).
    ``quality``/``inversion`` come straight from music21's RomanNumeral parse,
    which is figure-only and does not require a key -- but a key is accepted
    for API symmetry with the rest of this module and future refinement (e.g.
    disambiguating scale-degree accidentals against the key signature).
    """
    # RomanNumeral can parse a figure against a default (C major) key purely to
    # extract quality/inversion/degree; the key only matters for absolute pitch,
    # which normalize_rn deliberately discards.
    probe_key = to_key(key_like) if key_like is not None else m21key.Key("C")
    rn = m21roman.RomanNumeral(figure, probe_key)
    degree = rn.scaleDegree
    quality = rn.quality  # 'major' | 'minor' | 'diminished' | 'augmented' | 'other'
    inversion = rn.inversion()
    seventh = rn.seventh is not None
    return (degree, quality, inversion, seventh)


def rn_agreement(a: str, b: str, key_like: Optional[KeyLike] = None, *, strict: bool = False) -> bool:
    """Compare two Roman-numeral figures per the §10 agreement definition.

    Primary metric (``strict=False``, the default): degree + quality match.
    Secondary/stricter metric (``strict=True``): degree + quality + inversion +
    seventh-presence all match.
    """
    na, nb = normalize_rn(a, key_like), normalize_rn(b, key_like)
    if strict:
        return na == nb
    return na[0] == nb[0] and na[1] == nb[1]
