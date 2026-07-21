"""FastAPI wrapper around the harmonic analyzer.

One upload endpoint, Pydantic response models, auto-generated Swagger UI at
``/docs``.  A static frontend (drop zone + results table) is served at ``/``.
"""

from __future__ import annotations

import os
import tempfile

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .analyzer import DEFAULT_DURATION_THRESHOLD, AnalysisError, analyze_score
from .explainer import explain_progression
from .models import AnalysisResponse

app = FastAPI(
    title="Harmonyx API",
    version="1.0.0",
    description=(
        "Send a score, get back a chord-by-chord Roman numeral analysis as "
        "structured JSON. Upload a MusicXML or MIDI file to `/analyze`.\n\n"
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


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness probe for deployment platforms (Railway / Fly.io)."""
    return {"status": "ok"}


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
