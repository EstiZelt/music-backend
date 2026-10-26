
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from services.suno_service import (
    add_instrumental,
    get_generation_details,
    DEFAULT_TAGS,
    DEFAULT_NEGATIVE_TAGS,
)

from services.suno_cover_service import (
    generate_upload_cover,
    get_cover_generation_details,
    DEFAULT_COVER_STYLE,
    DEFAULT_COVER_NEGATIVE_TAGS,
)

from services.openai_service import analyze_song


app = FastAPI(
    title="Music Backend",
    version="2.2.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================
# REQUEST MODELS
# =====================================

class InstrumentalRequest(BaseModel):
    upload_url: str
    title: str = "POC Song"

    tags: str = Field(
        default=DEFAULT_TAGS,
        max_length=1000,
        description="Positive style prompt for Suno",
    )

    negative_tags: str = Field(
        default=DEFAULT_NEGATIVE_TAGS,
        max_length=500,
        description="Elements Suno should avoid",
    )

    lyrics: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional song lyrics",
    )


class UploadCoverRequest(BaseModel):
    upload_url: str
    title: str = "My Song"
    lyrics: str = ""

    tags: str = Field(
        default=DEFAULT_COVER_STYLE,
        max_length=1000,
        description="Positive style prompt for Suno Cover",
    )

    negative_tags: str = Field(
        default=DEFAULT_COVER_NEGATIVE_TAGS,
        max_length=500,
        description="Elements Suno Cover should avoid",
    )

    persona_id: str | None = None
    persona_model: str | None = None


class AnalyzeSongRequest(BaseModel):
    upload_url: str = Field(
        ...,
        description="Public HTTPS URL of an MP3 or WAV recording",
    )


class AutoSongRequest(BaseModel):
    upload_url: str
    title: str | None = None


# =====================================
# HEALTH CHECK
# =====================================

@app.get("/")
def health():
    return {
        "status": "online",
        "service": "music-backend",
    }


# =====================================
# ADD INSTRUMENTAL
# =====================================

@app.post("/add-instrumental")
async def create_instrumental(
    request: InstrumentalRequest
):
    try:
        result = await add_instrumental(
            upload_url=request.upload_url,
            title=request.title,
            tags=request.tags,
            negative_tags=request.negative_tags,
            lyrics=request.lyrics,
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


# =====================================
# SONG STATUS
# =====================================

@app.get("/song-status/{task_id}")
async def song_status(task_id: str):
    try:
        result = await get_generation_details(
            task_id
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


# =====================================
# UPLOAD COVER
# =====================================

@app.post("/upload-cover")
async def upload_cover_endpoint(
    request: UploadCoverRequest
):
    try:
        result = await generate_upload_cover(
            upload_url=request.upload_url,
            title=request.title,
            style=request.tags,
            negative_tags=request.negative_tags,
            lyrics=request.lyrics,
            persona_id=request.persona_id,
            persona_model=(
                request.persona_model or "voice_persona"
            ),
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=e.response.text,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

# =====================================
# COVER GENERATION DETAILS
# =====================================

@app.get("/cover-generation-details/{task_id}")
async def cover_generation_details_endpoint(
    task_id: str
):
    try:
        result = await get_cover_generation_details(
            task_id=task_id
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =====================================
# GPT SONG ANALYSIS
# =====================================

@app.post("/analyze-song")
async def analyze_song_endpoint(
    request: AnalyzeSongRequest
):
    try:
        result = await analyze_song(
            upload_url=request.upload_url
        )

        return {
            "success": True,
            "data": result,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except httpx.HTTPStatusError as e:
        error_body = e.response.text

        print(
            "OpenAI API error:",
            e.response.status_code,
            error_body[:2000],
        )

        raise HTTPException(
            status_code=502,
            detail={
                "status_code": e.response.status_code,
                "message": (
                    "OpenAI API request failed. "
                    "Check Render logs for the provider error."
                ),
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =====================================
# AUTOMATIC SONG CREATION
# GPT ANALYSIS -> SUNO
# =====================================

@app.post("/create-song-auto")
async def create_song_auto(
    request: AutoSongRequest
):
    try:
        analysis = await analyze_song(
            upload_url=request.upload_url
        )

        lyrics = analysis["lyrics"]

        title = (
            request.title
            or analysis.get("title")
            or "My Song"
        )

        tags = (
            analysis.get("tags")
            or DEFAULT_TAGS
        )

        negative_tags = (
            analysis.get("negative_tags")
            or DEFAULT_NEGATIVE_TAGS
        )

        result = await add_instrumental(
            upload_url=request.upload_url,
            title=title,
            lyrics=lyrics,
            tags=tags,
            negative_tags=negative_tags,
        )

        return {
            "success": True,
            "analysis": analysis,
            "generation": result,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=(
                f"External API error: "
                f"{e.response.status_code}"
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =====================================
# DISABLED FEATURES
# =====================================

# The following features remain disabled:
#
# /cover
# /analyze-alignment
# /test-timing-mix
# /mashup
# /mashup-details
#
# Related service modules have not been deleted.
# They can be enabled again when needed.
