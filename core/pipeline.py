"""Orchestrator: run pipeline stages with resumable checkpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.checkpoint import StageStatus
from core.config import AppConfig
from core.logging_setup import get_logger
from core.project import Project
from core.stages import Stage, StageResult, build_default_registry

log = get_logger(__name__)


@dataclass
class PipelineResult:
    project_id: str
    completed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: str | None = None
    error: str | None = None
    results: dict[str, StageResult] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.failed is None


class Pipeline:
    """
    Run ordered stages against a Project.

    Resumability: stages already COMPLETED in state.json are skipped unless
    `force=True` or the stage is explicitly requested via `only`.
    """

    def __init__(
        self,
        config: AppConfig,
        *,
        stages: dict[str, Stage] | None = None,
    ) -> None:
        self.config = config
        self.stages = stages if stages is not None else build_default_registry()

    def run(
        self,
        project: Project,
        *,
        only: list[str] | None = None,
        skip: list[str] | None = None,
        force: bool = False,
        from_stage: str | None = None,
    ) -> PipelineResult:
        planned = self._plan(
            only=only,
            skip=skip,
            from_stage=from_stage,
        )
        result = PipelineResult(project_id=project.project_id)
        log.info(
            "Pipeline start project=%s stages=%s",
            project.project_id,
            " → ".join(planned),
        )

        for name in planned:
            stage = self.stages.get(name)
            if stage is None:
                msg = f"Unknown stage '{name}'. Known: {sorted(self.stages)}"
                log.error(msg)
                result.failed = name
                result.error = msg
                project.checkpoint.mark_failed(name, msg)
                project.save()
                if self.config.pipeline.fail_fast:
                    break
                continue

            rec = project.checkpoint.get(name)
            if (
                rec.status == StageStatus.COMPLETED
                and not force
                and only is None
            ):
                log.info("[skip] %s (already completed)", name)
                result.skipped.append(name)
                continue

            # When --only is set, re-run even if completed (unless force=False
            # and we want to keep cache — convention: --only implies re-run)
            if only is not None and name in only:
                pass  # always execute selected stages
            elif rec.status == StageStatus.COMPLETED and not force:
                log.info("[skip] %s (already completed)", name)
                result.skipped.append(name)
                continue

            log.info("[run]  %s", name)
            project.checkpoint.mark_running(name)
            project.save()

            try:
                stage_result = stage.run(project)
            except Exception as exc:  # noqa: BLE001 — capture for checkpoint
                err = f"{type(exc).__name__}: {exc}"
                log.exception("Stage %s failed: %s", name, err)
                project.checkpoint.mark_failed(name, err)
                project.save()
                result.failed = name
                result.error = err
                if self.config.pipeline.fail_fast:
                    break
                continue

            project.checkpoint.mark_completed(
                name,
                artifacts=stage_result.artifacts,
                meta=stage_result.meta,
            )
            project.save()
            result.completed.append(name)
            result.results[name] = stage_result
            log.info(
                "[done] %s — %s",
                name,
                stage_result.message or f"{len(stage_result.artifacts)} artifact(s)",
            )

        log.info(
            "Pipeline finished project=%s completed=%s skipped=%s failed=%s",
            project.project_id,
            result.completed,
            result.skipped,
            result.failed,
        )
        return result

    def _plan(
        self,
        *,
        only: list[str] | None,
        skip: list[str] | None,
        from_stage: str | None,
    ) -> list[str]:
        order = list(self.config.pipeline.stages)
        known = set(self.stages.keys()) | set(order)

        if only:
            unknown = [s for s in only if s not in known]
            if unknown:
                raise ValueError(f"Unknown stage(s) in --only: {unknown}")
            # Preserve global order for multi-stage only
            return [s for s in order if s in only]

        skip_set = set(skip or [])
        if from_stage:
            if from_stage not in order:
                raise ValueError(
                    f"--from-stage '{from_stage}' not in pipeline order: {order}"
                )
            idx = order.index(from_stage)
            order = order[idx:]

        return [s for s in order if s not in skip_set]


def run_pipeline(
    config: AppConfig,
    project: Project,
    **kwargs: Any,
) -> PipelineResult:
    """Convenience wrapper."""
    return Pipeline(config).run(project, **kwargs)
