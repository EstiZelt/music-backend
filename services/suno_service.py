import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


async def add_instrumental(
    upload_url: str,
    title: str = "My Song",
    tags: str = (
        "professional studio accompaniment, "
        "supportive clean arrangement, "
        "piano, warm strings, subtle drums, "
        "follow the original melody, rhythm and phrasing accurately, "
        "leave musical space for the lead vocal, "
        "use the complete uploaded melody from beginning to end, "
        "preserve every musical phrase, "
        "do not omit or shorten any phrase, "
        "do not end the arrangement before the original melody is complete, "
        "follow the full structure of the uploaded audio"
    ),
    negative_tags: str = (
        "lead melody doubling, "
        "instrumental melody copying the vocal, "
        "busy countermelody, "
        "dense orchestration, "
        "solo instruments competing with the vocal, "
        "choir, backing vocals, background vocals, vocal harmonies, "
        "second voice, doubled vocals, layered vocals, "
        "call and response, vocal ad-libs, "
        "heavy drums, heavy metal, distorted vocals, "
        "truncated ending, "
        "early ending, "
        "omitted phrases, "
        "shortened structure, "
        "missing melody sections"
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
