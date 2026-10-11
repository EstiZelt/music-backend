
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

import os

from services.suno_service import (
    add_instrumental,
    get_generation_details,
    upload_cover,
)

from services.alignment_service import analyze_alignment
from services.timing_service import create_timing_test_mix


app = FastAPI(
    title="Music Backend",
    version="2.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InstrumentalRequest(BaseModel):
    upload_url: str
    title: str = "POC Song"


class CoverRequest(BaseModel):
    upload_url: str
    title: str = "POC Cover"
    style: str = (
        "Professional studio instrumental accompaniment, "
        "warm piano, expressive strings, gentle rhythmic drums, "
        "faithful to the uploaded melody and musical phrasing, "
        "preserve the original song structure and natural timing, "
        "supportive arrangement with no competing lead melody"
    )


class AlignmentRequest(BaseModel):
    vocal_url: str
    instrumental_url: str


class TimingMixRequest(BaseModel):
    vocal_url: str
    instrumental_url: str

    instrumental_delay_seconds: float = Field(
        default=0.0,
        ge=0.0,
        le=15.0,
        description=(
            "Delay the instrumental in seconds. "
            "The original vocal is never shifted."
        ),
    )

    preview_duration_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=180.0,
        description=(
            "Length of the diagnostic mix in seconds."
        ),
    )


@app.get("/")
def health():
    return {
        "status": "online",
        "service": "music-backend",
    }


@app.post("/add-instrumental")
async def create_instrumental(request: InstrumentalRequest):
    try:
        result = await add_instrumental(
            upload_url=request.upload_url,
            title=request.title,
        )

        return {
            "success": True,
            "data": result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/cover")
async def create_cover(request: CoverRequest):
    try:
        result = await upload_cover(
            upload_url=request.upload_url,
            title=request.title,
            style=request.style,
        )

        return {
            "success": True,
            "data": result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get("/song-status/{task_id}")
async def song_status(task_id: str):
    try:
        result = await get_generation_details(task_id)

        return {
            "success": True,
            "data": result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/analyze-alignment")
async def alignment_analysis(request: AlignmentRequest):
    try:
        result = await analyze_alignment(
            vocal_url=request.vocal_url,
            instrumental_url=request.instrumental_url,
        )

        return {
            "success": True,
            "data": result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/test-timing-mix")
async def test_timing_mix(request: TimingMixRequest):
    try:
        result = await create_timing_test_mix(
            vocal_url=request.vocal_url,
            instrumental_url=request.instrumental_url,
            instrumental_delay_seconds=(
                request.instrumental_delay_seconds
            ),
            preview_duration_seconds=(
                request.preview_duration_seconds
            ),
        )

        return FileResponse(
            path=result["file_path"],
            media_type="audio/wav",
            filename="timing_test_mix.wav",
            background=BackgroundTask(
                os.unlink,
                result["file_path"],
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
