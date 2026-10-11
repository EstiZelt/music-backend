
import gc
import os
import tempfile

import httpx
import librosa
import numpy as np
import soundfile as sf


MIX_SAMPLE_RATE = 22050

VOCAL_GAIN = 1.0
INSTRUMENTAL_GAIN = 0.45
MASTER_GAIN = 0.65

CHUNK_SECONDS = 5


async def _download_audio_preview(
    url: str,
    max_duration_seconds: float,
):
    """
    Download audio and decode only the preview section.

    The original remote file is not modified.
    The diagnostic copy is mono at 22050 Hz.
    """

    temp_source_path = None

    try:
        async with httpx.AsyncClient(
            timeout=120.0,
            follow_redirects=True,
        ) as client:

            async with client.stream(
                "GET",
                url,
            ) as response:

                response.raise_for_status()

                with tempfile.NamedTemporaryFile(
                    suffix=".mp3",
                    delete=False,
                ) as temp_file:

                    temp_source_path = temp_file.name

                    async for chunk in response.aiter_bytes():
                        temp_file.write(chunk)

        audio, sr = librosa.load(
            temp_source_path,
            sr=MIX_SAMPLE_RATE,
            mono=True,
            duration=max_duration_seconds,
            dtype=np.float32,
        )

        if len(audio) == 0:
            raise ValueError(
                "Downloaded audio is empty."
            )

        return audio, sr

    finally:
        if (
            temp_source_path
            and os.path.exists(temp_source_path)
        ):
            os.unlink(temp_source_path)


def _get_chunk(
    audio,
    start,
    end,
):
    """
    Read a fixed-size section.

    Missing samples are filled with silence.
    """

    chunk_length = end - start

    if end <= 0 or start >= len(audio):
        return np.zeros(
            chunk_length,
            dtype=np.float32,
        )

    safe_start = max(0, start)
    safe_end = min(len(audio), end)

    chunk = audio[safe_start:safe_end]

    result = np.zeros(
        chunk_length,
        dtype=np.float32,
    )

    destination_start = safe_start - start

    result[
        destination_start:
        destination_start + len(chunk)
    ] = chunk

    return result


async def create_timing_test_mix(
    vocal_url: str,
    instrumental_url: str,
    instrumental_delay_seconds: float = 0.0,
    preview_duration_seconds: float = 30.0,
):
    """
    Create a short timing test mix.

    - Vocal always starts at time zero.
    - Instrumental starts after the chosen delay.
    - No pitch correction.
    - No time stretching.
    - No vocal synthesis.
    - No vocal samples removed from the beginning.

    Diagnostic preview only.
    """

    if not 0 <= instrumental_delay_seconds <= 15:
        raise ValueError(
            "Instrumental delay must be 0-15 seconds."
        )

    if not 5 <= preview_duration_seconds <= 180:
        raise ValueError(
            "Preview duration must be 5-180 seconds."
        )

    sr = MIX_SAMPLE_RATE

    vocal = None
    instrumental = None
    temp_path = None

    try:
        vocal, vocal_sr = await _download_audio_preview(
            vocal_url,
            preview_duration_seconds,
        )

        # Only this much instrumental audio can
        # appear inside the requested preview.
        instrumental_duration = max(
            0.0,
            preview_duration_seconds
            - instrumental_delay_seconds,
        )

        if instrumental_duration > 0:
            instrumental, instrumental_sr = (
                await _download_audio_preview(
                    instrumental_url,
                    instrumental_duration,
                )
            )

            if instrumental_sr != sr:
                raise ValueError(
                    "Unexpected instrumental sample rate."
                )

        else:
            instrumental = np.zeros(
                0,
                dtype=np.float32,
            )

        if vocal_sr != sr:
            raise ValueError(
                "Unexpected vocal sample rate."
            )

        delay_samples = int(
            round(
                instrumental_delay_seconds * sr
            )
        )

        target_length = int(
            round(
                preview_duration_seconds * sr
            )
        )

        chunk_samples = int(
            CHUNK_SECONDS * sr
        )

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name

        with sf.SoundFile(
            temp_path,
            mode="w",
            samplerate=sr,
            channels=1,
            subtype="PCM_16",
            format="WAV",
        ) as output_file:

            for start in range(
                0,
                target_length,
                chunk_samples,
            ):
                end = min(
                    start + chunk_samples,
                    target_length,
                )

                vocal_chunk = _get_chunk(
                    vocal,
                    start,
                    end,
                )

                # Convert output positions into
                # instrumental source positions.
                instrumental_start = (
                    start - delay_samples
                )

                instrumental_end = (
                    end - delay_samples
                )

                instrumental_chunk = _get_chunk(
                    instrumental,
                    instrumental_start,
                    instrumental_end,
                )

                mixed_chunk = (
                    vocal_chunk * VOCAL_GAIN
                    + instrumental_chunk * INSTRUMENTAL_GAIN
                )

                mixed_chunk *= MASTER_GAIN

                np.clip(
                    mixed_chunk,
                    -1.0,
                    1.0,
                    out=mixed_chunk,
                )

                output_file.write(mixed_chunk)

        return {
            "file_path": temp_path,
            "sample_rate": sr,
            "instrumental_delay_seconds": (
                instrumental_delay_seconds
            ),
            "preview_duration_seconds": (
                preview_duration_seconds
            ),
        }

    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    finally:
        del vocal, instrumental
        gc.collect()
