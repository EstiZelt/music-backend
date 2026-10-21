
import os
import json
import base64
import httpx
from urllib.parse import urlparse

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-audio")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

MAX_AUDIO_BYTES = 20 * 1024 * 1024

SYSTEM_PROMPT = """
You are an expert music transcription specialist for
Hebrew, Yiddish, Hasidic and Ashkenazi songs.

Listen to the COMPLETE uploaded audio.

Your task is to prepare exactly four fields for Suno:
title, lyrics, tags, negative_tags.

TRANSCRIPTION:
- Identify every meaningful sung word.
- Preserve every verse, chorus, line and repetition.
- Preserve the singer's actual dialect.
- Never convert Hasidic pronunciation into Litvish.
- Correct obvious accidental word omissions only when
  strongly supported by other occurrences and context.
- For unclear Yiddish, use real Yiddish vocabulary and
  grammar. Never invent nonsense words.
- Never fabricate lyrics to fill unclear passages.

PRONUNCIATION:
- Write lyrics in Latin letters.
- Preserve the original vowels, consonants and accent.
- Use KH for Hebrew guttural Chet, not English CH.
- Example: prefer Tapukhei over Tapuchei when the
  recording contains the Hebrew guttural sound.
- Keep repeated words consistent with the dominant
  pronunciation of the song.
- Do not normalize authentic dialect differences.

STRUCTURE:
- Identify verses, choruses and repeated sections
  from the recording itself.
- Preserve the complete order of the original song.
- Use tags such as [Verse 1], [Chorus], [Bridge].
- Replace wordless "du du", "na na" passages with
  [Instrumental Break] or [Instrumental Outro].
- Never replace meaningful sung words with music.

ARRANGEMENT:
- Decide automatically whether a tasteful instrumental
  intro, transition or outro would improve the song.
- Add only musically appropriate sections.
- Never interrupt or replace an original vocal phrase.
- Keep all original vocal entrances and repetitions.
- Prefer no additional transition when uncertain.

TITLE:
- Infer a short, meaningful title from the song.
- Prefer Hebrew script for Hebrew or Yiddish songs.
- Do not invent a title unrelated to the recording.

TAGS:
- Professional instrumental arrangement.
- Preserve the original singer's identity, timbre,
  pronunciation, melody, phrasing and timing.
- Use supportive piano, strings, bass and drums.
- Keep the original singer dominant.
- Follow the original vocal entrances.

NEGATIVE TAGS:
- No replacement singer, changed lyrics, missing words,
  skipped verses, choir, backing vocals, vocal doubling,
  altered melody or cut-off ending.

LIMITS:
- tags: maximum 1000 characters.
- negative_tags: maximum 500 characters.
- lyrics: maximum 5000 characters.

Return ONLY a valid JSON object:
{
  "title": "",
  "lyrics": "",
  "tags": "",
  "negative_tags": ""
}

Do not include Markdown.
Do not include explanations outside JSON.
If you cannot reliably identify the lyrics, do not
invent a complete transcription.
"""


async def analyze_song(upload_url: str) -> dict:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    parsed = urlparse(upload_url)

    if parsed.scheme != "https":
        raise ValueError("upload_url must use HTTPS")

    # Configure this in Render to your public R2 host,
    # for example: pub-xxxx.r2.dev
    allowed_host = os.getenv("AUDIO_PUBLIC_HOST")

    if not allowed_host:
        raise RuntimeError("AUDIO_PUBLIC_HOST is not configured")

    if parsed.hostname != allowed_host:
        raise ValueError("Audio URL host is not allowed")

    async with httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=False
    ) as client:
        response = await client.get(upload_url)
        response.raise_for_status()

        audio_bytes = response.content

        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise ValueError("Audio file exceeds 20 MB limit")

        path = parsed.path.lower()

        if path.endswith(".mp3"):
            audio_format = "mp3"
        elif path.endswith(".wav"):
            audio_format = "wav"
        else:
            raise ValueError(
                "For this endpoint, use an MP3 or WAV audio URL"
            )

        audio_base64 = base64.b64encode(
            audio_bytes
        ).decode("utf-8")

        payload = {
            "model": OPENAI_MODEL,
            "modalities": ["text"],
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Listen to the entire recording. "
                                "Return the complete phonetic Latin transcription "
                                "and a Hebrew song title as JSON."
                            ),
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": audio_format,
                            },
                        },
                    ],
                },
            ],
        }

        api_response = await client.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=240.0,
        )

        api_response.raise_for_status()
        result = api_response.json()

    usage = result.get("usage", {})

    print("OPENAI MODEL:", result.get("model"))
    print("OPENAI USAGE:", usage)

    content = result["choices"][0]["message"]["content"]

    # The model should return JSON, but may occasionally
    # wrap it in Markdown fences.
    content = content.strip()

    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0].strip()

    try:
        song = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "OpenAI returned invalid JSON"
        ) from exc

    
    required_fields = ("title", "lyrics")

    for field in required_fields:
        if not isinstance(song.get(field), str):
            raise RuntimeError(
                f"OpenAI response missing valid field: {field}"
            )

    if not song["title"].strip():
        raise RuntimeError("OpenAI returned an empty title")

    if not song["lyrics"].strip():
        raise RuntimeError("OpenAI returned empty lyrics")

    if len(song["lyrics"]) > 5000:
        raise RuntimeError("Lyrics exceed 5000 characters")

    return {
        "title": song["title"],
        "lyrics": song["lyrics"]
    }
