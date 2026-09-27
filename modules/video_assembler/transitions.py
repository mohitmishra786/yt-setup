"""Optional transitions (crossfade / pan) helpers for FFmpeg filter graphs."""

from __future__ import annotations


def crossfade_offset(clip_durations: list[float], crossfade: float) -> list[float]:
    """
    Compute concat offsets when each pair of clips overlaps by `crossfade` seconds.

    Returns start time of each clip on the timeline.
    """
    if not clip_durations:
        return []
    offsets = [0.0]
    for i in range(1, len(clip_durations)):
        prev_end = offsets[i - 1] + clip_durations[i - 1]
        start = max(0.0, prev_end - crossfade)
        offsets.append(start)
    return offsets


def total_duration_with_crossfade(clip_durations: list[float], crossfade: float) -> float:
    if not clip_durations:
        return 0.0
    if len(clip_durations) == 1:
        return clip_durations[0]
    # Sum durations minus one crossfade per join
    return sum(clip_durations) - crossfade * (len(clip_durations) - 1)
