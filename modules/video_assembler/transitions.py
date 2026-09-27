"""Scene-level concatenation and transition logic for animated video assembly."""

from __future__ import annotations


def compute_timeline_offsets(
    clip_durations: list[float], transition_overlap: float = 0.0
) -> list[float]:
    """
    Compute start timestamp of each scene clip on the master timeline.
    """
    if not clip_durations:
        return []
    offsets = [0.0]
    for i in range(1, len(clip_durations)):
        prev_end = offsets[i - 1] + clip_durations[i - 1]
        start = max(0.0, prev_end - transition_overlap)
        offsets.append(round(start, 3))
    return offsets


def total_timeline_duration(clip_durations: list[float], transition_overlap: float = 0.0) -> float:
    """Calculate total running time of concatenated clips accounting for any overlap."""
    if not clip_durations:
        return 0.0
    if len(clip_durations) == 1 or transition_overlap <= 0:
        return sum(clip_durations)
    return sum(clip_durations) - transition_overlap * (len(clip_durations) - 1)


def build_scene_concat_filter(
    clip_count: int,
    durations: list[float],
    *,
    transition: str = "cut",  # cut | crossfade
    crossfade_duration: float = 0.25,
) -> tuple[list[str], str, str]:
    """
    Build FFmpeg filter_complex for joining N video+audio scenes.

    Returns:
    (filter_complex_args, output_video_label, output_audio_label)
    """
    if clip_count <= 0:
        raise ValueError("clip_count must be at least 1")

    if clip_count == 1 or transition == "cut" or crossfade_duration <= 0.0:
        # Standard clean concat filter graph
        inputs_v = "".join(f"[{i}:v][{i}:a]" for i in range(clip_count))
        filter_str = f"{inputs_v}concat=n={clip_count}:v=1:a=1[v_out][a_out]"
        return [filter_str], "[v_out]", "[a_out]"

    # Progressive xfade + acrossfade for soft scene joins
    filter_parts: list[str] = []
    cur_v = "[0:v]"
    cur_a = "[0:a]"
    offset = 0.0

    for i in range(1, clip_count):
        prev_dur = durations[i - 1] if i - 1 < len(durations) else 5.0
        offset += max(0.1, prev_dur - crossfade_duration)
        out_v = f"v_join_{i}"
        out_a = f"a_join_{i}"
        filter_parts.append(
            f"{cur_v}[{i}:v]xfade=transition=fade:duration={crossfade_duration:.3f}:offset={offset:.3f}[{out_v}]"
        )
        filter_parts.append(f"{cur_a}[{i}:a]acrossfade=d={crossfade_duration:.3f}[{out_a}]")
        cur_v = f"[{out_v}]"
        cur_a = f"[{out_a}]"

    return filter_parts, cur_v, cur_a
