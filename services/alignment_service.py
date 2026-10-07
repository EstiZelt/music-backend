import io

import httpx
import librosa
import numpy as np


async def _download_audio(url: str):
    """
    Download audio and decode it as mono.
    No audio modification is performed.
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


def _basic_analysis(y, sr):
    duration = librosa.get_duration(y=y, sr=sr)

    tempo, beat_frames = librosa.beat.beat_track(
        y=y,
        sr=sr,
    )

    beat_times = librosa.frames_to_time(
        beat_frames,
        sr=sr,
    )

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


def _prepare_chroma(y, sr, target_sr=22050):
    """
    Create a musical representation for alignment.

    We use chroma instead of raw waveform because the vocal and
    instrumental have very different timbres, but should share
    related pitch/harmonic movement.
    """

    if sr != target_sr:
        y = librosa.resample(
            y,
            orig_sr=sr,
            target_sr=target_sr,
        )
        sr = target_sr

    # Harmonic component reduces the influence of percussion.
    y_harmonic = librosa.effects.harmonic(y)

    hop_length = 512

    chroma = librosa.feature.chroma_cqt(
        y=y_harmonic,
        sr=sr,
        hop_length=hop_length,
    )

    return chroma, sr, hop_length


def _calculate_local_alignment(
    vocal,
    vocal_sr,
    instrumental,
    instrumental_sr,
):
    """
    Estimate local time correspondence between the original vocal
    and the generated instrumental using chroma + DTW.

    IMPORTANT:
    This is diagnostic only.
    It does not modify either audio file.
    """

    vocal_chroma, vocal_sr, vocal_hop = _prepare_chroma(
        vocal,
        vocal_sr,
    )

    instrumental_chroma, instrumental_sr, instrumental_hop = (
        _prepare_chroma(
            instrumental,
            instrumental_sr,
        )
    )

    # Dynamic Time Warping finds a path through the two musical
    # representations even when local timing differs.
    _, warping_path = librosa.sequence.dtw(
        X=vocal_chroma,
        Y=instrumental_chroma,
        metric="cosine",
    )

    # librosa returns the path backwards.
    warping_path = warping_path[::-1]

    vocal_times = librosa.frames_to_time(
        warping_path[:, 0],
        sr=vocal_sr,
        hop_length=vocal_hop,
    )

    instrumental_times = librosa.frames_to_time(
        warping_path[:, 1],
        sr=instrumental_sr,
        hop_length=instrumental_hop,
    )

    # Instead of returning thousands of DTW points,
    # sample approximately one diagnostic point every 2 seconds.
    vocal_duration = librosa.get_duration(
        y=vocal,
        sr=vocal_sr,
    )

    sample_times = np.arange(
        0.0,
        vocal_duration + 0.001,
        2.0,
    )

    alignment_points = []

    for source_time in sample_times:
        index = int(
            np.argmin(
                np.abs(vocal_times - source_time)
            )
        )

        actual_source_time = float(vocal_times[index])
        target_time = float(instrumental_times[index])

        shift = target_time - actual_source_time

        alignment_points.append(
            {
                "source_time": round(
                    actual_source_time,
                    3,
                ),
                "target_time": round(
                    target_time,
                    3,
                ),
                "shift_seconds": round(
                    shift,
                    3,
                ),
            }
        )

    shifts = np.array(
        [
            point["shift_seconds"]
            for point in alignment_points
        ],
        dtype=float,
    )

    if len(shifts) > 0:
        mean_shift = float(np.mean(shifts))
        max_abs_shift = float(np.max(np.abs(shifts)))
    else:
        mean_shift = 0.0
        max_abs_shift = 0.0

    return {
        "method": "chroma_cqt_dtw",
        "point_interval_seconds": 2.0,
        "alignment_points": alignment_points,
        "summary": {
            "mean_shift_seconds": round(
                mean_shift,
                3,
            ),
            "max_absolute_shift_seconds": round(
                max_abs_shift,
                3,
            ),
        },
    }


async def analyze_alignment(
    vocal_url: str,
    instrumental_url: str,
):
    """
    Compare original vocal and generated instrumental.

    Diagnostic only:
    no time stretching,
    no pitch correction,
    no audio modification.
    """

    vocal, vocal_sr = await _download_audio(
        vocal_url
    )

    instrumental, instrumental_sr = await _download_audio(
        instrumental_url
    )

    vocal_analysis = _basic_analysis(
        vocal,
        vocal_sr,
    )

    instrumental_analysis = _basic_analysis(
        instrumental,
        instrumental_sr,
    )

    local_alignment = _calculate_local_alignment(
        vocal=vocal,
        vocal_sr=vocal_sr,
        instrumental=instrumental,
        instrumental_sr=instrumental_sr,
    )

    duration_difference = (
        instrumental_analysis["duration_seconds"]
        - vocal_analysis["duration_seconds"]
    )

    return {
        "vocal": vocal_analysis,
        "instrumental": instrumental_analysis,

        "comparison": {
            "duration_difference_seconds": round(
                duration_difference,
                3,
            ),
        },

        "local_alignment": local_alignment,

        "note": (
            "Diagnostic analysis only. "
            "No audio has been modified."
        ),
    }
