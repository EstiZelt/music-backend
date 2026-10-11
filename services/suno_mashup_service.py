
import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


DEFAULT_STYLE = (
    "Vocal song with instrumental accompaniment. "
    "The lead vocal from the first uploaded audio must "
    "be clearly audible throughout the song. "
    "Use the second uploaded audio as backing music. "
    "Keep the original vocal melody, rhythm and phrasing. "
    "Do not produce an instrumental-only track. "
    "No backing singers, choir or additional vocal layers. "
    "Balanced professional studio mix."
)


async def generate_mashup(
    vocal_url: str,
    instrumental_url: str,
    title: str = "My Mashup",
    style: str = DEFAULT_STYLE,
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
