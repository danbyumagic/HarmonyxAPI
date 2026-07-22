"""Pydantic request/response models for the Harmonyx API.

These drive both validation and the auto-generated Swagger UI at ``/docs``,
so the ``examples`` matter -- they are the demo surface.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ChordOut(BaseModel):
    measure: int = Field(..., description="1-indexed measure number.")
    beat: float = Field(..., description="Beat within the measure the harmony falls on.")
    pitches: List[str] = Field(..., description="Sounding pitches, e.g. ['G3','B3','D4'].")
    roman: str = Field(..., description="Roman numeral figure, e.g. 'I', 'V6', 'ii65'.")
    quality: str = Field(..., description="Chord quality: major, minor, diminished, ...")
    inversion: int = Field(..., description="0 = root position, 1 = first inversion, ...")
    fermata: bool = Field(False, description="Whether this harmony falls under a fermata (phrase end).")

    model_config = {
        "json_schema_extra": {
            "example": {
                "measure": 1,
                "beat": 1,
                "pitches": ["G3", "B3", "D4"],
                "roman": "I",
                "quality": "major",
                "inversion": 0,
                "fermata": False,
            }
        }
    }


class CadenceOut(BaseModel):
    measure: int = Field(..., description="Measure where the cadence resolves.")
    type: str = Field(..., description="PAC | IAC | plagal | half | deceptive")


class AnalysisResponse(BaseModel):
    key: str = Field(..., description="Detected key, e.g. 'G major'.")
    confidence: float = Field(..., description="Key-detection certainty in [0, 1].")
    chords: List[ChordOut]
    cadences: List[CadenceOut]
    explanation: Optional[str] = Field(
        None,
        description="Plain-English walkthrough of the progression. "
        "Present only when explanation was requested and an LLM key is configured.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "G major",
                "confidence": 0.91,
                "chords": [
                    {
                        "measure": 1,
                        "beat": 1,
                        "pitches": ["G3", "B3", "D4"],
                        "roman": "I",
                        "quality": "major",
                        "inversion": 0,
                        "fermata": False,
                    },
                    {
                        "measure": 1,
                        "beat": 3,
                        "pitches": ["C4", "E4", "G4"],
                        "roman": "IV",
                        "quality": "major",
                        "inversion": 0,
                        "fermata": True,
                    },
                ],
                "cadences": [{"measure": 8, "type": "PAC"}],
                "explanation": None,
            }
        }
    }


class GenerateRequest(BaseModel):
    """Body for ``POST /generate``: Roman numerals → four-part MusicXML."""

    key: str = Field(..., description="Key, e.g. 'C major' or 'A minor'.", examples=["C major"])
    progression: List[str] = Field(
        ...,
        min_length=1,
        description="Roman-numeral figures in order, e.g. ['I', 'IV', 'V', 'I'].",
    )
    time_signature: str = Field(
        "4/4",
        description="Time signature for the realized score.",
    )
    soprano: Optional[List[Optional[int]]] = Field(
        None,
        description=(
            "Optional MIDI pitches for the soprano, one per chord. "
            "null leaves that beat free. Length must match progression when set."
        ),
    )

    @field_validator("progression")
    @classmethod
    def _figures_nonempty(cls, value: List[str]) -> List[str]:
        if any(not (f and str(f).strip()) for f in value):
            raise ValueError("progression figures must be non-empty strings")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "C major",
                "progression": ["I", "IV", "V", "I"],
                "time_signature": "4/4",
                "soprano": None,
            }
        }
    }


class PlaybackEvent(BaseModel):
    """One note for browser playback (block chords share the same beat)."""

    beat: float = Field(..., description="Onset in quarter-note beats from the start.")
    midi: int = Field(..., description="MIDI note number.")
    duration: float = Field(1.0, description="Length in quarter-note beats.")


class PlaybackPayload(BaseModel):
    tempo_bpm: int = Field(75, description="Playback tempo in beats per minute.")
    events: List[PlaybackEvent]


class GenerateResponse(BaseModel):
    """Successful realization: the input progression plus MusicXML text."""

    key: str
    progression: List[str]
    time_signature: str
    musicxml: str = Field(..., description="Four-part SATB score as MusicXML text.")
    playback: PlaybackPayload = Field(
        ...,
        description="Block-chord note events for simple Web Audio playback.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "C major",
                "progression": ["I", "IV", "V", "I"],
                "time_signature": "4/4",
                "musicxml": "<?xml version='1.0' ...",
                "playback": {
                    "tempo_bpm": 75,
                    "events": [
                        {"beat": 0, "midi": 72, "duration": 1.0},
                        {"beat": 0, "midi": 64, "duration": 1.0},
                    ],
                },
            }
        }
    }


class SopranoOptionsRequest(BaseModel):
    """Body for ``POST /generate/soprano-options``."""

    key: str = Field(..., description="Key, e.g. 'C major' or 'A minor'.", examples=["C major"])
    progression: List[str] = Field(
        ...,
        min_length=1,
        description="Roman-numeral figures in order, e.g. ['I', 'IV', 'V', 'I'].",
    )
    count: int = Field(
        3,
        ge=1,
        le=10,
        description=(
            "Number of distinct soprano-line options to return "
            "(default 3, max 10)."
        ),
    )

    @field_validator("progression")
    @classmethod
    def _figures_nonempty(cls, value: List[str]) -> List[str]:
        if any(not (f and str(f).strip()) for f in value):
            raise ValueError("progression figures must be non-empty strings")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {"key": "C major", "progression": ["I", "IV", "V", "I"]}
        }
    }


class SopranoOption(BaseModel):
    soprano: List[int] = Field(..., description="MIDI pitches, one per chord.")
    pitches: List[str] = Field(..., description="Same pitches as spelled names, e.g. 'C5'.")


class SopranoOptionsResponse(BaseModel):
    """Up to 3 distinct soprano-line options, best (lowest-cost) first."""

    options: List[SopranoOption]

    model_config = {
        "json_schema_extra": {
            "example": {
                "options": [
                    {"soprano": [72, 72, 71, 72], "pitches": ["C5", "C5", "B4", "C5"]},
                    {"soprano": [64, 65, 62, 64], "pitches": ["E4", "F4", "D4", "E4"]},
                ]
            }
        }
    }


class RomanAlternativesRequest(BaseModel):
    """Body for ``POST /generate/roman-alternatives``."""

    key: str = Field(..., description="Key, e.g. 'C major' or 'A minor'.", examples=["C major"])
    progression: List[str] = Field(
        ...,
        min_length=1,
        description="Roman-numeral figures in order, e.g. ['I', 'IV', 'V', 'I'].",
    )
    index: int = Field(..., ge=0, description="Index of the slot to suggest alternatives for.")
    locked: Optional[dict[int, str]] = Field(
        None, description="Map of index -> required figure for other slots."
    )
    cadence: Optional[Literal["PAC", "HC"]] = Field(
        None, description="If set, alternatives must preserve this cadence shape."
    )

    @field_validator("progression")
    @classmethod
    def _figures_nonempty(cls, value: List[str]) -> List[str]:
        if any(not (f and str(f).strip()) for f in value):
            raise ValueError("progression figures must be non-empty strings")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "C major",
                "progression": ["I", "IV", "V", "I"],
                "index": 1,
            }
        }
    }


class RomanAlternative(BaseModel):
    figure: str = Field(..., description="Candidate Roman-numeral figure.")
    label: str = Field(..., description="Short human-readable description of the edit.")


class RomanAlternativesResponse(BaseModel):
    """Up to 6 theory-valid replacement figures for one progression slot."""

    alternatives: List[RomanAlternative]

    model_config = {
        "json_schema_extra": {
            "example": {
                "alternatives": [
                    {"figure": "V", "label": "Use dominant"},
                    {"figure": "ii", "label": "Beat 2: IV → ii"},
                ]
            }
        }
    }


class ProgressionRequest(BaseModel):
    """Body for ``POST /progression``: idiomatic Roman-numeral list (Layer 1)."""

    key: str = Field(..., description="Key, e.g. 'C major' or 'A minor'.", examples=["C major"])
    length: int = Field(
        8,
        ge=1,
        le=64,
        description="Number of chords to generate (PAC needs >= 2).",
    )
    locked: Optional[dict[int, str]] = Field(
        None,
        description=(
            "Optional map of chord index → Roman figure that must appear "
            "at that slot (e.g. {\"1\": \"IV\"})."
        ),
    )
    cadence: str = Field(
        "PAC",
        description='Cadence type: "PAC" (V|V7→I/i) or "HC" (ends on V).',
    )
    seed: Optional[int] = Field(
        None,
        description="If set, generation is deterministic for the same inputs.",
    )
    spice: int = Field(
        0,
        ge=0,
        le=3,
        description=(
            "Color knob 0–3 (default 0 = student-safe, no secondary dominants). "
            "2+ allows V/V, V7/V, V6/V; 3 also V/vi and V/ii (major) or minor analogues. "
            "Ignored when style is set (style wins)."
        ),
    )
    style: Optional[str] = Field(
        None,
        description=(
            'Optional preset: "student" (spice 0), "hymnal" (1), "spicy" (2). '
            "When set, overrides spice."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "C major",
                "length": 8,
                "locked": {"1": "IV"},
                "cadence": "PAC",
                "seed": 42,
                "spice": 0,
                "style": None,
            }
        }
    }


class ProgressionResponse(BaseModel):
    """Generated Roman-numeral progression."""

    key: str
    length: int
    cadence: str
    seed: Optional[int] = None
    spice: int = 0
    style: Optional[str] = None
    progression: List[str] = Field(..., description="Roman-numeral figures in order.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "C major",
                "length": 8,
                "cadence": "PAC",
                "seed": 42,
                "spice": 0,
                "style": "student",
                "progression": ["I", "IV", "ii6", "V", "I", "vi", "V7", "I"],
            }
        }
    }
