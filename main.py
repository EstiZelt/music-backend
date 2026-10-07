from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.suno_service import (
    add_instrumental,
    get_generation_details,
)

from services.alignment_service import analyze_alignment


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
