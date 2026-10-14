import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"



DEFAULT_TAGS = (
    "Professional studio song production based on the uploaded vocal performance. "
    "PRIMARY GOAL: retain the recognizable original singer, natural vocal timbre, "
    "accent, pronunciation, exact lyrics, melody and phrasing. "
    "Keep the original lead vocal as the sole singer, without re-singing or changing words. "
    "Clean and polished vocal sound with gentle noise reduction, transparent EQ "
    "and natural compression. "
    "Create a complete, clearly audible, moderately rich instrumental arrangement "
    "with piano, warm strings, bass and steady rhythmic drums. "
    "Instruments must support the vocal throughout the song, with balanced volume "
    "and no competing melodies. "
    "Maintain natural vocal expression, consistent accompaniment, clear intelligible "
    "words, professional mixing and a smooth musical ending."
)


DEFAULT_NEGATIVE_TAGS = (
    "replacement singer, synthetic vocals, altered vocal identity, "
    "changed timbre, wrong pronunciation, changed lyrics, missing words, "
    "re-singing, heavy autotune, choir, backing vocals, vocal harmonies, "
    "doubled vocals, second singer, instrumental only, weak accompaniment, "
    "sparse arrangement, excessive orchestration, loud instruments, "
    "background noise, hiss, distortion, muddy mix, abrupt ending, cut vocals"
)


async def add_instrumental(
    upload_url: str,
    title: str = "My Song",
    tags: str = DEFAULT_TAGS,
    negative_tags: str = DEFAULT_NEGATIVE_TAGS,
    lyrics: str | None = None,
):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

    if len(negative_tags) > 500:
        raise ValueError(
            f"negative_tags exceeds Suno limit: "
            f"{len(negative_tags)}/500 characters"
        )

    url = f"{SUNO_BASE_URL}/api/v1/generate/add-instrumental"

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "uploadUrl": upload_url,
        "title": title,
        "tags": tags,
        "negativeTags": negative_tags,
        "callBackUrl": "https://example.com/callback",

        "model": "V6",
        "audioWeight": 1.0,
        "styleWeight": 0.1,
        "weirdnessConstraint": 0.0,
        "variety": 0,
    }

    if lyrics and lyrics.strip():
        if len(lyrics) > 5000:
            raise ValueError(
                "lyrics exceeds Suno V6 limit: 5000 characters"
            )
        payload["lyrics"] = lyrics

    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    response.raise_for_status()
    return response.json()


async def get_generation_details(task_id: str):
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

async def upload_cover(
    upload_url: str,
    title: str = "My Song Cover",
    style: str = (
        "Professional studio instrumental accompaniment, "
        "warm piano, expressive strings, gentle rhythmic drums, "
        "faithful to the uploaded melody and musical phrasing, "
        "preserve the original song structure and natural timing, "
        "supportive arrangement with no competing lead melody"
    ),
):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

    url = f"{SUNO_BASE_URL}/api/v1/generate/upload-cover"

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "uploadUrl": upload_url,
        "title": title,
        "style": style,
        "negativeTags": (
            "vocals, lead singer, backing vocals, choir, "
            "vocal harmonies, second voice, doubled vocals, "
            "busy countermelody, instruments doubling the vocal melody, "
            "heavy drums, truncated ending"
        ),
        "instrumental": True,
        "model": "V6",
        "callBackUrl": "https://example.com/callback",
        "audioWeight": 1.0,
        "styleWeight": 0.5,
        "weirdnessConstraint": 0.0,
        "variety": 0,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    response.raise_for_status()
    return response.json()
