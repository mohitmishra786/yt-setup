"""yt-studio core: project model, checkpointing, and pipeline orchestration."""

from core.checkpoint import Checkpoint, StageStatus
from core.pipeline import Pipeline, PipelineResult
from core.project import Project

__all__ = [
    "Checkpoint",
    "StageStatus",
    "Pipeline",
    "PipelineResult",
    "Project",
]

__version__ = "0.1.0"
