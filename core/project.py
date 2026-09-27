"""Project paths and lifecycle for a single video."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from core.checkpoint import Checkpoint
from core.config import AppConfig


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, *, max_len: int = 60) -> str:
    slug = _SLUG_RE.sub("-", text.lower().strip()).strip("-")
    if not slug:
        slug = "untitled"
    return slug[:max_len].rstrip("-")


def make_project_id(topic: str, *, when: date | None = None) -> str:
    d = (when or date.today()).isoformat()
    return f"{d}_{slugify(topic)}"


@dataclass
class ProjectPaths:
    """Canonical artifact paths under projects/<project_id>/."""

    root: Path

    @property
    def state(self) -> Path:
        return self.root / "state.json"

    @property
    def outline(self) -> Path:
        return self.root / "outline.json"

    @property
    def seo(self) -> Path:
        return self.root / "seo.json"

    @property
    def slides(self) -> Path:
        return self.root / "slides.pptx"

    @property
    def audio_dir(self) -> Path:
        return self.root / "audio"

    @property
    def frames_dir(self) -> Path:
        return self.root / "frames"

    @property
    def final_video(self) -> Path:
        return self.root / "final.mp4"

    @property
    def final_video_subtitled(self) -> Path:
        return self.root / "final_subtitled.mp4"

    @property
    def transcript_json(self) -> Path:
        return self.root / "transcript.json"

    @property
    def transcript_srt(self) -> Path:
        return self.root / "transcript.srt"

    @property
    def transcript_vtt(self) -> Path:
        return self.root / "transcript.vtt"

    @property
    def chapters(self) -> Path:
        return self.root / "chapters.txt"

    @property
    def thumbnail(self) -> Path:
        return self.root / "thumbnail.jpg"

    @property
    def shorts_dir(self) -> Path:
        return self.root / "shorts"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(exist_ok=True)
        self.frames_dir.mkdir(exist_ok=True)
        self.shorts_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

    def audio_for_slide(self, index: int) -> Path:
        return self.audio_dir / f"slide_{index:02d}.mp3"

    def frame_for_slide(self, index: int) -> Path:
        return self.frames_dir / f"slide_{index:02d}.png"


@dataclass
class Project:
    """In-memory handle for one video project."""

    project_id: str
    paths: ProjectPaths
    checkpoint: Checkpoint
    config: AppConfig
    # Extra run context (topic, source docs, keywords, etc.)
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def topic(self) -> str:
        return self.checkpoint.topic or str(self.context.get("topic", ""))

    @property
    def voice_id(self) -> str:
        return self.checkpoint.voice_id

    def save(self) -> None:
        self.checkpoint.save(self.paths.state)

    def rel(self, path: Path) -> str:
        """Path relative to project root when possible (for state artifacts)."""
        try:
            return str(path.resolve().relative_to(self.paths.root.resolve()))
        except ValueError:
            return str(path)

    @classmethod
    def create(
        cls,
        config: AppConfig,
        topic: str,
        *,
        project_id: str | None = None,
        voice_id: str | None = None,
        options: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        force: bool = False,
    ) -> Project:
        pid = project_id or make_project_id(topic)
        root = config.projects_dir() / pid
        if root.exists() and force:
            shutil.rmtree(root)
        paths = ProjectPaths(root=root)
        paths.ensure()

        voice = voice_id or config.voice.default_voice
        if paths.state.exists() and not force:
            checkpoint = Checkpoint.load(paths.state)
            # Allow updating topic/voice if still empty
            if topic and not checkpoint.topic:
                checkpoint.topic = topic
            if voice_id:
                checkpoint.voice_id = voice_id
        else:
            checkpoint = Checkpoint.new(
                pid,
                config.pipeline.stages,
                topic=topic,
                voice_id=voice,
                options=options or {},
            )
            checkpoint.save(paths.state)

        ctx = {"topic": topic, **(context or {})}
        return cls(
            project_id=pid,
            paths=paths,
            checkpoint=checkpoint,
            config=config,
            context=ctx,
        )

    @classmethod
    def load(cls, config: AppConfig, project_id: str) -> Project:
        root = config.projects_dir() / project_id
        paths = ProjectPaths(root=root)
        if not paths.state.exists():
            raise FileNotFoundError(
                f"Project '{project_id}' not found (missing {paths.state})"
            )
        checkpoint = Checkpoint.load(paths.state)
        paths.ensure()
        return cls(
            project_id=project_id,
            paths=paths,
            checkpoint=checkpoint,
            config=config,
            context={"topic": checkpoint.topic},
        )
