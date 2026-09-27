"""Chapter formatting rules."""

from __future__ import annotations

from modules.chapters.generate_chapters import format_chapter_line


def test_format_under_one_hour() -> None:
    assert format_chapter_line(0, "Intro") == "0:00 Intro"
    assert format_chapter_line(92, "Topic") == "1:32 Topic"


def test_format_over_one_hour() -> None:
    assert format_chapter_line(3661, "Deep dive") == "1:01:01 Deep dive"
