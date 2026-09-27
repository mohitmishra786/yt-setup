"""Config loading defaults."""

from __future__ import annotations

from pathlib import Path

import yaml

from core.config import load_config


def test_defaults_without_file(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    # No pyproject — load_config still returns defaults
    cfg = load_config()
    assert "scriptwriter" in cfg.pipeline.stages
    assert cfg.voice.engine == "chatterbox"
    assert cfg.publisher.default_privacy == "private"


def test_yaml_override(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    data = {"voice": {"engine": "elevenlabs", "default_voice": "pro"}}
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    cfg = load_config(path)
    assert cfg.voice.engine == "elevenlabs"
    assert cfg.voice.default_voice == "pro"
