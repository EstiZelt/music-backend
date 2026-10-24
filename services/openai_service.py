
import os
import json
import base64
import asyncio
import tempfile
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx


logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-audio")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

MAX_AUDIO_BYTES = 20 * 1024 * 1024
MAX_ATTEMPTS = 2


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

WORDLESS SINGING AND HUMMING:
- A recording may contain meaningful lyrics, wordless
  singing, humming, or a mixture of these.
- All these are valid musical performances.
- If the singer sings syllables such as "na na",
  "la la", "ma ma" or "du du", transcribe the
  audible syllables as sung.
- Do not invent meaningful words for wordless singing.
- Do not replace audible singing with
  [Instrumental Break] or [Instrumental Outro].
- If the recording contains only closed-mouth humming
  with no identifiable syllables, lyrics may be empty.
- Empty lyrics for pure humming is a valid result,
  not an error.
- Never invent lyrics merely to fill the lyrics field.
- The uploaded audio remains the musical reference.

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
- Use [Instrumental Break] only for genuinely
  instrumental passages without audible singing.
- Never replace sung words or sung syllables with music.

ARRANGEMENT:
- Decide automatically whether a tasteful instrumental
  intro, transition or outro would improve the song.
- Add only musically appropriate sections.
- Never interrupt or replace an original vocal phrase.
- Keep all original vocal entrances and repetitions.
- Prefer no additional transition when uncertain.
- For wordless singing and humming, arrange instruments
  around the exact uploaded melody and timing.

TITLE:
- Infer a short, meaningful title from the song.
- Prefer Hebrew script for Hebrew or Yiddish songs.
- For wordless recordings, use a short neutral title.
- Do not invent a title unrelated to the recording.

TAGS:
- Professional instrumental arrangement.
- Preserve the original singer's identity, timbre,
  pronunciation, melody, phrasing and timing.
- Use supportive piano, strings, bass and drums.
- Keep the original singer dominant.
- Follow the original vocal entrances.
- For humming, preserve the hummed melody and
  build accompaniment around it.

NEGATIVE TAGS:
- No replacement singer, changed lyrics, missing words,
  skipped verses, choir, backing vocals, vocal doubling,
  altered melody or cut-off ending.
- No invented lyrics for wordless recordings.

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

All four fields must be strings.
The lyrics string may be empty for pure humming.

Do not include Markdown.
Do not include explanations outside JSON.
If you cannot reliably identify the lyrics, do not
invent a complete transcription.
"""


async def convert_audio_to_wav(audio_bytes: bytes) -> bytes:
    """Convert browser audio formats to 24 kHz mono WAV."""

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "input_audio"
        output_path = Path(temp_dir) / "output.wav"

        input_path.write_bytes(audio_bytes)

        try:
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-nostdin",
                "-y",
                "-i", str(input_path),
                "-vn",
                "-ac", "1",
                "-ar", "24000",
                "-c:a", "pcm_s16le",
                str(output_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "FFmpeg is not installed on the server"
            ) from exc

        try:
            _, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=90,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise ValueError(
                "Audio conversion timed out"
            ) from exc

        if process.returncode != 0 or not output_path.exists():
            details = stderr.decode(
                "utf-8",
                errors="replace",
            )[:500]
            raise ValueError(
                f"Audio conversion failed: {details}"
            )

        wav_bytes = output_path.read_bytes()

        if len(wav_bytes) > MAX_AUDIO_BYTES:
            raise ValueError(
                "Converted WAV exceeds 20 MB limit"
            )

        return wav_bytes


def parse_song_response(result: dict) -> dict:
    """Parse and validate the four required GPT fields."""

    choices = result.get("choices") or []

    if not choices:
        raise ValueError("OpenAI returned no choices")

    choice = choices[0]
    finish_reason = choice.get("finish_reason")

    if finish_reason == "length":
        raise ValueError(
            "OpenAI response was truncated"
        )

    if finish_reason not in (None, "stop"):
        raise ValueError(
            f"OpenAI finished unexpectedly: {finish_reason}"
        )

    message = choice.get("message") or {}
    content = message.get("content")

    if not isinstance(content, str):
        raise ValueError(
            "OpenAI returned no text content"
        )

    content = content.strip()

    if content.startswith("```"):
        parts = content.split("\n", 1)

        if len(parts) == 2:
            content = parts[1].rsplit(
                "```", 1
            )[0].strip()

    try:
        song = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "OpenAI returned invalid JSON"
        ) from exc

    if not isinstance(song, dict):
        raise ValueError(
            "OpenAI JSON must be an object"
        )

    required_fields = (
        "title",
        "lyrics",
        "tags",
        "negative_tags",
    )

    for field in required_fields:
        if not isinstance(song.get(field), str):
            raise ValueError(
                f"OpenAI response missing valid field: {field}"
            )

    if not song["title"].strip():
        song["title"] = "My Melody"

    # IMPORTANT:
    # Empty lyrics are valid for pure humming.
    # Do not reject them.

    if len(song["lyrics"]) > 5000:
        raise ValueError(
            "Lyrics exceed 5000 characters"
        )

    if len(song["tags"]) > 1000:
        raise ValueError(
            "Tags exceed 1000 characters"
        )

    if len(song["negative_tags"]) > 500:
        raise ValueError(
            "Negative tags exceed 500 characters"
        )

    return {
        field: song[field]
        for field in required_fields
    }


async def analyze_song(upload_url: str) -> dict:

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured"
        )

    parsed = urlparse(upload_url)

    if parsed.scheme != "https":
        raise ValueError(
            "upload_url must use HTTPS"
        )

    allowed_host = os.getenv("AUDIO_PUBLIC_HOST")

    if not allowed_host:
        raise RuntimeError(
            "AUDIO_PUBLIC_HOST is not configured"
        )

    if parsed.hostname != allowed_host:
        raise ValueError(
            "Audio URL host is not allowed"
        )

    async with httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=False,
    ) as client:

        response = await client.get(upload_url)
        response.raise_for_status()

        audio_bytes = response.content

        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise ValueError(
                "Audio file exceeds 20 MB limit"
            )

        audio_bytes = await convert_audio_to_wav(
            audio_bytes
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
                                "Analyze this complete song recording "
                                "and return the Suno-ready JSON. "
                                "The recording may contain real words, "
                                "wordless syllables, humming, or a mix. "
                                "Do not invent lyrics for humming. "
                                "Return all four JSON string fields. "
                                "Empty lyrics are valid for pure humming."
                            ),
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": "wav",
                            },
                        },
                    ],
                },
            ],
        }

        last_error = None

        for attempt in range(1, MAX_ATTEMPTS + 1):

            try:
                api_response = await client.post(
                    OPENAI_URL,
                    headers={
                        "Authorization": (
                            f"Bearer {OPENAI_API_KEY}"
                        ),
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=240.0,
                )

                api_response.raise_for_status()

                result = api_response.json()

                return parse_song_response(result)

            except ValueError as exc:
                last_error = exc

                logger.warning(
                    "OpenAI transcription validation failed "
                    "on attempt %s/%s: %s",
                    attempt,
                    MAX_ATTEMPTS,
                    str(exc),
                )

                if attempt < MAX_ATTEMPTS:
                    continue

    raise RuntimeError(
        "OpenAI could not return a valid song analysis "
        f"after {MAX_ATTEMPTS} attempts: {last_error}"
    )
