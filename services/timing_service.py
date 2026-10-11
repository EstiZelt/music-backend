
import gc
import io
import os
import tempfile

import httpx
import librosa
import numpy as np
import soundfile as sf


# Diagnostic mix settings.
# No pitch correction, time stretching or vocal shifting.
MIX_SAMPLE_RATE = 22050
VOCAL_GAIN = 1.0
INSTRUMENTAL_GAIN = 0.45

# Write small chunks instead of building a full mix in RAM.
CHUNK_SECONDS = 5


async def _download_audio(url: str):
    """
    Download and decode an audio file.

    The downloaded source file is not modified.
    The in-memory copy is converted to mono at
    the diagnostic mix sample rate.
    """
    async with httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=True,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        audio_data = response.content

    with io.BytesIO(audio_data) as audio_bytes:
        audio, sr = librosa.load(
            audio_bytes,
            sr=MIX_SAMPLE_RATE,
            mono=True,
            dtype=np.float32,
        )

    del audio_data, response
    gc.collect()

    if len(audio) == 0:
        raise ValueError("Downloaded audio is empty.")

    return audio, sr


def _get_chunk(audio, start, end):
    """
    Return a fixed-length audio chunk.

    Pad with silence when the track has ended.
    Never remove audio from the beginning.
    """
    chunk_length = end - start

    chunk = audio[start:end]

    if len(chunk) < chunk_length:
        chunk = np.pad(
            chunk,
            (0, chunk_length - len(chunk)),
        )

    return np.asarray(chunk, dtype=np.float32)


async def create_timing_test_mix(
    vocal_url: str,
    instrumental_url: str,
):
    """
    Create a diagnostic mix with no timing changes.

    IMPORTANT:
    - Original vocal starts at time zero.
    - No vocal samples are cut.
    - No pitch correction.
    - No time stretching.
    - No voice synthesis.
    - No timbre transformation algorithm.

    This is a listening test, not a final master.
    """

    vocal, vocal_sr = await _download_audio(
        vocal_url
    )

    instrumental, instrumental_sr = (
        await _download_audio(
            instrumental_url
        )
    )

    if vocal_sr != instrumental_sr:
        raise ValueError(
            "Audio sample rates do not match."
        )

    sr = vocal_sr

    vocal_length = len(vocal)
    instrumental_length = len(instrumental)

    target_length = max(
        vocal_length,
        instrumental_length,
    )

    chunk_samples = int(
        CHUNK_SECONDS * sr
    )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name

        # A fixed gain prevents clipping without
        # a second full-song normalization pass.
        # The original vocal is not overwritten.
        safe_master_gain = 0.65

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

                instrumental_chunk = _get_chunk(
                    instrumental,
                    start,
                    end,
                )

                mixed_chunk = (
                    vocal_chunk * VOCAL_GAIN
                    + instrumental_chunk * INSTRUMENTAL_GAIN
                )

                mixed_chunk *= safe_master_gain

                # Protect the exported WAV from clipping.
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
            "timing_shift_seconds": 0.0,
            "vocal_duration_seconds": round(
                vocal_length / sr, 3
            ),
            "instrumental_duration_seconds": round(
                instrumental_length / sr, 3
            ),
            "mix_duration_seconds": round(
                target_length / sr, 3
            ),
        }

    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    finally:
        del vocal, instrumental
        gc.collect()
