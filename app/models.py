"""Pydantic response models for the analysis API.

These drive both response validation and the auto-generated Swagger UI at
``/docs``, so the ``examples`` matter -- they are the demo surface.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ChordOut(BaseModel):
    measure: int = Field(..., description="1-indexed measure number.")
    beat: float = Field(..., description="Beat within the measure the harmony falls on.")
    pitches: List[str] = Field(..., description="Sounding pitches, e.g. ['G3','B3','D4'].")
    roman: str = Field(..., description="Roman numeral figure, e.g. 'I', 'V6', 'ii65'.")
    quality: str = Field(..., description="Chord quality: major, minor, diminished, ...")
    inversion: int = Field(..., description="0 = root position, 1 = first inversion, ...")

    model_config = {
        "json_schema_extra": {
            "example": {
                "measure": 1,
                "beat": 1,
                "pitches": ["G3", "B3", "D4"],
                "roman": "I",
                "quality": "major",
                "inversion": 0,
            }
        }
    }


class CadenceOut(BaseModel):
    measure: int = Field(..., description="Measure where the cadence resolves.")
    type: str = Field(..., description="authentic | plagal | half | deceptive")


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
                    },
                    {
                        "measure": 1,
                        "beat": 3,
                        "pitches": ["C4", "E4", "G4"],
                        "roman": "IV",
                        "quality": "major",
                        "inversion": 0,
                    },
                ],
                "cadences": [{"measure": 8, "type": "authentic"}],
                "explanation": None,
            }
        }
    }
