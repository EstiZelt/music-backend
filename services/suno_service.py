import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


DEFAULT_TAGS = (
    "ABSOLUTE PRIORITY: Use the EXACT original uploaded vocal "
    "recording as the sole lead vocal track in the final mix. "
    "Preserve its authentic waveform, unique vocal fingerprint, "
    "tone color, timbre, formants, resonance, texture, pitch "
    "contours, intonation, vibrato, microtonal nuances, dynamics, "
    "breaths, accent, pronunciation, consonants, vowels, syllables, "
    "lyrics, melody, phrasing, timing and emotion with total fidelity. "
    "Retain every original sung phrase, verse, chorus and ending "
    "in full and in order. Vocal authenticity takes precedence "
    "over all production decisions. Apply only gentle background "
    "noise reduction and transparent minimal EQ. Build a beautiful, "
    "full, rich instrumental arrangement with piano, warm strings, "
    "bass and rhythmic drums, precisely supporting the original "
    "vocal entrances, pauses and tempo. Keep the singer clear "
    "and dominant, with elegant instrumental intro, transitions "
    "and outro."
)

DEFAULT_NEGATIVE_TAGS = (
    "AI vocal regeneration, re-singing, replacement voice, "
    "voice cloning, altered vocal identity, changed timbre, "
    "formant shifting, pitch correction, autotune, altered "
    "intonation, vibrato or pitch contours, changed pronunciation, "
    "accent, vowels, consonants or lyrics, missing words, "
    "skipped verses, time stretching, vocal effects, choir, "
    "backing vocals, harmonies, doubled vocals, extra singers, "
    "instrumental replacement of vocals, overpowering instruments, "
    "aggressive denoising, cut vocals"
)

assert len(DEFAULT_TAGS) <= 1000
assert len(DEFAULT_NEGATIVE_TAGS) <= 500


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
        "styleWeight": 0.3,
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
