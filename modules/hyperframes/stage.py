"""HyperFrames stage: validate + render projects/<id>/composition/ into final.mp4.

The composition itself is authored by the coding agent (see skills/create-video and
skills/create-short). This stage only owns the deterministic tail: the `hyperframes check`
gate, the render, and baking the chosen poster frame as frame 0.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from core.logging_setup import get_logger
from core.project import Project
from core.stages import StageResult

log = get_logger(__name__)

QUALITIES = ("draft", "standard", "high")


def _npx() -> str:
    found = shutil.which("npx")
    if not found:
        raise RuntimeError(
            "npx not found on PATH. HyperFrames needs Node.js 22+ "
            "(https://nodejs.org) — then verify with `npx hyperframes doctor`."
        )
    return found


def _run(cmd: list[str], cwd: Path, what: str) -> None:
    log.info("%s: %s", what, " ".join(cmd))
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr)[-2000:]
        raise RuntimeError(f"{what} failed (exit {proc.returncode}):\n{tail}")


def read_poster_time(root: Path) -> float | None:
    """Optional poster frame time from projects/<id>/poster.json ({"time": 3.2})."""
    poster_file = root / "poster.json"
    if not poster_file.exists():
        return None
    data = json.loads(poster_file.read_text(encoding="utf-8"))
    t = data.get("time")
    return float(t) if t is not None else None


def bake_poster(final: Path, poster_jpg: Path, at: float, ffmpeg: str = "ffmpeg") -> None:
    """Extract the settled frame at `at` seconds and overlay it onto frame 0 only."""
    final, poster_jpg = final.resolve(), poster_jpg.resolve()
    ff = shutil.which(ffmpeg) or shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("ffmpeg not found on PATH")
    grab = [ff, "-y", "-ss", f"{at:.3f}", "-i", str(final), "-frames:v", "1", "-q:v", "2",
            str(poster_jpg)]
    _run(grab, final.parent, "poster extract")
    tmp = final.with_suffix(".poster.mp4")
    bake = [
        ff, "-y", "-i", str(final), "-i", str(poster_jpg),
        "-filter_complex", "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]",
        "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18", "-preset", "slow",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(tmp),
    ]
    _run(bake, final.parent, "poster bake")
    tmp.replace(final)


class HyperframesStage:
    """Check and render the agent-authored HyperFrames composition."""

    name = "hyperframes"

    def run(self, project: Project) -> StageResult:
        root = project.paths.root
        comp = root / "composition"
        if not (comp / "index.html").exists():
            raise FileNotFoundError(
                f"Missing {comp / 'index.html'} — author the HyperFrames composition first "
                "(skills/create-video/references/compose.md)."
            )

        quality = os.getenv("YT_STUDIO_HF_QUALITY", "high")
        if quality not in QUALITIES:
            raise ValueError(f"YT_STUDIO_HF_QUALITY must be one of {QUALITIES}, got {quality!r}")

        npx = _npx()
        final = project.paths.final_video
        _run([npx, "hyperframes", "check"], comp, "hyperframes check")
        _run(
            [npx, "hyperframes", "render", "--quality", quality, "--output", str(final)],
            comp,
            "hyperframes render",
        )
        if not final.exists():
            raise RuntimeError(f"hyperframes render reported success but {final} is missing")

        artifacts = [project.rel(final)]
        meta: dict[str, object] = {"quality": quality, "engine": "hyperframes"}
        poster_at = read_poster_time(root)
        if poster_at is not None:
            poster = root / "poster.jpg"
            bake_poster(final, poster, poster_at, project.config.video.ffmpeg_bin)
            artifacts.append(project.rel(poster))
            meta["poster_time"] = poster_at

        return StageResult(
            stage=self.name,
            artifacts=artifacts,
            meta=meta,
            message=f"final.mp4 rendered by HyperFrames ({quality})",
        )
