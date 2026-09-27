"""Per-project resumable stage state (state.json)."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageRecord(BaseModel):
    status: StageStatus = StageStatus.PENDING
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class Checkpoint(BaseModel):
    """Serializable project pipeline state."""

    project_id: str
    created_at: str
    updated_at: str
    topic: str = ""
    voice_id: str = "default"
    stages: dict[str, StageRecord] = Field(default_factory=dict)
    # Free-form user inputs / options for stages
    options: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def new(
        cls,
        project_id: str,
        stage_names: list[str],
        *,
        topic: str = "",
        voice_id: str = "default",
        options: dict[str, Any] | None = None,
    ) -> Checkpoint:
        now = _now_iso()
        return cls(
            project_id=project_id,
            created_at=now,
            updated_at=now,
            topic=topic,
            voice_id=voice_id,
            stages={name: StageRecord() for name in stage_names},
            options=options or {},
        )

    @classmethod
    def load(cls, path: Path) -> Checkpoint:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.model_validate(data)

    def save(self, path: Path) -> None:
        """Atomic write so a crash mid-write never corrupts state.json."""
        self.updated_at = _now_iso()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.model_dump(mode="json")
        fd, tmp_name = tempfile.mkstemp(
            dir=path.parent, prefix=".state.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with open(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            tmp_path.replace(path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    def get(self, stage: str) -> StageRecord:
        if stage not in self.stages:
            self.stages[stage] = StageRecord()
        return self.stages[stage]

    def mark_running(self, stage: str) -> None:
        rec = self.get(stage)
        rec.status = StageStatus.RUNNING
        rec.started_at = _now_iso()
        rec.finished_at = None
        rec.error = None

    def mark_completed(
        self,
        stage: str,
        *,
        artifacts: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        rec = self.get(stage)
        rec.status = StageStatus.COMPLETED
        rec.finished_at = _now_iso()
        rec.error = None
        if artifacts is not None:
            rec.artifacts = artifacts
        if meta is not None:
            rec.meta = meta

    def mark_failed(self, stage: str, error: str) -> None:
        rec = self.get(stage)
        rec.status = StageStatus.FAILED
        rec.finished_at = _now_iso()
        rec.error = error

    def mark_skipped(self, stage: str, reason: str = "skipped by user") -> None:
        rec = self.get(stage)
        rec.status = StageStatus.SKIPPED
        rec.finished_at = _now_iso()
        rec.error = reason

    def is_completed(self, stage: str) -> bool:
        return self.get(stage).status == StageStatus.COMPLETED

    def summary(self) -> dict[str, str]:
        return {name: rec.status.value for name, rec in self.stages.items()}


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
