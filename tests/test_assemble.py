"""Tests for modules/video_assembler: scene concat, muxing, and transitions."""

from __future__ import annotations

import subprocess
from pathlib import Path

from modules.scenegen.renderer import render_scene_stub
from modules.video_assembler.assemble import _concat_clips, _ffmpeg, _mux_scene_and_audio
from modules.video_assembler.transitions import (
    build_scene_concat_filter,
    compute_timeline_offsets,
    total_timeline_duration,
)


def test_timeline_duration_and_offsets() -> None:
    durations = [10.0, 15.0, 20.0]
    offsets = compute_timeline_offsets(durations, transition_overlap=0.0)
    assert offsets == [0.0, 10.0, 25.0]
    assert total_timeline_duration(durations, 0.0) == 45.0

    # With 1.0s overlap
    overlap_offsets = compute_timeline_offsets(durations, transition_overlap=1.0)
    assert overlap_offsets == [0.0, 9.0, 23.0]
    assert total_timeline_duration(durations, 1.0) == 43.0


def test_build_scene_concat_filter() -> None:
    # Direct cut
    filter_args, v_label, a_label = build_scene_concat_filter(3, [5.0, 5.0, 5.0], transition="cut")
    assert len(filter_args) == 1
    assert "concat=n=3:v=1:a=1" in filter_args[0]
    assert v_label == "[v_out]"
    assert a_label == "[a_out]"

    # Soft crossfade
    xfade_args, xv, xa = build_scene_concat_filter(
        3, [5.0, 5.0, 5.0], transition="crossfade", crossfade_duration=0.5
    )
    assert any("xfade=" in part for part in xfade_args)
    assert any("acrossfade=" in part for part in xfade_args)


def _generate_synthetic_tone(output_wav: Path, duration: float = 2.0) -> Path:
    """Generate a clean synthetic WAV audio track via FFmpeg."""
    ff = _ffmpeg()
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ff,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={duration:.3f}",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "24000",
        str(output_wav),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_wav


def test_mux_scene_pads_video_to_audio_duration(tmp_path: Path) -> None:
    ff = _ffmpeg()

    # Short video (1.5s)
    short_video = tmp_path / "short_scene.mp4"
    render_scene_stub(short_video, duration=1.5)

    # Longer audio narration (3.5s)
    long_audio = tmp_path / "long_audio.wav"
    _generate_synthetic_tone(long_audio, duration=3.5)

    out_clip = tmp_path / "muxed_clip.mp4"
    dur = _mux_scene_and_audio(
        ff,
        short_video,
        long_audio,
        out_clip,
        fps=30,
        video_codec="libx264",
        audio_codec="aac",
        crf=20,
        preset="ultrafast",
    )
    assert dur >= 3.4
    assert out_clip.exists()
    assert out_clip.stat().st_size > 500


def test_concat_scene_clips(tmp_path: Path) -> None:
    ff = _ffmpeg()

    clip1 = tmp_path / "c1.mp4"
    clip2 = tmp_path / "c2.mp4"
    a1 = tmp_path / "a1.wav"
    a2 = tmp_path / "a2.wav"
    v1 = tmp_path / "v1.mp4"
    v2 = tmp_path / "v2.mp4"

    render_scene_stub(v1, duration=1.5)
    render_scene_stub(v2, duration=1.5)
    _generate_synthetic_tone(a1, duration=1.5)
    _generate_synthetic_tone(a2, duration=1.5)

    _mux_scene_and_audio(
        ff,
        v1,
        a1,
        clip1,
        fps=30,
        video_codec="libx264",
        audio_codec="aac",
        crf=20,
        preset="ultrafast",
    )
    _mux_scene_and_audio(
        ff,
        v2,
        a2,
        clip2,
        fps=30,
        video_codec="libx264",
        audio_codec="aac",
        crf=20,
        preset="ultrafast",
    )

    final_mp4 = tmp_path / "final.mp4"
    _concat_clips(
        ff,
        [clip1, clip2],
        final_mp4,
        [1.5, 1.5],
        crossfade=0.0,
        fps=30,
        video_codec="libx264",
        audio_codec="aac",
        crf=20,
        preset="ultrafast",
    )
    assert final_mp4.exists()
    assert final_mp4.stat().st_size > 1000
