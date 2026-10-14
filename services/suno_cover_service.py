
import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


DEFAULT_COVER_STYLE = (
    "ABSOLUTE PRIORITY: Preserve the EXACT ORIGINAL uploaded "
    "lead vocal recording and singer's UNIQUE VOCAL FINGERPRINT. "
    "Keep 100% of the original voice identity, timbre, formants, "
    "resonance, texture, accent, pronunciation, vibrato, breaths, "
    "emotion, melody, lyrics, phrasing and timing. "
    "NEVER regenerate, replace, imitate, resynthesize or re-sing "
    "the voice. Use the AUTHENTIC ORIGINAL vocal audio unchanged. "
    "Preserve every note, syllable, pause and natural imperfection. "
    "NO pitch correction unless absolutely essential and inaudible. "
    "Build rich professional piano, strings, bass and rhythmic "
    "drums AROUND the vocal, following its exact timing and melody. "
    "Original lead vocal always dominant. No additional voices. "
    "Transparent studio mixing, subtle EQ, compression and reverb. "
    "Keep the COMPLETE original performance and natural ending. "
    "VOCAL AUTHENTICITY OVERRIDES ALL PRODUCTION ENHANCEMENTS."
)

DEFAULT_COVER_NEGATIVE_TAGS = (
    "instrumental only, missing vocals, replacement singer, "
    "altered voice, synthetic vocals, re-sung vocals, "
    "autotune, robotic voice, backing vocals, choir, "
    "vocal harmonies, doubled vocals, vocal ad-libs, "
    "changed melody, changed phrasing, missing lyrics, "
    "missing phrases, competing melodies, "
    "instruments doubling lead vocal, heavy drums, "
    "distorted vocals, abrupt ending, truncated ending"
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
