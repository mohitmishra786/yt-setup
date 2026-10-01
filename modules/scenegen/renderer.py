"""Playwright headless browser scene renderer to MP4 video."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from core.logging_setup import get_logger

log = get_logger(__name__)


def _ffmpeg_bin(configured: str = "ffmpeg") -> str:
    found = shutil.which(configured) or shutil.which("ffmpeg")
    if not found:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install FFmpeg: https://ffmpeg.org/download.html"
        )
    return found


def render_scene_stub(
    output_mp4: Path,
    duration: float,
    *,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
    ffmpeg_bin: str = "ffmpeg",
) -> Path:
    """Generate a clean synthetic MP4 using FFmpeg color filter in milliseconds."""
    ff = _ffmpeg_bin(ffmpeg_bin)
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    dur = max(1.0, duration)

    cmd = [
        ff,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x0f141c:s={width}x{height}:d={dur:.3f}:r={fps}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "ultrafast",
        "-t",
        f"{dur:.3f}",
        str(output_mp4),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg stub render failed: {proc.stderr[-500:]}")
    return output_mp4


def capture_scene_still(
    html_path: Path,
    output_png: Path,
    seek_time: float,
    *,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """Capture a single frame at seek_time seconds for visual QA."""
    output_png.parent.mkdir(parents=True, exist_ok=True)

    if os.getenv("YT_STUDIO_STUB_SCENES") == "1":
        # Create solid stub image
        from PIL import Image

        img = Image.new("RGB", (width, height), (15, 20, 28))
        img.save(output_png, format="PNG")
        return output_png

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(f"file://{html_path.resolve()}")
        page.wait_for_load_state("networkidle")
        page.evaluate(f"window.seekTo({seek_time:.2f})")
        page.screenshot(path=str(output_png))
        browser.close()

    return output_png


def render_scene_with_playwright(
    html_path: Path,
    output_mp4: Path,
    duration: float,
    *,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
    ffmpeg_bin: str = "ffmpeg",
) -> Path:
    """
    Render HTML scene to MP4 using Playwright native recording + FFmpeg transcode.
    """
    ff = _ffmpeg_bin(ffmpeg_bin)
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    dur = max(1.0, duration)

    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory(prefix="yt_render_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            context = browser.new_context(
                record_video_dir=str(tmp_path),
                record_video_size={"width": width, "height": height},
                viewport={"width": width, "height": height},
            )
            page = context.new_page()
            page.goto(f"file://{html_path.resolve()}")
            page.wait_for_load_state("networkidle")

            # Trigger real-time playback
            page.evaluate("window.startAnimation()")
            # Wait for the animation to play out
            page.wait_for_timeout(int((dur + 0.3) * 1000))

            # Capture still frame near end of scene for QA
            still_png = output_mp4.with_suffix(".png")
            page.screenshot(path=str(still_png))

            context.close()
            browser.close()

        # Find recorded video file in temp dir
        recorded_files = list(tmp_path.glob("*.webm"))
        if not recorded_files:
            raise RuntimeError(f"Playwright recording failed: no video found in {tmp_dir}")
        raw_video = recorded_files[0]

        # Transcode to clean high-quality MP4
        cmd = [
            ff,
            "-y",
            "-i",
            str(raw_video),
            "-t",
            f"{dur:.3f}",
            "-vf",
            f"fps={fps},format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            str(output_mp4),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(
                f"FFmpeg transcode failed for {html_path.name}: {proc.stderr[-1000:]}"
            )

    return output_mp4


def render_scene(
    html_path: Path,
    output_mp4: Path,
    duration: float,
    *,
    force: bool = False,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
    ffmpeg_bin: str = "ffmpeg",
) -> Path:
    """
    Render a single scene HTML file to MP4, respecting cached outputs.
    """
    if output_mp4.exists() and not force and output_mp4.stat().st_size > 1000:
        log.info("Cached scene %s already exists; skipping render", output_mp4.name)
        return output_mp4

    is_stub = os.getenv("YT_STUDIO_STUB_SCENES") == "1" or os.getenv("YT_STUDIO_FORCE_STUB") == "1"

    if is_stub:
        log.info("Rendering scene (stub) %s duration=%.2fs", output_mp4.name, duration)
        return render_scene_stub(
            output_mp4,
            duration,
            fps=fps,
            width=width,
            height=height,
            ffmpeg_bin=ffmpeg_bin,
        )

    log.info("Rendering scene (Playwright) %s duration=%.2fs", output_mp4.name, duration)
    try:
        return render_scene_with_playwright(
            html_path,
            output_mp4,
            duration,
            fps=fps,
            width=width,
            height=height,
            ffmpeg_bin=ffmpeg_bin,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Playwright render failed (%s); falling back to stub render", exc)
        return render_scene_stub(
            output_mp4,
            duration,
            fps=fps,
            width=width,
            height=height,
            ffmpeg_bin=ffmpeg_bin,
        )
