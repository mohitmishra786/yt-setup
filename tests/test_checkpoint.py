"""Checkpoint atomicity and status transitions."""

from __future__ import annotations

from pathlib import Path

from core.checkpoint import Checkpoint, StageStatus


def test_checkpoint_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    cp = Checkpoint.new("demo", ["scriptwriter", "slidebuilder"], topic="Hello")
    cp.mark_running("scriptwriter")
    cp.mark_completed("scriptwriter", artifacts=["outline.json"])
    cp.save(path)

    loaded = Checkpoint.load(path)
    assert loaded.project_id == "demo"
    assert loaded.topic == "Hello"
    assert loaded.is_completed("scriptwriter")
    assert loaded.get("slidebuilder").status == StageStatus.PENDING
    assert loaded.get("scriptwriter").artifacts == ["outline.json"]


def test_mark_failed(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    cp = Checkpoint.new("demo", ["voice"])
    cp.mark_running("voice")
    cp.mark_failed("voice", "boom")
    cp.save(path)
    loaded = Checkpoint.load(path)
    assert loaded.get("voice").status == StageStatus.FAILED
    assert loaded.get("voice").error == "boom"
