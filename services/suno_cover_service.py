
import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


DEFAULT_COVER_STYLE = (
    "Professional studio production using the original lead vocal. "
    "Preserve the singer's exact vocal timbre, identity, melody, "
    "phrasing, timing, breaths and emotion. "
    "Apply gentle, natural pitch correction without changing the voice. "
    "Add rich piano, warm strings, soft bass and subtle drums. "
    "Follow the vocal closely with supportive harmonies, no competing melodies. "
    "Professional vocal mix, EQ, compression, reverb and mastering. "
    "Deliver the complete song with original vocals and a natural ending."
)

DEFAULT_COVER_NEGATIVE_TAGS = (
    "instrumental only, missing vocals, replacement singer, "
    "altered voice, synthetic vocals, re-sung vocals, "
    "heavy autotune, robotic pitch correction, "
    "backing vocals, choir, vocal harmonies, doubled vocals, "
    "vocal ad-libs, changed melody, changed phrasing, "
    "missing phrases, competing instrumental solos, "
    "instruments doubling the vocal melody, "
    "overpowering drums, distorted vocals, "
    "abrupt ending, truncated ending"
)


async def generate_upload_cover(
    upload_url: str,
    title: str = "My Song",
    style: str = DEFAULT_COVER_STYLE,
    negative_tags: str = DEFAULT_COVER_NEGATIVE_TAGS,
    lyrics: str = "",
):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

    if len(negative_tags) > 500:
        raise ValueError(
            f"negative_tags exceeds Suno limit: "
            f"{len(negative_tags)}/500 characters"
        )

    if len(style) > 1000:
        raise ValueError(
            f"style exceeds Suno limit: "
            f"{len(style)}/1000 characters"
        )

    url = f"{SUNO_BASE_URL}/api/v1/generate/upload-cover"

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "uploadUrl": upload_url,
        "title": title,
        "style": style,
        "negativeTags": negative_tags,
        "instrumental": False,
        "callBackUrl": os.getenv(
            "SUNO_CALLBACK_URL",
            "https://example.com/callback"
        ),
        "model": "V6",
        "audioWeight": 1.0,
        "styleWeight": 0.5,
        "weirdnessConstraint": 0.0,
        "variety": 0,
        "lyrics": lyrics,
    }

    if lyrics.strip():
    payload["lyrics"] = lyrics.strip()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    response.raise_for_status()
    result = response.json()

    if result.get("code") != 200:
        raise RuntimeError(
            f"Suno Cover generation failed: {result}"
        )

    return result


async def get_cover_generation_details(task_id: str):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

    url = f"{SUNO_BASE_URL}/api/v1/generate/record-info"

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
    }

    params = {
        "taskId": task_id
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            url,
            headers=headers,
            params=params,
        )

    response.raise_for_status()
    result = response.json()

    if result.get("code") != 200:
        raise RuntimeError(
            f"Suno Cover status request failed: {result}"
        )

    return result
