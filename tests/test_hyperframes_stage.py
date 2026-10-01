"""HyperFrames render stage + opt-in stage planning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from core.config import AppConfig, ProjectSettings
from core.pipeline import Pipeline, _insert_opt_in
from core.project import Project
from modules.hyperframes import stage as hf


def _project(tmp_path: Path) -> Project:
    cfg = AppConfig(project=ProjectSettings(root=tmp_path / "projects"))
    cfg.repo_root = tmp_path
    return Project.create(cfg, "HF Demo")


def test_opt_in_stage_keeps_registry_position() -> None:
    order = ["scriptwriter", "voice", "video_assembler", "transcriber"]
    registry = ["scriptwriter", "voice", "video_assembler", "hyperframes", "transcriber"]
    assert _insert_opt_in(order, registry) == [
        "scriptwriter", "voice", "video_assembler", "hyperframes", "transcriber",
    ]


def test_only_plans_hyperframes_between_voice_and_transcriber(tmp_path: Path) -> None:
    proj = _project(tmp_path)
    assert "hyperframes" not in proj.config.pipeline.stages
    planned = Pipeline(proj.config)._plan(
        only=["transcriber", "hyperframes", "voice"], skip=None, from_stage=None
    )
    assert planned == ["voice", "hyperframes", "transcriber"]


def test_missing_composition_raises(tmp_path: Path) -> None:
    proj = _project(tmp_path)
    with pytest.raises(FileNotFoundError, match="composition"):
        hf.HyperframesStage().run(proj)


def test_check_then_render(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj = _project(tmp_path)
    comp = proj.paths.root / "composition"
    comp.mkdir()
    (comp / "index.html").write_text("<html></html>", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path, what: str) -> None:
        calls.append(cmd[1:3])
        if "render" in cmd:
            Path(cmd[cmd.index("--output") + 1]).write_bytes(b"mp4")

    monkeypatch.setattr(hf, "_npx", lambda: "npx")
    monkeypatch.setattr(hf, "_run", fake_run)
    monkeypatch.setenv("YT_STUDIO_HF_QUALITY", "draft")

    result = hf.HyperframesStage().run(proj)

    assert calls == [["hyperframes", "check"], ["hyperframes", "render"]]
    assert proj.paths.final_video.exists()
    assert result.meta["quality"] == "draft"
    assert "poster_time" not in result.meta


def test_bad_quality_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj = _project(tmp_path)
    (proj.paths.root / "composition").mkdir()
    (proj.paths.root / "composition" / "index.html").write_text("x", encoding="utf-8")
    monkeypatch.setenv("YT_STUDIO_HF_QUALITY", "ultra")
    with pytest.raises(ValueError, match="YT_STUDIO_HF_QUALITY"):
        hf.HyperframesStage().run(proj)


def test_read_poster_time(tmp_path: Path) -> None:
    assert hf.read_poster_time(tmp_path) is None
    (tmp_path / "poster.json").write_text(json.dumps({"time": 3.2}), encoding="utf-8")
    assert hf.read_poster_time(tmp_path) == 3.2
