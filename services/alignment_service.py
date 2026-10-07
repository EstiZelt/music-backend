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


def _prepare_chroma(
    y,
    sr,
    target_sr=22050,
):
    """
    Create a musical representation for alignment.

    Chroma focuses mainly on pitch-class movement rather than
    timbre, which makes it more suitable for comparing a vocal
    recording with an instrumental arrangement.
    """

    if sr != target_sr:
        y = librosa.resample(
            y,
            orig_sr=sr,
            target_sr=target_sr,
        )

        sr = target_sr

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
    Diagnostic local musical alignment using chroma + DTW.

    No audio is modified here.
    """

    (
        vocal_chroma,
        prepared_vocal_sr,
        vocal_hop,
    ) = _prepare_chroma(
        vocal,
        vocal_sr,
    )

    (
        instrumental_chroma,
        prepared_instrumental_sr,
        instrumental_hop,
    ) = _prepare_chroma(
        instrumental,
        instrumental_sr,
    )

    _, warping_path = librosa.sequence.dtw(
        X=vocal_chroma,
        Y=instrumental_chroma,
        metric="cosine",
    )

    # DTW path is returned backwards.
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

    # IMPORTANT:
    # Use the real last time represented by the DTW path.
    # This avoids the duplicated end points we saw previously.
    max_source_time = float(vocal_times[-1])

    sample_times = np.arange(
        0.0,
        max_source_time,
        2.0,
    )

    # Always include the final valid point once.
    sample_times = np.append(
        sample_times,
        max_source_time,
    )

    alignment_points = []

    for requested_time in sample_times:
        index = int(
            np.argmin(
                np.abs(
                    vocal_times - requested_time
                )
            )
        )

        source_time = float(
            vocal_times[index]
        )

        target_time = float(
            instrumental_times[index]
        )

        shift = (
            target_time - source_time
        )

        alignment_points.append(
            {
                "source_time": round(
                    source_time,
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

    # Remove duplicate source points.
    unique_points = []

    seen_source_times = set()

    for point in alignment_points:
        source_time = point["source_time"]

        if source_time in seen_source_times:
            continue

        seen_source_times.add(source_time)
        unique_points.append(point)

    alignment_points = unique_points

    # ---------------------------------------------------------
    # Reliability / suspicious jump analysis
    # ---------------------------------------------------------

    previous_shift = None

    for point in alignment_points:
        shift = point["shift_seconds"]

        suspicious = False
        reasons = []

        # A very large absolute displacement may indicate that
        # DTW matched the vocal to a similar musical phrase
        # somewhere else.
        if abs(shift) > 1.5:
            suspicious = True
            reasons.append(
                "large_absolute_shift"
            )

        # A sudden change relative to the previous point is also
        # suspicious.
        if previous_shift is not None:
            jump = abs(
                shift - previous_shift
            )

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
            dtype=float,
        )

        median_reliable_shift = float(
            np.median(reliable_shifts)
        )

        mean_reliable_shift = float(
            np.mean(reliable_shifts)
        )

        max_reliable_shift = float(
            np.max(
                np.abs(
                    reliable_shifts
                )
            )
        )

    else:
        median_reliable_shift = 0.0
        mean_reliable_shift = 0.0
        max_reliable_shift = 0.0

    return {
        "method": "chroma_cqt_dtw",

        "point_interval_seconds": 2.0,

        "alignment_points": alignment_points,

        "summary": {
            "total_points": len(
                alignment_points
            ),

            "reliable_points": len(
                reliable_points
            ),

            "suspicious_points": len(
                suspicious_points
            ),

            "median_reliable_shift_seconds": round(
                median_reliable_shift,
                3,
            ),

            "mean_reliable_shift_seconds": round(
                mean_reliable_shift,
                3,
            ),

            "max_reliable_absolute_shift_seconds": round(
                max_reliable_shift,
                3,
            ),
        },

        "warning": (
            "DTW alignment is diagnostic only. "
            "Suspicious points must not be used directly "
            "for vocal time-stretching."
        ),
    }


async def analyze_alignment(
    vocal_url: str,
    instrumental_url: str,
):
    """
    Compare the original vocal with the generated instrumental.

    Diagnostic only.

    No time stretching.
    No pitch correction.
    No modification of the original vocal.
    """

    vocal, vocal_sr = await _download_audio(
        vocal_url
    )

    instrumental, instrumental_sr = (
        await _download_audio(
            instrumental_url
        )
    )

    vocal_analysis = _basic_analysis(
        vocal,
        vocal_sr,
    )

    instrumental_analysis = _basic_analysis(
        instrumental,
        instrumental_sr,
    )

    local_alignment = (
        _calculate_local_alignment(
            vocal=vocal,
            vocal_sr=vocal_sr,
            instrumental=instrumental,
            instrumental_sr=instrumental_sr,
        )
    )

    duration_difference = (
        instrumental_analysis[
            "duration_seconds"
        ]
        - vocal_analysis[
            "duration_seconds"
        ]
    )

    return {
        "vocal": vocal_analysis,

        "instrumental": (
            instrumental_analysis
        ),

        "comparison": {
            "duration_difference_seconds": round(
                duration_difference,
                3,
            ),
        },

        "local_alignment": (
            local_alignment
        ),

        "note": (
            "Diagnostic analysis only. "
            "No audio has been modified."
        ),
    }
