
import os
import json
import base64
import asyncio
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import httpx


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-audio")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

MAX_AUDIO_BYTES = 20 * 1024 * 1024


SYSTEM_PROMPT = """
You are a meticulous audio-to-phonetic-lyrics transcriber.

Listen to the ENTIRE recording from the first audible
sung sound through the last.

The actual audio is the ONLY authority.

Return exactly four JSON string fields:
title, lyrics, tags, negative_tags.


ABSOLUTE TRANSCRIPTION PRIORITY:

- Transcribe the SOUNDS actually sung, not an
  expected or familiar text.

- The lyrics field MUST use LATIN LETTERS ONLY
  for every sung word.

- No Hebrew, Yiddish, Arabic, Cyrillic or other
  non-Latin script in lyrics.

- This is PHONETIC TRANSLITERATION,
  NOT TRANSLATION INTO ENGLISH.

- Preserve every audible consonant, vowel,
  syllable, diphthong, word ending, stress
  pattern, repetition and sung vocal entrance.

- Preserve the individual singer's Hasidic,
  Ashkenazi or Yiddish accent exactly.

- Never normalize pronunciation to Israeli
  Hebrew, Litvish or dictionary pronunciation.

- Write the guttural Hebrew Chet sound as KH,
  never CH.

- Do not replace other sounds with KH unless
  that sound is actually heard.

- Never correct, complete, infer or substitute
  a word based on familiar lyrics or texts.

- If the singer sings nonsense syllables such
  as la-la, du-du or na-na, transcribe those
  actual syllables exactly as heard.

- Do NOT replace sung syllables with an
  instrumental section.

- Never invent meaningful words.

- For indistinct sounds, transcribe only what
  is reliably audible.

- Mark genuinely unintelligible short portions
  as [Unclear].

- Never silently omit verses, repetitions,
  vocalizations or endings.

- Never make repeated words consistent if the
  singer actually varies their pronunciation.


STRUCTURE:

- Preserve the exact original order and
  repetitions.

- Use section markers such as:
  [Verse 1], [Chorus], [Bridge],
  [Instrumental Break].

- Use [Instrumental Break] only when no
  singing is audible.

- Do not add imagined verses, lyrics,
  intros or outros.


TITLE:

- Give a short title grounded in the recording.

- Hebrew script is permitted in title,
  but NOT in lyrics.


TAGS:

- Describe a polished instrumental arrangement
  around the uploaded original lead vocal.

- Support its timing, entrances and melody.

- Favor piano, warm strings, bass and steady
  drums where appropriate.

- Keep the original singer clearly dominant.

- Preserve all sung sections.


NEGATIVE TAGS:

- No new or replacement singer.
- No voice imitation.
- No choir or backing vocals.
- No vocal doubling.
- No changed lyrics or pronunciation.
- No skipped words or altered melody.
- No missing sections or cut-off ending.


LIMITS:

- lyrics: maximum 5000 characters.
- tags: maximum 1000 characters.
- negative_tags: maximum 500 characters.


Return ONLY a valid JSON object:

{
  "title": "",
  "lyrics": "",
  "tags": "",
  "negative_tags": ""
}

No Markdown fences.
No additional explanation.
"""


async def convert_audio_to_wav(audio_bytes: bytes) -> bytes:
    """
    Convert browser audio formats to 24 kHz mono WAV.

    Supports WebM, MP3, WAV, M4A and other formats
    recognized by FFmpeg.
    """

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
                timeout=90
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
                errors="replace"
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

    # Trusted Supabase Storage hostname.
    # Configure AUDIO_PUBLIC_HOST in Render
    # without https:// or paths.

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
        follow_redirects=False
    ) as client:

        response = await client.get(upload_url)
        response.raise_for_status()

        audio_bytes = response.content

        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise ValueError(
                "Audio file exceeds 20 MB limit"
            )

        # Convert actual audio content to WAV.
        # Do not rely on the URL extension.

        audio_bytes = await convert_audio_to_wav(
            audio_bytes
        )

        audio_format = "wav"

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
                                "Listen to the complete audio. "
                                "Transcribe the exact sung sounds "
                                "using Latin letters only. "
                                "Preserve every syllable, vowel, "
                                "consonant, pronunciation variation "
                                "and repetition. "
                                "Do not translate, normalize or "
                                "invent lyrics. "
                                "Return the Suno-ready JSON."
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

    content = result["choices"][0]["message"]["content"]

    content = content.strip()

    # Remove Markdown fences if present.

    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit(
            "```", 1
        )[0].strip()

    try:
        song = json.loads(content)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "OpenAI returned invalid JSON"
        ) from exc

    required_fields = (
        "title",
        "lyrics",
        "tags",
        "negative_tags",
    )

    for field in required_fields:

        if not isinstance(song.get(field), str):
            raise RuntimeError(
                f"OpenAI response missing valid field: {field}"
            )

    if not song["title"].strip():
        raise RuntimeError(
            "OpenAI returned an empty title"
        )

    if not song["lyrics"].strip():
        raise RuntimeError(
            "OpenAI returned empty lyrics"
        )

    # Reject non-Latin letters in lyrics.
    # Never silently rewrite pronunciation.

    for character in song["lyrics"]:

        if (
            character.isalpha()
            and "LATIN" not in unicodedata.name(
                character, ""
            )
        ):
            raise RuntimeError(
                "OpenAI returned non-Latin lyrics; "
                "please retry transcription"
            )

    if len(song["lyrics"]) > 5000:
        raise RuntimeError(
            "Lyrics exceed 5000 characters"
        )

    if len(song["tags"]) > 1000:
        raise RuntimeError(
            "Tags exceed 1000 characters"
        )

    if len(song["negative_tags"]) > 500:
        raise RuntimeError(
            "Negative tags exceed 500 characters"
        )

    return {
        field: song[field]
        for field in required_fields
    }
