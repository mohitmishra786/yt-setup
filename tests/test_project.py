"""Project id slugification and path layout."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from core.config import AppConfig, ProjectSettings
from core.project import Project, make_project_id, slugify


def test_slugify() -> None:
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  Rust: Async?  ") == "rust-async"
    assert slugify("") == "untitled"


def test_make_project_id() -> None:
    pid = make_project_id("Docker Networking", when=date(2026, 7, 9))
    assert pid == "2026-07-09_docker-networking"


def test_project_create_and_load(tmp_path: Path) -> None:
    cfg = AppConfig(project=ProjectSettings(root=tmp_path / "projects"))
    cfg.repo_root = tmp_path
    proj = Project.create(cfg, "Unit Test Video", voice_id="mohit")
    assert proj.paths.state.exists()
    assert proj.paths.audio_dir.is_dir()
    assert proj.voice_id == "mohit"

    loaded = Project.load(cfg, proj.project_id)
    assert loaded.topic == "Unit Test Video"
    assert loaded.paths.root == proj.paths.root
