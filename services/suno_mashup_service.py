
import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"



DEFAULT_STYLE = (
    "Original vocal preservation, faithful vocal performance, "
    "professional studio mix with instrumental accompaniment. "

    "The first uploaded audio contains the ORIGINAL lead vocal. "
    "Treat this vocal recording as the primary performance "
    "and preserve it as faithfully as possible. "

    "Retain the singer's original vocal timbre, unique voice "
    "character, tone, natural texture, resonance, articulation, "
    "pronunciation, accent, breaths, vibrato and emotional expression. "

    "Preserve every original sung word exactly as performed. "
    "Do not rewrite, replace, omit, repeat or invent lyrics. "
    "Follow the original vocal recording for all words and phrasing. "

    "Keep the exact original melody, pitch contour, note durations, "
    "rhythm, tempo variations, pauses and vocal entrances. "
    "Avoid pitch correction, time stretching, vocal regeneration "
    "or any unnecessary changes to the lead vocal. "

    "The second uploaded audio is the INSTRUMENTAL ACCOMPANIMENT. "
    "Use it as supportive backing music and adapt its arrangement "
    "to the original vocal performance, not the other way around. "

    "Keep the original lead vocal clearly audible and dominant "
    "throughout the entire song. "
    "Do not generate a new singer, backing vocals, harmonies, "
    "choir, doubled vocals or additional vocal layers. "

    "Produce a complete vocal song, NOT an instrumental-only track. "
    "Blend the original vocal and instrumental into a cohesive, "
    "balanced professional studio production. "
    "Preserve the complete original vocal performance "
    "and finish with a natural musical ending."
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
