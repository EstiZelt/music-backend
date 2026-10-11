
import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"





DEFAULT_STYLE = (
    "CRITICAL: Preserve the EXACT ORIGINAL uploaded lead vocal "
    "recording with maximum fidelity. The singer's UNIQUE VOCAL "
    "FINGERPRINT and identity are SACRED and MUST remain unchanged. "
    "Retain the original vocal audio, timbre, formants, resonance, "
    "texture, accent, pronunciation, vibrato, breaths, emotion, "
    "lyrics, melody, phrasing, pitch and timing. "
    "NEVER regenerate, replace, imitate, resing, transform or "
    "resynthesize the singer's voice. NO voice modification, "
    "autotune, pitch shifting or artificial vocal enhancement. "
    "Preserve every original note, syllable, pause and imperfection. "
    "ONLY add professional instrumental accompaniment: expressive "
    "piano, warm strings, bass and tasteful rhythmic drums. "
    "Adapt ALL instruments to the ORIGINAL vocal, NEVER the reverse. "
    "No backing vocals, choir, harmonies, doubling or extra voices. "
    "Keep the original vocal dominant, complete and uninterrupted. "
    "Natural studio mix and beautiful ending. "
    "ORIGINAL VOCAL AUTHENTICITY OVERRIDES EVERYTHING."
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
