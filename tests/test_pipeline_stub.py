"""End-to-end pipeline with offline-friendly stubs for heavy stages."""

from __future__ import annotations

from pathlib import Path

from core.config import AppConfig, ProjectSettings
from core.pipeline import Pipeline
from core.project import Project


def _cfg(tmp_path: Path) -> AppConfig:
    cfg = AppConfig(project=ProjectSettings(root=tmp_path / "projects"))
    cfg.repo_root = tmp_path
    # Prefer silent voice + stub transcribe for unit speed
    cfg.voice.engine = "silence"
    cfg.voice.require_clone = False
    cfg.transcription.engine = "faster-whisper"
    cfg.video.crossfade_seconds = 0.0
    return cfg


def test_full_stub_pipeline(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("YT_STUDIO_STUB_VOICE", "1")
    monkeypatch.setenv("YT_STUDIO_STUB_TRANSCRIBE", "1")
    monkeypatch.setenv("YT_STUDIO_SKIP_VANTAGE", "1")
    monkeypatch.setenv("YT_STUDIO_PUBLISH_DRY_RUN", "1")

    cfg = _cfg(tmp_path)
    proj = Project.create(cfg, "Pipeline Stub Demo")

    result = Pipeline(cfg).run(proj)
    assert result.ok, result.error
    assert set(result.completed) == set(cfg.pipeline.stages)

    assert proj.paths.outline.exists()
    assert proj.paths.seo.exists()
    assert proj.paths.slides.exists()
    assert proj.paths.final_video.exists()
    assert proj.paths.final_video.stat().st_size > 500
    assert proj.paths.transcript_json.exists()
    assert proj.paths.transcript_srt.exists()
    assert proj.paths.chapters.exists()
    assert list(proj.paths.shorts_dir.glob("short_*.mp4"))
    assert (proj.paths.root / "publish_manifest.json").exists()

    for name in cfg.pipeline.stages:
        assert proj.checkpoint.is_completed(name)


def test_resume_skips_completed(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("YT_STUDIO_STUB_VOICE", "1")
    monkeypatch.setenv("YT_STUDIO_STUB_TRANSCRIBE", "1")
    monkeypatch.setenv("YT_STUDIO_SKIP_VANTAGE", "1")
    monkeypatch.setenv("YT_STUDIO_PUBLISH_DRY_RUN", "1")

    cfg = _cfg(tmp_path)
    proj = Project.create(cfg, "Resume Demo")

    first = Pipeline(cfg).run(proj, only=["scriptwriter", "slidebuilder"])
    assert first.ok
    assert first.completed == ["scriptwriter", "slidebuilder"]

    second = Pipeline(cfg).run(proj)
    assert second.ok, second.error
    assert "scriptwriter" in second.skipped
    assert "slidebuilder" in second.skipped
    assert "voice" in second.completed


def test_only_stage(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = _cfg(tmp_path)
    proj = Project.create(cfg, "Only Stage")
    Pipeline(cfg).run(proj, only=["scriptwriter"])
    assert proj.checkpoint.is_completed("scriptwriter")
    assert not proj.checkpoint.is_completed("slidebuilder")


def test_dependency_failure(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    proj = Project.create(cfg, "Dep Fail")
    result = Pipeline(cfg).run(proj, only=["slidebuilder"])
    assert not result.ok
    assert result.failed == "slidebuilder"
