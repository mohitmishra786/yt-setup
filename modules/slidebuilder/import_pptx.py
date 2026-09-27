"""Import an existing .pptx (e.g. from Claude.ai UI) into a project.

Extracts slide titles, body bullets, and speaker notes into outline.json so the
pipeline can continue from voice without Claude API or slidebuilder.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from core.logging_setup import get_logger
from core.schemas import ChapterSkeletonItem, Slide, SlideOutline
from core.stub_utils import write_json

log = get_logger(__name__)


def _shape_text(shape) -> str:
    if not getattr(shape, "has_text_frame", False):
        return ""
    parts: list[str] = []
    for para in shape.text_frame.paragraphs:
        t = "".join(run.text for run in para.runs).strip()
        if not t:
            t = (para.text or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts).strip()


def _collect_text_blocks(slide) -> list[str]:
    blocks: list[str] = []
    for shape in slide.shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            continue
        text = _shape_text(shape)
        if text:
            blocks.append(text)
    return blocks


def _speaker_notes(slide) -> str:
    try:
        if not slide.has_notes_slide:
            return ""
        tf = slide.notes_slide.notes_text_frame
        return (tf.text or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _guess_title_and_bullets(blocks: list[str]) -> tuple[str, list[str]]:
    if not blocks:
        return "Untitled slide", []
    title = blocks[0].splitlines()[0].strip()[:200] or "Untitled slide"
    bullets: list[str] = []
    # Remaining lines from first block + later blocks become bullets
    first_lines = blocks[0].splitlines()[1:]
    for line in first_lines:
        line = line.strip().lstrip("•-*–— ").strip()
        if line:
            bullets.append(line[:120])
    for block in blocks[1:]:
        for line in block.splitlines():
            line = line.strip().lstrip("•-*–— ").strip()
            if line and line != title:
                bullets.append(line[:120])
    # de-dupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for b in bullets:
        key = b.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(b)
    return title, uniq[:8]


def extract_outline_from_pptx(
    pptx_path: Path,
    *,
    deck_title: str | None = None,
) -> SlideOutline:
    """Parse a PPTX into a SlideOutline (speaker notes preferred for narration)."""
    if not pptx_path.exists():
        raise FileNotFoundError(f"PPTX not found: {pptx_path}")

    prs = Presentation(str(pptx_path))
    slides_out: list[Slide] = []
    for i, slide in enumerate(prs.slides, start=1):
        blocks = _collect_text_blocks(slide)
        title, bullets = _guess_title_and_bullets(blocks)
        notes = _speaker_notes(slide)
        if not notes:
            # Synthesize usable narration from on-slide text when notes are empty
            bits = [title] + bullets
            notes = ". ".join(bits) + "."
            log.warning(
                "Slide %d has no speaker notes; synthesized notes from title/bullets. "
                "For best narration, add speaker notes in PowerPoint/Keynote before import.",
                i,
            )
        slides_out.append(
            Slide(
                index=i,
                title=title,
                bullets=bullets,
                speaker_notes=notes,
                visual_hint="imported",
            )
        )

    if len(slides_out) < 1:
        raise ValueError(f"No slides found in {pptx_path}")

    # SlideOutline requires min 3 slides — pad only if needed for schema, but
    # prefer real content. Use model with relaxed rebuild if short decks.
    title = deck_title or Path(pptx_path).stem.replace("_", " ").replace("-", " ")
    if len(slides_out) < 3:
        log.warning(
            "Deck has only %d slide(s). Padding outline to meet pipeline minimum of 3 "
            "(duplicate last slide structure for schema). Prefer decks with 3+ slides.",
            len(slides_out),
        )
        while len(slides_out) < 3:
            last = slides_out[-1]
            slides_out.append(
                Slide(
                    index=len(slides_out) + 1,
                    title=last.title,
                    bullets=list(last.bullets),
                    speaker_notes=last.speaker_notes,
                    visual_hint="imported-padded",
                )
            )

    return SlideOutline(
        title=title,
        target_duration_minutes=max(5.0, len(slides_out) * 0.75),
        audience="imported deck",
        slides=slides_out,
        chapter_skeleton=[
            ChapterSkeletonItem(title=slides_out[0].title, approx_minute=0),
            ChapterSkeletonItem(
                title=slides_out[len(slides_out) // 2].title,
                approx_minute=max(1.0, len(slides_out) * 0.3),
            ),
            ChapterSkeletonItem(
                title=slides_out[-1].title,
                approx_minute=max(2.0, len(slides_out) * 0.7),
            ),
        ],
    )


def import_pptx_into_project(
    project_root: Path,
    pptx_path: Path,
    *,
    deck_title: str | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    """
    Copy PPTX to project/slides.pptx and write outline.json + minimal seo.json.

    Returns paths written.
    """
    project_root.mkdir(parents=True, exist_ok=True)
    dest = project_root / "slides.pptx"
    src = pptx_path.resolve()
    if src != dest.resolve():
        shutil.copy2(src, dest)

    outline = extract_outline_from_pptx(dest, deck_title=deck_title or topic)
    outline_path = project_root / "outline.json"
    write_json(outline_path, outline.model_dump(by_alias=True))

    seo = {
        "_imported": True,
        "title": (topic or outline.title)[:100],
        "description": (
            f"{outline.title}\n\n"
            "Imported from existing PowerPoint. Chapters will be filled after transcription.\n\n"
            "Chapters:\n"
            "(generated in the chapters stage)\n"
        ),
        "tags": _tags_from_title(outline.title),
        "hashtags": [],
        "category_hint": "Education",
        "thumbnail_text": outline.title[:40],
        "hook_line": outline.slides[0].speaker_notes[:160],
    }
    seo_path = project_root / "seo.json"
    write_json(seo_path, seo)

    log.info(
        "Imported PPTX slides=%d notes_ok=%s -> %s",
        len(outline.slides),
        sum(1 for s in outline.slides if s.visual_hint != "imported" or True),
        dest,
    )
    return {
        "slides": str(dest),
        "outline": str(outline_path),
        "seo": str(seo_path),
        "slide_count": len(outline.slides),
        "title": outline.title,
    }


def import_outline_json(
    project_root: Path,
    outline_path: Path,
    *,
    seo_path: Path | None = None,
) -> dict[str, Any]:
    """Copy a hand-written / Claude.ai-exported outline JSON into the project."""
    import json

    project_root.mkdir(parents=True, exist_ok=True)
    with outline_path.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    outline = SlideOutline.model_validate(raw)
    dest_outline = project_root / "outline.json"
    write_json(dest_outline, outline.model_dump(by_alias=True))

    dest_seo = project_root / "seo.json"
    if seo_path and seo_path.exists():
        shutil.copy2(seo_path, dest_seo)
    elif not dest_seo.exists():
        write_json(
            dest_seo,
            {
                "_imported": True,
                "title": outline.title[:100],
                "description": f"{outline.title}\n\nChapters:\n(generated in the chapters stage)\n",
                "tags": _tags_from_title(outline.title),
                "hashtags": [],
                "category_hint": "Education",
                "thumbnail_text": outline.title[:40],
                "hook_line": outline.slides[0].speaker_notes[:160],
            },
        )
    return {
        "outline": str(dest_outline),
        "seo": str(dest_seo),
        "slide_count": len(outline.slides),
        "title": outline.title,
    }


def _tags_from_title(title: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9]+", title.lower())
    tags = [title.lower()[:40], "tutorial", "explained"]
    tags.extend(w for w in words if len(w) > 3)
    # unique
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:20]
