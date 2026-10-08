import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


async def add_instrumental(
    upload_url: str,
    title: str = "My Song",
    tags: str = (
        "Professional studio production built around the exact uploaded "
        "vocal performance. "
        "Preserve the original lead vocal identity, natural tone, "
        "melody, pitch contour, rhythm, phrasing, breaths, pauses, "
        "timing and emotional expression. "
        "Add a refined, warm piano-led accompaniment with gentle strings, "
        "soft bass and restrained percussion. "
        "All instruments must follow and support the existing vocal performance. "
        "Preserve the complete structure and every phrase through the natural "
        "final ending. "
        "Keep the original lead vocal clear, prominent and authentic."
        ),
    negative_tags: str = (
       "new lead singer, replaced vocals, altered vocal identity, "
        "vocal harmonies, backing vocals, choir, doubled vocals, "
        "ad-libs, excessive pitch correction, vocal rephrasing, "
        "changed melody, competing instrumental melodies, "
        "busy arrangement, missing phrases, truncated ending"
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

        # זמני בשלב ה-POC.
        # בהמשך נחליף ל-callback endpoint אמיתי אצלנו.
        "callBackUrl": "https://example.com/callback",

        "model": "V6",

        # שומרים על הנאמנות הגבוהה למקור
        "audioWeight": 1.0,

        # בניסוי הקודם 0.5 נתן תוצאה מדויקת ומסודרת יותר
        "styleWeight": 0.5,

        # כרגע לא מוסיפים יצירתיות חריגה
        "weirdnessConstraint": 0.0,

        # כרגע משאירים קבוע כדי לא לשנות כמה משתנים יחד
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
