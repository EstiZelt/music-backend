
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

router = APIRouter(
    prefix="/voice-cover",
    tags=["Voice Cover Experiment"]
)

BASE_URL = "https://apibox.erweima.ai"


class UploadSourceRequest(BaseModel):
    file_url: HttpUrl
    file_name: str = "original-song.mp3"
    model: str = "suno-v6"


@router.post("/upload-source")
async def upload_source(body: UploadSourceRequest):
    api_key = os.getenv("SUNO_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="SUNO_API_KEY is not configured"
        )

    payload = {
        "model": body.model,
        "file_url": str(body.file_url),
        "file_name": body.file_name,
        "upload_type": "file_upload"
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{BASE_URL}/api/music/upload-source",
                headers={
                    "Authorization": f"Bearer {api_key}"
                },
                json=payload
            )
            response.raise_for_status()
            result = response.json()

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "provider_status": exc.response.status_code,
                "provider_response": exc.response.text[:1000]
            }
        )
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Provider error: {type(exc).__name__}"
        )

    if result.get("code") not in (None, 200):
        raise HTTPException(
            status_code=502,
            detail=result
        )

    return result
