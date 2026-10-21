"""Experimental Voice endpoints against the existing apibox.erweima.ai account.

Provider support for /api/v1/voice/* is NOT verified. Use only with
explicit consent from the person whose voice is being enrolled.
"""
import os
from typing import Any, Literal
import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl

from datetime import datetime, timezone

voice_callbacks = []

router = APIRouter(prefix="/voice", tags=["Voice fingerprint (experimental)"])
BASE_URL = os.getenv("SUNO_BASE_URL", "https://apibox.erweima.ai").rstrip("/")


def _api_key() -> str:
    key = os.getenv("SUNO_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="SUNO_API_KEY is not configured")
    return key


async def _request(method: str, path: str, *, payload: dict | None = None,
                   params: dict | None = None) -> Any:
    headers = {"Authorization": f"Bearer {_api_key()}", "Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            response = await client.request(method, f"{BASE_URL}{path}",
                                            headers=headers, json=payload, params=params)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            provider_detail = exc.response.json()
        except ValueError:
            provider_detail = exc.response.text[:1000]
        raise HTTPException(status_code=502, detail={
            "provider_status": exc.response.status_code,
            "provider_response": provider_detail,
        }) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502,
                            detail=f"Voice provider connection failed: {type(exc).__name__}") from exc
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Voice provider returned non-JSON data") from exc


class VoiceValidateRequest(BaseModel):
    voiceUrl: HttpUrl
    vocalStartS: float = Field(default=0, ge=0)
    vocalEndS: float = Field(default=10, gt=0)
    language: str = "en"
    callBackUrl: HttpUrl


class VoiceGenerateRequest(BaseModel):
    taskId: str = Field(min_length=1)
    verifyUrl: HttpUrl
    voiceName: str = Field(min_length=1)
    description: str = ""
    style: str = ""
    singerSkillLevel: Literal["professional", "amateur", "beginner"] = "professional"
    callBackUrl: HttpUrl


class VoiceCheckRequest(BaseModel):
    taskId: str = Field(min_length=1)


@router.post("/validate")
async def validate_voice(body: VoiceValidateRequest):
    if body.vocalEndS <= body.vocalStartS:
        raise HTTPException(status_code=422, detail="vocalEndS must be greater than vocalStartS")
    return await _request("POST", "/api/v1/voice/validate", payload=body.model_dump(mode="json"))


@router.get("/validate-info")
async def voice_validate_info(
    task_id: str = Query(
        min_length=1,
        description="Voice validation task ID"
    )
):
    return await _request(
        "GET",
        "/api/v1/voice/validate-info",
        params={"taskId": task_id}
    )

@router.post("/callback")
async def voice_callback(payload: dict):
    event = {
        "received_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "payload": payload
    }

    voice_callbacks.append(event)

    # Keep only the latest 20 events
    if len(voice_callbacks) > 20:
        voice_callbacks.pop(0)

    return {"received": True}


@router.get("/callback-results")
async def get_voice_callback_results():
    return {
        "count": len(voice_callbacks),
        "events": voice_callbacks
    }

@router.post("/generate")
async def generate_voice(body: VoiceGenerateRequest):
    return await _request("POST", "/api/v1/voice/generate", payload=body.model_dump(mode="json"))


@router.get("/record-info")
async def voice_record_info(task_id: str = Query(min_length=1)):
    return await _request("GET", "/api/v1/voice/record-info", params={"taskId": task_id})


@router.post("/check-voice")
async def check_voice(body: VoiceCheckRequest):
    return await _request("POST", "/api/v1/voice/check-voice", payload=body.model_dump(mode="json"))
