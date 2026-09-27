"""JSON extraction and schema validation helpers."""

from __future__ import annotations

import pytest

from core.llm import extract_json_object
from core.schemas import ChaptersDocument, SEOMetadata, SlideOutline


def test_extract_raw_json() -> None:
    data = extract_json_object('{"title": "Hi", "x": 1}')
    assert data["title"] == "Hi"


def test_extract_fenced_json() -> None:
    text = """Here you go:
```json
{"a": 2, "b": "ok"}
```
"""
    assert extract_json_object(text)["a"] == 2


def test_slide_outline_renumbers() -> None:
    outline = SlideOutline.model_validate(
        {
            "title": "Demo",
            "slides": [
                {
                    "index": 9,
                    "title": "A",
                    "bullets": ["one"],
                    "speaker_notes": "Hello there friends.",
                },
                {
                    "index": 9,
                    "title": "B",
                    "bullets": ["two"],
                    "speaker_notes": "More narration for slide two here.",
                },
                {
                    "index": 9,
                    "title": "C",
                    "bullets": ["three"],
                    "speaker_notes": "Closing thoughts for the audience today.",
                },
            ],
        }
    )
    assert [s.index for s in outline.slides] == [1, 2, 3]
    assert outline.chapter_skeleton


def test_seo_title_trim() -> None:
    seo = SEOMetadata(title="x" * 120, description="desc here is long enough")
    assert len(seo.title) <= 100


def test_chapters_first_zero() -> None:
    doc = ChaptersDocument.model_validate(
        {
            "chapters": [
                {"start_seconds": 12, "title": "Later"},
                {"start_seconds": 0, "title": "Intro"},
            ]
        }
    )
    assert doc.chapters[0].start_seconds == 0.0
    text = doc.to_youtube_text()
    assert text.startswith("0:00")
