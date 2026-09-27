"""Import existing PPTX without Claude API."""

from __future__ import annotations

import json
from pathlib import Path

from modules.slidebuilder.import_pptx import (
    extract_outline_from_pptx,
    import_pptx_into_project,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck.pptx"


def test_extract_outline() -> None:
    assert FIXTURE.exists()
    outline = extract_outline_from_pptx(FIXTURE, deck_title="Sample")
    assert len(outline.slides) >= 3
    assert outline.slides[0].title == "Welcome"
    assert "Welcome everyone" in outline.slides[0].speaker_notes


def test_import_into_project(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    info = import_pptx_into_project(root, FIXTURE, topic="Sample Topic")
    assert (root / "slides.pptx").exists()
    assert (root / "outline.json").exists()
    assert (root / "seo.json").exists()
    data = json.loads((root / "outline.json").read_text(encoding="utf-8"))
    assert data["slides"][0]["title"] == "Welcome"
    assert info["slide_count"] >= 3
