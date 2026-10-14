import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"







DEFAULT_TAGS = (
    "FULL SONG WITH ORIGINAL VOCALS AND INSTRUMENTAL BACKING. "
    "MANDATORY: The final audio MUST contain the original recorded "
    "lead singer, clearly audible throughout the entire song. "
    "NEVER produce an instrumental-only track. "
    "Use the EXACT uploaded vocal recording, not a recreated voice. "
    "Preserve vocal identity, timbre, formants, melody, pitch, "
    "timing, breaths, phrasing and emotion. "
    "STRICT PRONUNCIATION: Keep every original word, syllable, "
    "consonant, vowel and accent exactly as sung. "
    "Never replace, regenerate, correct, omit or re-sing vocals. "
    "ONE SINGER ONLY. Absolutely NO choir, backing singers, "
    "harmonies, doubled vocals or additional voices. "
    "Keep every sung phrase from first to last without cuts. "
    "Add rich piano, warm strings, bass and steady drums BEHIND "
    "the original vocal. Keep the lead voice clear and dominant. "
    "Professional balanced mix and smooth ending."
)

DEFAULT_NEGATIVE_TAGS = (
    "regenerated vocals, re-singing, replacement singer, voice cloning, "
    "changed timbre, formants or pitch, mispronunciation, altered vowels, "
    "consonants, syllables, words, endings, stress or accent, missing words, "
    "invented lyrics, phonetic reconstruction, autotune, pitch correction, "
    "time stretching, vocal effects, choir, backing vocals, harmonies, "
    "doubling, layered voices, second singer, group singing, ad-libs, "
    "humming, vocal synthesis, omitted phrases, cut vocals, instrumental only"
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
