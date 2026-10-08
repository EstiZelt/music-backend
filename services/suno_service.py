import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


async def add_instrumental(
    upload_url: str,
    title: str = "My Song",
    tags: str = (
            "Premium professional studio production, emotionally rich "
            "and elegant musical arrangement. "
            "Preserve the uploaded lead vocal as the central performance, "
            "retaining its natural vocal character, original melody, "
            "phrasing and timing. "
            "Create beautiful piano harmonies, expressive warm strings, "
            "rounded bass, subtle acoustic percussion and tasteful "
            "orchestral textures. "
            "Begin with an intimate arrangement and gradually build "
            "toward powerful but balanced musical climaxes. "
            "Follow the singer's natural pauses and expressive timing. "
            "Maintain the complete vocal performance and provide a "
            "satisfying musical resolution after the final vocal phrase."
),

negative_tags: str = (
            "replacement singer, synthetic lead voice, backing vocals, "
            "choir, vocal harmonies, doubled lead, vocal ad-libs, "
            "aggressive pitch correction, instrumental lead melody, "
            "excessive orchestration, overpowering drums, "
            "abrupt ending, missing vocal sections"
),
):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

    url = f"{SUNO_BASE_URL}/api/v1/generate/add-instrumental"

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
    }
    if len(final_negative_tags) > 500:
        raise ValueError(
            f"negative_tags exceeds Suno limit: "
            f"{len(final_negative_tags)}/500 characters"
        )
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
