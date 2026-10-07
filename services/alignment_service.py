import io

import httpx
import librosa
import numpy as np
import soundfile as sf


async def _download_audio(url: str):
    """
    Downloads an audio file and converts it to mono audio
    at librosa's native sampling rate.
    """
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

    return y, sr


def _analyze_audio(y, sr):
    """
    Basic timing/rhythm analysis.
    Does NOT modify the audio.
    """

    duration = librosa.get_duration(
        y=y,
        sr=sr,
    )

    tempo, beat_frames = librosa.beat.beat_track(
        y=y,
        sr=sr,
    )

    beat_times = librosa.frames_to_time(
        beat_frames,
        sr=sr,
    )

    # librosa may return tempo as ndarray
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo.flat[0])
    else:
        tempo = float(tempo)

    return {
        "duration_seconds": round(float(duration), 3),
        "sample_rate": int(sr),
        "tempo_bpm": round(tempo, 3),
        "beat_count": int(len(beat_times)),
        "beat_times": [
            round(float(t), 3)
            for t in beat_times
        ],
    }


async def analyze_alignment(
    vocal_url: str,
    instrumental_url: str,
):
    """
    Compare the original vocal recording with the generated
    instrumental.

    IMPORTANT:
    This endpoint is diagnostic only.
    It does not time-stretch, pitch-shift or modify the vocal.
    """

    vocal, vocal_sr = await _download_audio(vocal_url)
    instrumental, instrumental_sr = await _download_audio(
        instrumental_url
    )

    vocal_analysis = _analyze_audio(
        vocal,
        vocal_sr,
    )

    instrumental_analysis = _analyze_audio(
        instrumental,
        instrumental_sr,
    )

    vocal_duration = vocal_analysis["duration_seconds"]
    instrumental_duration = instrumental_analysis["duration_seconds"]

    duration_difference = (
        instrumental_duration - vocal_duration
    )

    vocal_tempo = vocal_analysis["tempo_bpm"]
    instrumental_tempo = instrumental_analysis["tempo_bpm"]

    tempo_difference = (
        instrumental_tempo - vocal_tempo
    )

    return {
        "vocal": vocal_analysis,
        "instrumental": instrumental_analysis,

        "comparison": {
            "duration_difference_seconds": round(
                duration_difference,
                3,
            ),
            "tempo_difference_bpm": round(
                tempo_difference,
                3,
            ),
        },

        "note": (
            "Diagnostic analysis only. "
            "No audio has been modified."
        ),
    }
