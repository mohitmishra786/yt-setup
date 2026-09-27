"""Stage 6 — transcript segments -> YouTube chapter markers."""

from __future__ import annotations

import json
import os
from typing import Any

from core.llm import LLMError, client_from_config
from core.logging_setup import get_logger
from core.project import Project
from core.schemas import ChapterMarker, ChaptersDocument
from core.stages import StageResult
from core.stub_utils import write_text

log = get_logger(__name__)

CHAPTERS_SYSTEM = """You are a YouTube chapter editor.

Given timestamped transcript segments, produce chapter markers for the video description.

Rules:
1. Return ONLY valid JSON: {"chapters":[{"start_seconds":0,"title":"Intro"}, ...]}
2. The first chapter MUST start at start_seconds=0.
3. Use 3 to 15 chapters depending on video length.
4. Titles: concise (2-6 words), no emojis, no leading numbers.
5. Prefer natural topic boundaries; do not place chapters less than MIN_GAP seconds apart.
6. start_seconds must be integers or whole seconds (floats allowed but prefer whole).
7. Cover the full video span using the last segment end as reference.
"""


def format_chapter_line(seconds: float, title: str) -> str:
    total = max(0, int(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        ts = f"{h}:{m:02d}:{s:02d}"
    else:
        ts = f"{m}:{s:02d}"
    return f"{ts} {title.strip()}"


def chapters_from_skeleton(outline: dict[str, Any]) -> ChaptersDocument:
    skeleton = list(outline.get("chapter_skeleton") or [])
    if not skeleton:
        slides = outline.get("slides") or []
        if slides:
            skeleton = [
                {"title": slides[0].get("title", "Intro"), "approx_minute": 0},
                {
                    "title": slides[len(slides) // 2].get("title", "Main"),
                    "approx_minute": 1,
                },
                {
                    "title": slides[-1].get("title", "Summary"),
                    "approx_minute": 2,
                },
            ]
        else:
            skeleton = [
                {"title": "Intro", "approx_minute": 0},
                {"title": "Main content", "approx_minute": 1},
                {"title": "Summary", "approx_minute": 2},
            ]
    markers: list[ChapterMarker] = []
    for i, ch in enumerate(skeleton):
        minutes = float(ch.get("approx_minute") or 0)
        seconds = 0.0 if i == 0 else minutes * 60.0
        markers.append(
            ChapterMarker(
                start_seconds=seconds,
                title=str(ch.get("title") or f"Part {i + 1}"),
            )
        )
    return ChaptersDocument(chapters=markers)


def chapters_from_segments_heuristic(
    segments: list[dict[str, Any]],
    *,
    min_gap: int,
    max_chapters: int,
) -> ChaptersDocument:
    """Heuristic chapters when LLM is unavailable: first segment + spaced samples."""
    if not segments:
        return ChaptersDocument(
            chapters=[ChapterMarker(start_seconds=0.0, title="Intro")]
        )

    markers = [ChapterMarker(start_seconds=0.0, title="Intro")]
    total_end = float(segments[-1].get("end") or 0)
    if total_end <= min_gap * 2:
        # Short video: intro + end-ish
        mid = segments[len(segments) // 2]
        markers.append(
            ChapterMarker(
                start_seconds=float(mid.get("start") or min_gap),
                title=_title_from_text(str(mid.get("text") or "Main")),
            )
        )
        return ChaptersDocument(chapters=markers)

    target_count = min(max_chapters, max(3, int(total_end // max(min_gap, 30))))
    step = total_end / target_count
    next_t = step
    for seg in segments[1:]:
        start = float(seg.get("start") or 0)
        if start < next_t:
            continue
        if start - markers[-1].start_seconds < min_gap:
            continue
        markers.append(
            ChapterMarker(
                start_seconds=start,
                title=_title_from_text(str(seg.get("text") or "Section")),
            )
        )
        next_t += step
        if len(markers) >= target_count:
            break
    return ChaptersDocument(chapters=markers)


def _title_from_text(text: str) -> str:
    words = text.strip().split()
    if not words:
        return "Section"
    title = " ".join(words[:6])
    title = title.rstrip(".,;:!")
    return title[:80] or "Section"


def chapters_with_claude(
    project: Project,
    segments: list[dict[str, Any]],
) -> ChaptersDocument:
    client = client_from_config(project.config)
    min_gap = project.config.chapters.min_chapter_gap_seconds
    max_ch = project.config.chapters.max_chapters
    # Compact segment list for prompt
    compact = [
        {
            "start": round(float(s.get("start") or 0), 1),
            "end": round(float(s.get("end") or 0), 1),
            "text": str(s.get("text") or "")[:200],
        }
        for s in segments[:200]
    ]
    system = CHAPTERS_SYSTEM.replace("MIN_GAP", str(min_gap))
    user = (
        f"Video topic: {project.topic}\n"
        f"Max chapters: {max_ch}\n"
        f"Min gap seconds: {min_gap}\n"
        f"Segments JSON:\n{json.dumps(compact, ensure_ascii=False)}"
    )
    return client.complete_json(
        system=system,
        user=user,
        schema=ChaptersDocument,
        temperature=0.2,
    )


def merge_chapters_into_seo(project: Project, chapters_text: str) -> None:
    if not project.paths.seo.exists():
        return
    with project.paths.seo.open(encoding="utf-8") as fh:
        seo = json.load(fh)
    desc = str(seo.get("description") or "")
    if "(generated in the chapters stage)" in desc:
        desc = desc.replace("(generated in the chapters stage)", chapters_text.strip())
    elif "Chapters:" in desc:
        # Replace everything after Chapters: until blank-line-double or end of section
        parts = desc.split("Chapters:", 1)
        head = parts[0] + "Chapters:\n" + chapters_text.strip() + "\n"
        # Drop old chapter block: keep content after first double newline following
        rest = parts[1]
        # If rest starts with chapter-like lines, skip until blank line
        lines = rest.splitlines()
        i = 0
        if lines and not lines[0].strip():
            i = 1
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                break
            # chapter line pattern roughly "0:00 Title" or "1:23 Title"
            if line[0].isdigit() and ":" in line.split()[0]:
                i += 1
                continue
            break
        tail = "\n".join(lines[i:]).lstrip("\n")
        desc = head + ("\n" + tail if tail else "\n")
    else:
        desc = desc.rstrip() + "\n\nChapters:\n" + chapters_text.strip() + "\n"
    seo["description"] = desc
    project.paths.seo.write_text(
        json.dumps(seo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


class ChaptersStage:
    """Produce chapters.txt for the YouTube description."""

    name = "chapters"

    def run(self, project: Project) -> StageResult:
        if not project.paths.transcript_json.exists():
            raise FileNotFoundError(
                f"Missing transcript.json — run transcriber first: "
                f"{project.paths.transcript_json}"
            )

        with project.paths.transcript_json.open(encoding="utf-8") as fh:
            transcript = json.load(fh)
        segments = list(transcript.get("segments") or [])

        use_llm = (
            bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
            and os.getenv("YT_STUDIO_STUB_LLM") != "1"
            and os.getenv("YT_STUDIO_FORCE_STUB") != "1"
        )

        doc: ChaptersDocument
        source = "heuristic"
        if use_llm and segments and transcript.get("engine") != "stub":
            try:
                doc = chapters_with_claude(project, segments)
                source = "claude"
            except LLMError as exc:
                log.warning("Chapter LLM failed (%s); heuristic", exc)
                doc = chapters_from_segments_heuristic(
                    segments,
                    min_gap=project.config.chapters.min_chapter_gap_seconds,
                    max_chapters=project.config.chapters.max_chapters,
                )
        elif segments and transcript.get("engine") != "stub":
            doc = chapters_from_segments_heuristic(
                segments,
                min_gap=project.config.chapters.min_chapter_gap_seconds,
                max_chapters=project.config.chapters.max_chapters,
            )
        else:
            outline: dict[str, Any] = {}
            if project.paths.outline.exists():
                with project.paths.outline.open(encoding="utf-8") as fh:
                    outline = json.load(fh)
            doc = chapters_from_skeleton(outline)
            source = "skeleton"

        # Enforce max chapters + min gap post-process
        doc = _post_process(
            doc,
            min_gap=project.config.chapters.min_chapter_gap_seconds,
            max_chapters=project.config.chapters.max_chapters,
        )

        body = doc.to_youtube_text()
        write_text(project.paths.chapters, body)
        merge_chapters_into_seo(project, body)

        log.info("Chapters source=%s count=%d", source, len(doc.chapters))
        return StageResult(
            stage=self.name,
            artifacts=[project.rel(project.paths.chapters)],
            meta={
                "chapter_count": len(doc.chapters),
                "source": source,
                "stub": source == "skeleton",
            },
            message=f"{len(doc.chapters)} chapters via {source}",
        )


def _post_process(
    doc: ChaptersDocument, *, min_gap: int, max_chapters: int
) -> ChaptersDocument:
    chapters = list(doc.chapters)
    if not chapters:
        chapters = [ChapterMarker(start_seconds=0.0, title="Intro")]
    chapters[0].start_seconds = 0.0
    chapters.sort(key=lambda c: c.start_seconds)
    cleaned: list[ChapterMarker] = [chapters[0]]
    for ch in chapters[1:]:
        if ch.start_seconds - cleaned[-1].start_seconds < min_gap:
            continue
        cleaned.append(ch)
        if len(cleaned) >= max_chapters:
            break
    return ChaptersDocument(chapters=cleaned)
