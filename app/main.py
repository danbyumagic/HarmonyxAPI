"""FastAPI wrapper around the harmonic analyzer and chorale generator.

Upload endpoints for analysis, JSON endpoints for generation, Pydantic models
for Swagger at ``/docs``. A static frontend is served at ``/``.
"""

from __future__ import annotations

import os
import tempfile

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .analyzer import DEFAULT_DURATION_THRESHOLD, AnalysisError, analyze_score
from .explainer import explain_progression
from .generation.grammar import (
    GrammarError,
    generate_progression,
    resolve_spice_and_style,
)
from .generation.realize import (
    DEFAULT_PLAYBACK_TEMPO_BPM,
    RealizationError,
    check_soprano,
    playback_from_voicings,
    realize,
    satb_voicings_from_score,
    soprano_alternatives,
)
from .generation.chords import midi_to_name
from .models import (
    AnalysisResponse,
    GenerateRequest,
    GenerateResponse,
    PlaybackPayload,
    ProgressionRequest,
    ProgressionResponse,
    SopranoOptionsRequest,
    SopranoOptionsResponse,
)

app = FastAPI(
    title="Harmonyx API",
    version="1.0.0",
    description=(
        "Two-way harmony tool: **analyze** a score to Roman numerals "
        "(`POST /analyze`), **propose** an idiomatic progression "
        "(`POST /progression`), or **realize** RNs as four-part SATB MusicXML "
        "(`POST /generate`).\n\n"
        "**v1 scope:** four-part chorale texture in a single major/minor key, "
        "no modulation."
    ),
)

# music21 infers format from the file extension; keep the accepted set tight
# so we give a clear error rather than letting the parser fail obscurely.
SUPPORTED_EXTENSIONS = {".xml", ".musicxml", ".mxl", ".mid", ".midi"}


@app.post("/analyze", response_model=AnalysisResponse, tags=["analysis"])
async def analyze(
    file: UploadFile = File(..., description="A MusicXML or MIDI score."),
    duration_threshold: float = Query(
        DEFAULT_DURATION_THRESHOLD,
        ge=0.0,
        description="Minimum slice duration (in quarter lengths) to keep. "
        "Slices shorter than this are treated as passing motion and dropped.",
    ),
    explain: bool = Query(
        False,
        description="If true and an LLM key is configured, include a "
        "plain-English walkthrough of the progression.",
    ),
) -> AnalysisResponse:
    """Analyze an uploaded score and return its harmonic analysis."""
    ext = _extension(file.filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{ext or file.filename}'. "
                f"Expected one of: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
            ),
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # music21's converter works from a path; write the upload to a temp file
    # (preserving the extension so the format is inferred correctly).
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            result = analyze_score(tmp_path, duration_threshold=duration_threshold)
        except AnalysisError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    payload = result.to_dict()
    if explain:
        payload["explanation"] = explain_progression(result)

    return AnalysisResponse(**payload)


@app.post("/progression", response_model=ProgressionResponse, tags=["generation"])
async def progression(body: ProgressionRequest) -> ProgressionResponse:
    """Generate an idiomatic Roman-numeral progression (Layer 1 grammar).

    Honors optional locked slots and forces a PAC or HC ending. Pass the
    returned ``progression`` to ``POST /generate`` to realize SATB MusicXML.
    """
    try:
        effective_spice, norm_style = resolve_spice_and_style(
            spice=body.spice, style=body.style
        )
        figures = generate_progression(
            body.key,
            length=body.length,
            locked=body.locked,
            cadence=body.cadence,
            seed=body.seed,
            spice=effective_spice,
        )
    except GrammarError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "grammar_failed", "message": str(exc)},
        ) from exc

    return ProgressionResponse(
        key=body.key,
        length=body.length,
        cadence=body.cadence.upper(),
        seed=body.seed,
        spice=effective_spice,
        style=norm_style,
        progression=figures,
    )


@app.post("/generate", response_model=GenerateResponse, tags=["generation"])
async def generate(body: GenerateRequest) -> GenerateResponse:
    """Realize a Roman-numeral progression as a four-part SATB MusicXML score.

    Optional ``soprano`` MIDI pitches must be chord tones of their paired
    figures; mismatches return **422** with per-beat detail.
    """
    if body.soprano is not None:
        if len(body.soprano) != len(body.progression):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "soprano_length_mismatch",
                    "message": "soprano list length must match progression length",
                    "progression_length": len(body.progression),
                    "soprano_length": len(body.soprano),
                },
            )
        mismatches = check_soprano(body.progression, body.key, body.soprano)
        if mismatches:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "incompatible_soprano",
                    "message": "one or more soprano pitches are not chord tones",
                    "mismatches": mismatches,
                },
            )

    try:
        score = realize(
            body.progression,
            body.key,
            soprano=body.soprano,
            time_signature=body.time_signature,
        )
    except RealizationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "realization_failed", "message": str(exc)},
        ) from exc
    except Exception as exc:  # music21 / RN parse failures, etc.
        raise HTTPException(
            status_code=422,
            detail={"error": "realization_failed", "message": str(exc)},
        ) from exc

    musicxml = _score_to_musicxml_text(score)
    voicings = satb_voicings_from_score(score)
    playback = PlaybackPayload(
        **playback_from_voicings(voicings, tempo_bpm=DEFAULT_PLAYBACK_TEMPO_BPM)
    )
    return GenerateResponse(
        key=body.key,
        progression=body.progression,
        time_signature=body.time_signature,
        musicxml=musicxml,
        playback=playback,
    )


@app.post(
    "/generate/soprano-options",
    response_model=SopranoOptionsResponse,
    tags=["generation"],
)
async def generate_soprano_options(body: SopranoOptionsRequest) -> SopranoOptionsResponse:
    """Up to 3 distinct soprano-line options for a progression, best first.

    Lightweight preview (pitches only, no MusicXML) -- finalize a chosen
    option into a full score via ``POST /generate``'s ``soprano`` param.
    """
    try:
        options = soprano_alternatives(body.progression, body.key, n=3)
    except RealizationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "realization_failed", "message": str(exc)},
        ) from exc
    except Exception as exc:  # music21 / RN parse failures, etc.
        raise HTTPException(
            status_code=422,
            detail={"error": "realization_failed", "message": str(exc)},
        ) from exc

    return SopranoOptionsResponse(
        options=[
            {"soprano": s, "pitches": [midi_to_name(m) for m in s]}
            for s in options
        ]
    )


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness probe for deployment platforms (Railway / Fly.io)."""
    return {"status": "ok"}


def _score_to_musicxml_text(score) -> str:
    """Serialize a music21 Score to MusicXML text via a temp file (path required)."""
    tmp_path = None
    written_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tmp:
            tmp_path = tmp.name
        # music21 may rewrite the path / extension; prefer the returned path.
        written = score.write("musicxml", fp=tmp_path)
        written_path = str(written) if written is not None else tmp_path
        with open(written_path, encoding="utf-8") as fh:
            return fh.read()
    finally:
        for p in {tmp_path, written_path}:
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass


def _extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return filename[filename.rfind(".") :].lower()


# Serve the static frontend. Mounted last so it doesn't shadow the API routes.
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
