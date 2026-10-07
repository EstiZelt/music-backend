import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")

SUNO_BASE_URL = "https://apibox.erweima.ai"


async def async def add_instrumental(
    upload_url: str,
    title: str = "My Song",
    tags: str = (
        "professional studio accompaniment, "
        "supportive arrangement, "
        "piano, warm strings, subtle drums, "
        "follow the exact original vocal melody, rhythm and phrasing, "
        "keep the lead vocal clearly dominant, "
        "instruments should support the vocal without competing with it, "
        "clean restrained arrangement"
    ),
    negative_tags: str = (
        "backing vocals, background vocals, vocal harmonies, choir, "
        "second voice, doubled vocals, layered vocals, "
        "call and response, vocal ad-libs, "
        "countermelody vocals, "
        "instruments doubling the lead melody, "
        "busy arrangement, orchestral overload, "
        "heavy drums, heavy metal, distorted vocals"
    ),
):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

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

        # זמני בשלב ה-POC
        "callBackUrl": "https://example.com/callback",

        "model": "V6",

        # מקסימום נאמנות לאודיו המקורי
        "audioWeight": 1.0,

        # פחות כוח לסגנון כדי שהעיבוד לא ישתלט על השירה
        "styleWeight": 0.5,

        # לא רוצים כרגע יצירתיות מוזרה
        "weirdnessConstraint": 0.0,

        # משאירים כרגע כפי שכבר הוכח שעובד
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
