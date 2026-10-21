
import os
import httpx
from urllib.parse import urlparse, unquote

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-transcribe")

OPENAI_URL = "https://api.openai.com/v1/audio/transcriptions"

MAX_AUDIO_BYTES = 20 * 1024 * 1024

TRANSCRIPTION_PROMPT = """
The recording is a Hasidic song in Hebrew, Yiddish,
or a mixture of both.

Transcribe ALL sung words from beginning to end.
Preserve the actual Hasidic/Ashkenazi pronunciation,
including vowels, consonants, syllables and repetitions.

Do not normalize to modern Israeli or Litvish pronunciation.
Do not omit repeated verses or choruses.
Do not invent missing or unclear words.
Use authentic Yiddish vocabulary where appropriate.

Prefer phonetic Latin spelling suitable for Suno.
Represent the guttural Hebrew Chet with KH, not CH.
Preserve the singer's actual pronunciation, not the
standard spelling of the original Hebrew words.
"""

async def analyze_song(upload_url: str) -> dict:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    parsed = urlparse(upload_url)

    if parsed.scheme != "https":
        raise ValueError("upload_url must use HTTPS")

    allowed_host = os.getenv("AUDIO_PUBLIC_HOST")

    if not allowed_host:
        raise RuntimeError("AUDIO_PUBLIC_HOST is not configured")

    if parsed.hostname != allowed_host.lower():
        raise ValueError("Audio URL host is not allowed")

    path = unquote(parsed.path).lower()

    if path.endswith(".mp3"):
        content_type = "audio/mpeg"
        extension = "mp3"
    elif path.endswith(".wav"):
        content_type = "audio/wav"
        extension = "wav"
    else:
        raise ValueError("Only MP3 and WAV files are supported")

    async with httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=False
    ) as client:

        # Download the original recording
        async with client.stream("GET", upload_url) as response:
            response.raise_for_status()

            chunks = []
            total_bytes = 0

            async for chunk in response.aiter_bytes():
                total_bytes += len(chunk)

                if total_bytes > MAX_AUDIO_BYTES:
                    raise ValueError(
                        "Audio file exceeds 20 MB limit"
                    )

                chunks.append(chunk)

            audio_bytes = b"".join(chunks)

        if not audio_bytes:
            raise ValueError("Audio file is empty")

        # One transcription request only
        api_response = await client.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            },
            data={
                "model": OPENAI_MODEL,
                "prompt": TRANSCRIPTION_PROMPT,
                "response_format": "json"
            },
            files={
                "file": (
                    f"recording.{extension}",
                    audio_bytes,
                    content_type
                )
            },
            timeout=240.0
        )

        api_response.raise_for_status()
        result = api_response.json()

    lyrics = result.get("text", "").strip()

    if not lyrics:
        raise RuntimeError("OpenAI returned empty transcription")

    # The transcription API does not return a song title.
    # This placeholder avoids an additional paid AI call.
    title = "שיר ללא כותרת"

    print("OPENAI MODEL:", OPENAI_MODEL)
    print("OPENAI USAGE:", result.get("usage", {}))

    return {
        "title": title,
        "lyrics": lyrics
    }
