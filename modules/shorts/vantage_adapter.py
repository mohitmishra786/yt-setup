"""Stage 7 — Vantage adapter for keyword-targeted short clips."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx

from core.logging_setup import get_logger
from core.project import Project
from core.stages import StageResult
from core.stub_utils import write_json

log = get_logger(__name__)


class VantageClient:
    """HTTP client for a self-hosted Vantage instance."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 600.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("VANTAGE_API_KEY")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def health(self) -> bool:
        for path in ("/health", "/api/health", "/"):
            try:
                with httpx.Client(timeout=5.0) as client:
                    r = client.get(f"{self.base_url}{path}", headers=self._headers())
                    if r.status_code < 500:
                        return True
            except httpx.HTTPError:
                continue
        return False

    def create_clips(
        self,
        *,
        video_path: str,
        transcript: dict[str, Any],
        keywords: list[str],
        project_id: str,
    ) -> dict[str, Any]:
        payload = {
            "video_path": video_path,
            "video_url": video_path,
            "transcript": transcript,
            "keywords": keywords,
            "project_id": project_id,
        }
        endpoints = [
            "/api/v1/clips",
            "/api/clips",
            "/clips",
            "/v1/clips",
        ]
        last_err: Exception | None = None
        with httpx.Client(timeout=self.timeout) as client:
            for ep in endpoints:
                try:
                    r = client.post(
                        f"{self.base_url}{ep}",
                        json=payload,
                        headers=self._headers(),
                    )
                    if r.status_code == 404:
                        continue
                    r.raise_for_status()
                    return r.json()
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    continue
        raise RuntimeError(f"Vantage create_clips failed: {last_err}")


def _ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if not found:
        raise RuntimeError("ffmpeg required for local shorts extraction")
    return found


def local_keyword_clips(
    project: Project,
    keywords: list[str],
    *,
    max_clips: int = 3,
    clip_seconds: float = 30.0,
) -> list[dict[str, Any]]:
    """
    Offline fallback: extract clips around transcript segments matching keywords.

    Used when Vantage is unreachable so the pipeline still produces Shorts-like
    vertical candidates for review.
    """
    with project.paths.transcript_json.open(encoding="utf-8") as fh:
        transcript = json.load(fh)
    segments = list(transcript.get("segments") or [])
    kws = [k.lower() for k in keywords if k]
    hits: list[tuple[float, float, str]] = []

    for seg in segments:
        text = str(seg.get("text") or "").lower()
        if not kws or any(k in text for k in kws):
            start = max(0.0, float(seg.get("start") or 0.0) - 2.0)
            end = float(seg.get("end") or start) + 2.0
            # extend to clip_seconds window centered-ish
            if end - start < clip_seconds:
                end = start + clip_seconds
            hits.append((start, end, str(seg.get("text") or "")[:80]))
        if len(hits) >= max_clips:
            break

    if not hits and segments:
        # first N evenly spaced windows
        duration = float(segments[-1].get("end") or clip_seconds)
        step = max(clip_seconds, duration / max_clips)
        t = 0.0
        for _ in range(max_clips):
            hits.append((t, t + clip_seconds, "highlight"))
            t += step
            if t >= duration:
                break

    ff = _ffmpeg()
    w = project.config.project.shorts_width
    h = project.config.project.shorts_height
    clips_meta: list[dict[str, Any]] = []
    project.paths.shorts_dir.mkdir(parents=True, exist_ok=True)

    for i, (start, end, label) in enumerate(hits[:max_clips], start=1):
        out = project.paths.shorts_dir / f"short_{i:02d}.mp4"
        # Center-crop to 9:16
        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1"
        )
        duration = max(3.0, end - start)
        cmd = [
            ff,
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(project.paths.final_video),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vf,
            "-c:v",
            project.config.video.video_codec,
            "-crf",
            str(project.config.video.crf),
            "-preset",
            project.config.video.preset,
            "-c:a",
            project.config.video.audio_codec,
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            log.warning("short clip %d failed: %s", i, proc.stderr[-500:])
            continue
        clips_meta.append(
            {
                "id": f"short_{i:02d}",
                "path": f"shorts/{out.name}",
                "start": start,
                "end": start + duration,
                "keyword": keywords[0] if keywords else "highlight",
                "label": label,
                "source": "local_fallback",
            }
        )
    return clips_meta


def _download_or_copy_clip(url_or_path: str, dest: Path) -> bool:
    p = Path(url_or_path)
    if p.exists():
        shutil.copy2(p, dest)
        return True
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        try:
            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                r = client.get(url_or_path)
                r.raise_for_status()
                dest.write_bytes(r.content)
                return True
        except Exception as exc:  # noqa: BLE001
            log.warning("download clip failed: %s", exc)
    return False


class ShortsStage:
    """Call Vantage for keyword-targeted Shorts; local FFmpeg fallback if offline."""

    name = "shorts"

    def run(self, project: Project) -> StageResult:
        if not project.paths.final_video.exists():
            raise FileNotFoundError(
                f"Missing final.mp4 — run video_assembler first: {project.paths.final_video}"
            )
        if not project.paths.transcript_json.exists():
            raise FileNotFoundError(
                f"Missing transcript.json — run transcriber first: "
                f"{project.paths.transcript_json}"
            )

        keywords = list(project.checkpoint.options.get("keywords") or [])
        if not keywords:
            keywords = list(project.config.shorts.default_keywords)
        if not keywords:
            keywords = [project.topic] if project.topic else ["highlights"]

        with project.paths.transcript_json.open(encoding="utf-8") as fh:
            transcript = json.load(fh)

        project.paths.shorts_dir.mkdir(parents=True, exist_ok=True)
        # Clear previous shorts
        for old in project.paths.shorts_dir.glob("short_*.mp4"):
            old.unlink()

        clips: list[dict[str, Any]] = []
        source = "local_fallback"
        client = VantageClient(
            project.config.shorts.vantage_api_url,
            timeout=float(project.config.shorts.timeout_seconds),
        )

        if os.getenv("YT_STUDIO_SKIP_VANTAGE") == "1":
            log.info("Vantage skipped via env; local shorts extraction")
        elif client.health():
            try:
                resp = client.create_clips(
                    video_path=str(project.paths.final_video.resolve()),
                    transcript=transcript,
                    keywords=keywords,
                    project_id=project.project_id,
                )
                raw_clips = resp.get("clips") or resp.get("data") or []
                for i, item in enumerate(raw_clips, start=1):
                    dest = project.paths.shorts_dir / f"short_{i:02d}.mp4"
                    url = (
                        item.get("url")
                        or item.get("path")
                        or item.get("file")
                        or item.get("output")
                    )
                    if url and _download_or_copy_clip(str(url), dest):
                        clips.append(
                            {
                                "id": f"short_{i:02d}",
                                "path": f"shorts/{dest.name}",
                                "start": item.get("start"),
                                "end": item.get("end"),
                                "keyword": item.get("keyword") or keywords[0],
                                "source": "vantage",
                            }
                        )
                if clips:
                    source = "vantage"
            except Exception as exc:  # noqa: BLE001
                log.warning("Vantage call failed (%s); local fallback", exc)
        else:
            log.info(
                "Vantage not reachable at %s; local fallback",
                project.config.shorts.vantage_api_url,
            )

        if not clips:
            clips = local_keyword_clips(project, keywords)
            source = "local_fallback"

        if not clips:
            raise RuntimeError("No short clips produced (Vantage and local fallback empty)")

        manifest = {
            "vantage_api_url": project.config.shorts.vantage_api_url,
            "keywords": keywords,
            "source": source,
            "clips": clips,
        }
        manifest_path = project.paths.shorts_dir / "manifest.json"
        write_json(manifest_path, manifest)

        artifacts = [project.rel(manifest_path)]
        artifacts.extend(c["path"] for c in clips)

        log.info("Shorts source=%s count=%d keywords=%s", source, len(clips), keywords)
        return StageResult(
            stage=self.name,
            artifacts=artifacts,
            meta={
                "clip_count": len(clips),
                "keywords": keywords,
                "source": source,
                "stub": False,
            },
            message=f"{len(clips)} short(s) via {source}",
        )
