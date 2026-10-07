import io
import tempfile

import httpx
import librosa
import numpy as np
import soundfile as sf



async def _download_audio(url: str):
    async with httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=True,
    ) as client:
        response = await client.get(url)

    response.raise_for_status()

    audio_bytes = io.BytesIO(response.content)

    y, sr = librosa.load(
        audio_bytes,
        sr=None,
        mono=True,
    )

    return y.astype(np.float32), sr


def _resample_if_needed(y, sr, target_sr):
    if sr == target_sr:
        return y

    return librosa.resample(
        y,
        orig_sr=sr,
        target_sr=target_sr,
    ).astype(np.float32)


def _shift_audio(y, sr, shift_seconds):
    """
    Shift the vocal in time WITHOUT pitch shifting
    and WITHOUT time stretching.

    Positive shift_seconds:
        vocal is moved later.

    Negative shift_seconds:
        vocal is moved earlier.
    """

    samples = int(
        round(abs(shift_seconds) * sr)
    )

    if samples == 0:
        return y.copy()

    if shift_seconds > 0:
        # Move vocal later by adding silence at start.
        return np.concatenate(
            [
                np.zeros(samples, dtype=np.float32),
                y,
            ]
        )

    # Move vocal earlier by removing audio from the beginning.
    # This is used only for this diagnostic POC.
    if samples >= len(y):
        return np.zeros_like(y)

    return y[samples:]


def _normalize_for_mix(y):
    peak = np.max(np.abs(y))

    if peak > 0.98:
        y = y / peak * 0.98

    return y.astype(np.float32)


async def create_timing_test_mix(
    vocal_url: str,
    instrumental_url: str,
):
    """
    POC ONLY.

    Creates a test mix while preserving the original vocal waveform.

    IMPORTANT:
    - no pitch correction
    - no time stretching
    - no voice synthesis
    - no timbre transformation

    For this first test we apply only the robust global timing offset
    observed in our alignment analysis.

    We intentionally do NOT use the suspicious local DTW jumps.
    """

    vocal, vocal_sr = await _download_audio(
        vocal_url
    )

    instrumental, instrumental_sr = (
        await _download_audio(
            instrumental_url
        )
    )

    # Use the instrumental sample rate for the mix.
    vocal = _resample_if_needed(
        vocal,
        vocal_sr,
        instrumental_sr,
    )

    sr = instrumental_sr

    # From our reliable alignment analysis:
    # median shift = -0.372 seconds.
    #
    # The instrumental target occurs about 0.372 sec earlier,
    # therefore move the vocal earlier by that amount.
    timing_shift_seconds = -0.372

    shifted_vocal = _shift_audio(
        vocal,
        sr,
        timing_shift_seconds,
    )

    # Make both tracks the same length.
    target_length = max(
        len(shifted_vocal),
        len(instrumental),
    )

    if len(shifted_vocal) < target_length:
        shifted_vocal = np.pad(
            shifted_vocal,
            (
                0,
                target_length - len(shifted_vocal),
            ),
        )

    if len(instrumental) < target_length:
        instrumental = np.pad(
            instrumental,
            (
                0,
                target_length - len(instrumental),
            ),
        )

    # Keep vocal clearly dominant for evaluation.
    vocal_gain = 1.0
    instrumental_gain = 0.45

    mix = (
        shifted_vocal * vocal_gain
        + instrumental * instrumental_gain
    )

    mix = _normalize_for_mix(mix)

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False,
    )

    temp_file.close()

    sf.write(
        temp_file.name,
        mix,
        sr,
        subtype="PCM_16",
    )

    return {
        "file_path": temp_file.name,
        "sample_rate": sr,
        "timing_shift_seconds": timing_shift_seconds,
    }


    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
