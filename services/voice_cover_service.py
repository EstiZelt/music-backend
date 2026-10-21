
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


@router.get("/check-provider")
async def check_voice_cover_provider():
    path = "/api/music/voice-profile/cover"
    url = f"{BASE_URL}{path}"

    api_key = os.getenv("SUNO_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="SUNO_API_KEY is not configured"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    results = {}

    async with httpx.AsyncClient(timeout=20.0) as client:
        for method in ("OPTIONS", "GET"):
            try:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    follow_redirects=False,
                )

                results[method] = {
                    "status_code": response.status_code,
                    "allow": response.headers.get("allow"),
                    "content_type": response.headers.get(
                        "content-type"
                    ),
                    "body": response.text[:500],
                }

            except httpx.RequestError as exc:
                results[method] = {
                    "error": type(exc).__name__
                }

    statuses = [
        item.get("status_code")
        for item in results.values()
        if "status_code" in item
    ]

    if 405 in statuses:
        conclusion = (
            "Possible endpoint: method not allowed. "
            "POST support is not confirmed."
        )
    elif statuses and all(s == 404 for s in statuses):
        conclusion = (
            "Endpoint not found by these methods. "
            "POST availability remains unverified."
        )
    else:
        conclusion = (
            "Inconclusive. Inspect responses. "
            "No generation request was sent."
        )

    return {
        "provider": BASE_URL,
        "endpoint": path,
        "results": results,
        "conclusion": conclusion,
        "generation_started": False,
    }

