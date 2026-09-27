"""Pillow frame renderer."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from core.schemas import Slide, SlideOutline
from modules.video_assembler.frame_renderer import render_outline_frames


def test_render_frames(tmp_path: Path) -> None:
    outline = SlideOutline(
        title="Frames",
        slides=[
            Slide(index=1, title="One", bullets=["x"], speaker_notes="Narration one is here."),
            Slide(index=2, title="Two", bullets=["y"], speaker_notes="Narration two is here."),
            Slide(index=3, title="Three", bullets=["z"], speaker_notes="Narration three is here."),
        ],
    )
    frames = render_outline_frames(outline, tmp_path / "frames", width=640, height=360)
    assert len(frames) == 3
    img = Image.open(frames[0])
    assert img.size == (640, 360)
