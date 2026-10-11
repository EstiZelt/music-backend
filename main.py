from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.suno_service import (
    add_instrumental,
    get_generation_details,
    generate_mashup,
    get_mashup_details,
)

from services.alignment_service import analyze_alignment
from services.timing_service import create_timing_test_mix


app = FastAPI(
    title="Music Backend",
    version="2.0.0"
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


class AlignmentRequest(BaseModel):
    vocal_url: str
    instrumental_url: str


class MashupRequest(BaseModel):
    vocal_url: str
    instrumental_url: str
    title: str = "My Mashup"


@app.get("/")
def health():
    return {
        "status": "online",
        "service": "music-backend"
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
            "data": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/song-status/{task_id}")
async def song_status(task_id: str):
    try:
        result = await get_generation_details(task_id)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
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
            "data": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post("/test-timing-mix")
async def test_timing_mix(request: AlignmentRequest):
    try:
        result = await create_timing_test_mix(
            vocal_url=request.vocal_url,
            instrumental_url=request.instrumental_url,
        )

        return FileResponse(
            path=result["file_path"],
            media_type="audio/wav",
            filename="timing_test_mix.wav",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/mashup")
async def create_mashup(request: MashupRequest):
    try:
        return await generate_mashup(
            vocal_url=request.vocal_url,
            instrumental_url=request.instrumental_url,
            title=request.title,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=e.response.text
        )


@app.get("/mashup-details/{task_id}")
async def mashup_details(task_id: str):
    try:
        return await get_mashup_details(task_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=e.response.text
        )
