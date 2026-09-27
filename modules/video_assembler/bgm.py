"""Background music bed with simple sidechain-style ducking under voice."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from core.logging_setup import get_logger

log = get_logger(__name__)


def mix_background_music(
    video_path: Path,
    music_path: Path,
    output_path: Path,
    *,
    ffmpeg_bin: str = "ffmpeg",
    music_volume: float = 0.12,
) -> Path:
    """
    Mix a looped music bed under the existing video audio.

    Uses FFmpeg amix with volume scaling (practical ducking without full sidechain).
    """
    if not video_path.exists():
        raise FileNotFoundError(video_path)
    if not music_path.exists():
        raise FileNotFoundError(music_path)

    ff = shutil.which(ffmpeg_bin) or shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("ffmpeg required for BGM mix")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    vol = max(0.0, min(1.0, music_volume))
    # Loop music to video length, lower volume, amix
    filter_complex = (
        f"[1:a]volume={vol:.3f},aloop=loop=-1:size=2e+09[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )
    cmd = [
        ff,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(music_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_path),
    ]
    log.info("Mixing BGM volume=%.2f -> %s", vol, output_path.name)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"BGM mix failed: {proc.stderr[-2000:]}")
    return output_path
