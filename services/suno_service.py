import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")

SUNO_BASE_URL = "https://apibox.erweima.ai"


async def add_instrumental(
    upload_url: str,
    title: str = "My Song",
    tags: str = "professional studio arrangement, piano, strings, soft drums",
    negative_tags: str = "heavy metal, distorted vocals",
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

        # בשלב ה-POC נשתמש בכתובת זמנית.
        # בהמשך ניצור endpoint אמיתי אצלנו.
        "callBackUrl": "https://example.com/callback",

        "model": "V6",

        # אנחנו רוצים שהעיבוד ייצמד ככל האפשר לשירה
        "audioWeight": 1.0,

        # פחות חופש יצירתי בניסוי הראשון
        "styleWeight": 0.7,
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
