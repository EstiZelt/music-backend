
import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"




DEFAULT_STYLE = (
    "Vocal song with instrumental accompaniment. "
    "Preserve the ORIGINAL lead vocal from the first audio "
    "as faithfully as possible. Keep the singer's exact "
    "voice timbre, natural tone, texture, accent, pronunciation, "
    "vibrato, breaths and emotional expression. "
    "Preserve ALL original sung words without changing, "
    "omitting, repeating or inventing lyrics. "
    "Keep the original melody, pitch, rhythm, phrasing, "
    "pauses and timing. No vocal regeneration, replacement, "
    "pitch correction or time stretching. "
    "Use the second audio ONLY as instrumental backing, "
    "following the original vocal performance. "
    "Keep the original singer clearly audible and dominant. "
    "No new singer, backing vocals, choir, harmonies, "
    "vocal doubling or additional voices. "
    "Produce a complete song WITH the original vocals, "
    "NOT an instrumental-only track. "
    "Create a balanced studio mix with a natural ending."
)




async def generate_mashup(
    vocal_url: str,
    instrumental_url: str,
    title: str = "My Mashup",
    style: str = DEFAULT_STYLE,
    lyrics: str | None = None
):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

    if not vocal_url or not instrumental_url:
        raise ValueError(
            "Both vocal_url and instrumental_url are required"
        )

    url = f"{SUNO_BASE_URL}/api/v1/generate/mashup"

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "uploadUrlList": [
            vocal_url,
            instrumental_url,
        ],
        "title": title,
        "style": style,
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
    if lyrics:
            payload["lyrics"] = lyrics

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
            f"Suno Mashup API error: {result}"
        )

    return result


async def get_mashup_details(task_id: str):
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
    return response.json()
