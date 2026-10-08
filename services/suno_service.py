import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


async def add_instrumental(
    upload_url: str,
    title: str = "My Song",
    tags: str = (
    "Professional high-end studio production of the uploaded "
    "original vocal recording. "
    "Use the original singer's voice as the lead vocal throughout "
    "the entire song. "
    "Preserve the original vocal timbre, identity, tone, "
    "natural expression, phrasing, breaths and emotional delivery. "
    "Apply only gentle, transparent pitch correction to inaccurate notes, "
    "while preserving natural pitch transitions and vibrato. "
    "Keep the original vocal melody, timing and rhythmic phrasing. "
    "Create a beautiful, rich, emotionally expressive musical arrangement "
    "built around the existing vocal performance. "
    "Warm acoustic piano, lush strings, supportive bass, "
    "subtle percussion and elegant harmonic development. "
    "Professional vocal mixing, natural EQ, gentle compression, "
    "subtle reverb, balanced instrumentation and polished mastering. "
    "Keep the original lead vocal clear, warm, natural "
    "and prominent in the final mix. "
    "Preserve every vocal phrase and the complete original song structure. "
    "Finish naturally after the final vocal phrase."
),

negative_tags: str = (
    "voice replacement, new singer, synthetic vocals, "
    "changed vocal identity, altered vocal timbre, "
    "re-sung vocals, vocal regeneration, "
    "heavy autotune, robotic pitch correction, "
    "unnatural pitch transitions, excessive vocal processing, "
    "backing vocals, choir, vocal harmonies, "
    "doubled vocals, layered vocals, vocal ad-libs, "
    "changed melody, changed phrasing, missing vocal phrases, "
    "instrumental melody doubling the singer, "
    "competing instrumental solos, overpowering instruments, "
    "harsh compression, excessive reverb, distorted vocals, "
    "abrupt ending, truncated ending, early fade-out"
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
