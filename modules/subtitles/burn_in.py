"""Burn SRT subtitles into a video via FFmpeg subtitles filter."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from core.logging_setup import get_logger

log = get_logger(__name__)


def find_ffmpeg(configured: str = "ffmpeg") -> str:
    found = shutil.which(configured) or shutil.which("ffmpeg")
    if not found:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install FFmpeg: https://ffmpeg.org/download.html"
        )
    return found


def _escape_subtitles_path(path: Path) -> str:
    """Escape path for FFmpeg subtitles filter (cross-platform)."""
    s = str(path.resolve())
    # FFmpeg on Windows needs drive colon escaped; always normalize slashes
    s = s.replace("\\", "/")
    s = s.replace(":", r"\:")
    s = s.replace("'", r"\'")
    return s


def burn_subtitles(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    *,
    ffmpeg_bin: str = "ffmpeg",
    font: str = "Arial",
    font_size: int = 42,
    margin_v: int = 60,
    primary_color: str = "&H00FFFFFF",
    outline_color: str = "&H00000000",
    outline: int = 2,
    force_style: str | None = None,
) -> Path:
    """
    Burn SRT into video:

      ffmpeg -i video -vf subtitles=file.srt:force_style=... out.mp4
    """
    if not video_path.exists():
        raise FileNotFoundError(video_path)
    if not srt_path.exists():
        raise FileNotFoundError(srt_path)

    binary = find_ffmpeg(ffmpeg_bin)
    style = force_style or (
        f"FontName={font},FontSize={font_size},MarginV={margin_v},"
        f"PrimaryColour={primary_color},OutlineColour={outline_color},"
        f"BorderStyle=1,Outline={outline},Shadow=0,Alignment=2"
    )
    srt_escaped = _escape_subtitles_path(srt_path)
    vf = f"subtitles={srt_escaped}:force_style='{style}'"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        binary,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-c:a",
        "copy",
        str(output_path),
    ]
    log.info("Burning subtitles -> %s", output_path.name)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        # Fallback: ass-less simple subtitles without force_style
        log.warning("styled burn failed; retry plain subtitles filter")
        vf2 = f"subtitles={srt_escaped}"
        cmd[cmd.index(vf)] = vf2
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg subtitle burn failed: {proc.stderr[-2000:]}")
    return output_path


def burn_for_project_horizontal(project_paths: Any, config: Any) -> Path:  # type: ignore[name-defined]
    from core.project import ProjectPaths

    assert isinstance(project_paths, ProjectPaths)
    return burn_subtitles(
        project_paths.final_video,
        project_paths.transcript_srt,
        project_paths.final_video_subtitled,
        ffmpeg_bin=config.video.ffmpeg_bin,
        font=config.subtitles.font,
        font_size=config.subtitles.font_size,
        margin_v=config.subtitles.margin_v,
        primary_color=config.subtitles.primary_color,
        outline_color=config.subtitles.outline_color,
        outline=config.subtitles.outline,
    )


def burn_vertical_short(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    *,
    config: Any,
) -> Path:
    """Larger font / higher margin for vertical Shorts."""
    return burn_subtitles(
        video_path,
        srt_path,
        output_path,
        ffmpeg_bin=config.video.ffmpeg_bin,
        font=config.subtitles.font,
        font_size=config.subtitles.font_size_shorts,
        margin_v=max(config.subtitles.margin_v, 120),
        primary_color=config.subtitles.primary_color,
        outline_color=config.subtitles.outline_color,
        outline=config.subtitles.outline + 1,
    )
