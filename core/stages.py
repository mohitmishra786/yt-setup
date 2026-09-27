"""Stage protocol and registry for the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from core.project import Project


@dataclass
class StageResult:
    """Outcome of a single pipeline stage."""

    stage: str
    artifacts: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    message: str = ""


@runtime_checkable
class Stage(Protocol):
    """Contract every pipeline module must satisfy."""

    name: str

    def run(self, project: Project) -> StageResult:
        """
        Execute the stage against `project`.

        Must be idempotent where practical: re-running a completed stage
        with --force should overwrite previous artifacts cleanly.
        """
        ...


# Populated by modules via register_stage / build_default_registry
STAGE_REGISTRY: dict[str, type] = {}


def register_stage(cls: type) -> type:
    """Class decorator to register a stage implementation."""
    name = getattr(cls, "name", None)
    if not name or not isinstance(name, str):
        raise TypeError(f"{cls!r} must define a string class attribute `name`")
    STAGE_REGISTRY[name] = cls
    return cls


def build_default_registry() -> dict[str, Stage]:
    """
    Import all module stages and return name -> instance map.

    Imports are local to avoid circular deps and to keep optional heavy
    dependencies unloadable until the stage is actually used.
    """
    # Import side-effects register stubs (and later real implementations)
    from modules.chapters.generate_chapters import ChaptersStage
    from modules.publisher.youtube_upload import PublisherStage
    from modules.scenegen.stage import ScenegenStage
    from modules.scriptwriter.generate_outline import ScriptwriterStage
    from modules.shorts.vantage_adapter import ShortsStage
    from modules.storyboard.generator import StoryboardStage
    from modules.transcriber.transcribe import TranscriberStage
    from modules.video_assembler.assemble import VideoAssemblerStage
    from modules.voice.engine import VoiceStage

    stages: list[Stage] = [
        ScriptwriterStage(),
        StoryboardStage(),
        ScenegenStage(),
        VoiceStage(),
        VideoAssemblerStage(),
        TranscriberStage(),
        ChaptersStage(),
        ShortsStage(),
        PublisherStage(),
    ]
    return {s.name: s for s in stages}
