
import io
import gc

import httpx
import librosa
import numpy as np


# Low-memory analysis settings.
# These settings affect analysis only, not the original audio.
ANALYSIS_SR = 11025
HOP_LENGTH = 2048
N_FFT = 2048
POINT_INTERVAL_SECONDS = 2.0


async def _download_audio(url: str):
    """
    Download and decode audio at a reduced sample rate.

    The original audio file is NOT modified.
    Only the in-memory analysis copy is downsampled.
    """
    async with httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=True,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        audio_data = response.content

    with io.BytesIO(audio_data) as audio_bytes:
        y, sr = librosa.load(
            audio_bytes,
            sr=ANALYSIS_SR,
            mono=True,
            dtype=np.float32,
        )

    del audio_data, response

    if len(y) == 0:
        raise ValueError("Downloaded audio is empty.")

    return y, sr


def _basic_analysis(y, sr):
    """
    Estimate duration, tempo and beat positions
    using low-memory analysis settings.
    """
    duration = len(y) / float(sr)

    tempo, beat_frames = librosa.beat.beat_track(
        y=y,
        sr=sr,
        hop_length=HOP_LENGTH,
    )

    beat_times = librosa.frames_to_time(
        beat_frames,
        sr=sr,
        hop_length=HOP_LENGTH,
    )

    tempo_value = float(
        np.asarray(tempo).reshape(-1)[0]
    )

    return {
        "duration_seconds": round(duration, 3),
        "sample_rate": int(sr),
        "tempo_bpm": round(tempo_value, 3),
        "beat_count": int(len(beat_times)),
        "beat_times": [
            round(float(t), 3)
            for t in beat_times
        ],
    }


def _prepare_chroma(y, sr):
    """
    Create a lightweight chroma representation.

    Avoids:
    - harmonic separation (HPSS)
    - chroma_cqt
    - high-resolution feature frames

    No audio is modified.
    """
    chroma = librosa.feature.chroma_stft(
        y=y,
        sr=sr,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        tuning=0.0,
    )

    chroma = np.asarray(
        chroma,
        dtype=np.float32,
    )

    # Avoid zero-length vectors in cosine distance.
    chroma += 1e-8

    return chroma, sr, HOP_LENGTH


def _calculate_local_alignment(
    vocal,
    vocal_sr,
    instrumental,
    instrumental_sr,
):
    """
    Low-memory diagnostic alignment using
    chroma STFT + Dynamic Time Warping.

    No audio is modified.
    """

    vocal_chroma, prepared_vocal_sr, vocal_hop = (
        _prepare_chroma(vocal, vocal_sr)
    )

    instrumental_chroma, prepared_instrumental_sr, instrumental_hop = (
        _prepare_chroma(instrumental, instrumental_sr)
    )

    # With the reduced frame rate, the DTW matrix
    # is much smaller than in the previous version.
    _, warping_path = librosa.sequence.dtw(
        X=vocal_chroma,
        Y=instrumental_chroma,
        metric="cosine",
    )

    del vocal_chroma, instrumental_chroma

    # librosa returns the path in reverse order.
    warping_path = warping_path[::-1]

    vocal_times = librosa.frames_to_time(
        warping_path[:, 0],
        sr=prepared_vocal_sr,
        hop_length=vocal_hop,
    )

    instrumental_times = librosa.frames_to_time(
        warping_path[:, 1],
        sr=prepared_instrumental_sr,
        hop_length=instrumental_hop,
    )

    del warping_path

    max_source_time = float(vocal_times[-1])

    sample_times = np.arange(
        0.0,
        max_source_time,
        POINT_INTERVAL_SECONDS,
    )

    sample_times = np.append(
        sample_times,
        max_source_time,
    )

    alignment_points = []
    seen_source_times = set()

    for requested_time in sample_times:
        index = int(
            np.argmin(
                np.abs(vocal_times - requested_time)
            )
        )

        source_time = round(
            float(vocal_times[index]),
            3,
        )

        if source_time in seen_source_times:
            continue

        seen_source_times.add(source_time)

        target_time = round(
            float(instrumental_times[index]),
            3,
        )

        shift = round(
            target_time - source_time,
            3,
        )

        alignment_points.append({
            "source_time": source_time,
            "target_time": target_time,
            "shift_seconds": shift,
        })

    del vocal_times, instrumental_times

    previous_shift = None

    for point in alignment_points:
        shift = point["shift_seconds"]

        suspicious = False
        reasons = []

        if abs(shift) > 1.5:
            suspicious = True
            reasons.append(
                "large_absolute_shift"
            )

        if previous_shift is not None:
            jump = abs(shift - previous_shift)

            if jump > 1.25:
                suspicious = True
                reasons.append(
                    "sudden_alignment_jump"
                )

        point["suspicious"] = suspicious
        point["reasons"] = reasons

        previous_shift = shift

    reliable_points = [
        point
        for point in alignment_points
        if not point["suspicious"]
    ]

    suspicious_points = [
        point
        for point in alignment_points
        if point["suspicious"]
    ]

    if reliable_points:
        reliable_shifts = np.array(
            [
                point["shift_seconds"]
                for point in reliable_points
            ],
            dtype=np.float32,
        )

        median_reliable_shift = float(
            np.median(reliable_shifts)
        )

        mean_reliable_shift = float(
            np.mean(reliable_shifts)
        )

        max_reliable_shift = float(
            np.max(np.abs(reliable_shifts))
        )

    else:
        median_reliable_shift = 0.0
        mean_reliable_shift = 0.0
        max_reliable_shift = 0.0

    return {
        "method": "chroma_stft_dtw_low_memory",
        "point_interval_seconds": POINT_INTERVAL_SECONDS,
        "alignment_points": alignment_points,
        "summary": {
            "total_points": len(alignment_points),
            "reliable_points": len(reliable_points),
            "suspicious_points": len(suspicious_points),
            "median_reliable_shift_seconds": round(
                median_reliable_shift, 3
            ),
            "mean_reliable_shift_seconds": round(
                mean_reliable_shift, 3
            ),
            "max_reliable_absolute_shift_seconds": round(
                max_reliable_shift, 3
            ),
        },
        "warning": (
            "Low-memory STFT/DTW alignment is approximate "
            "and diagnostic only. "
            "Suspicious points must not be used directly "
            "for vocal time-stretching. "
            "Do not apply alignment automatically without validation."
        ),
    }


async def analyze_alignment(
    vocal_url: str,
    instrumental_url: str,
):
    """
    Compare the original vocal and instrumental.

    Diagnostic only:
    - No time stretching
    - No pitch correction
    - No change to original vocal
    """

    vocal, vocal_sr = await _download_audio(
        vocal_url
    )

    vocal_analysis = _basic_analysis(
        vocal,
        vocal_sr,
    )

    instrumental, instrumental_sr = (
        await _download_audio(
            instrumental_url
        )
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

    del vocal, instrumental
    gc.collect()

    return {
        "vocal": vocal_analysis,
        "instrumental": instrumental_analysis,
        "comparison": {
            "duration_difference_seconds": round(
                duration_difference, 3
            ),
        },
        "local_alignment": local_alignment,
        "note": (
            "Diagnostic analysis only. "
            "Audio was downsampled for analysis. "
            "Original audio files were not modified."
        ),
    }
