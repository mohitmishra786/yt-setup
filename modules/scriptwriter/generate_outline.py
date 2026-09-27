"""Stage 1 — Scriptwriter: Claude -> validated outline.json + seo.json."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from core.llm import LLMError, client_from_config
from core.logging_setup import get_logger
from core.project import Project
from core.schemas import SEOMetadata, Slide, SlideOutline
from core.stages import StageResult
from core.stub_utils import write_json

log = get_logger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def build_stub_outline(topic: str) -> SlideOutline:
    return SlideOutline(
        title=topic,
        target_duration_minutes=8,
        audience="general technical audience",
        slides=[
            Slide(
                index=1,
                title="Introduction",
                bullets=[f"What is {topic}?", "Why it matters", "What you will learn"],
                speaker_notes=(
                    f"Welcome. Today we are covering {topic}. "
                    "By the end of this video you will understand the core ideas "
                    "and how to apply them in practice."
                ),
                visual_hint="title card",
                visual_beat=(
                    "Centered title block with subtitle card, revealing topic keyword in "
                    "accent cyan with subtle underline draw-in"
                ),
            ),
            Slide(
                index=2,
                title="Core concepts",
                bullets=["Concept A", "Concept B", "Concept C"],
                speaker_notes=(
                    f"Let us break down the fundamentals of {topic}. "
                    "We will start with the building blocks, then connect them "
                    "into a practical mental model."
                ),
                visual_hint="three-column diagram",
                visual_beat=(
                    "Three labeled node boxes (Concept A, B, C) arranged horizontally with "
                    "directional connecting arrows revealing left-to-right"
                ),
            ),
            Slide(
                index=3,
                title="Summary and next steps",
                bullets=["Key takeaway", "Practice idea", "Watch next"],
                speaker_notes=(
                    "To recap: we covered the essentials, walked through a clear model, "
                    "and outlined what to do next. If this was useful, subscribe and "
                    "check the description for chapters and resources."
                ),
                visual_hint="outro CTA",
                visual_beat=(
                    "Summary container showing verified checkmarks and roadmap timeline "
                    "pointing forward"
                ),
            ),
        ],
        chapter_skeleton=[],
    )


def build_stub_outline_dict(topic: str) -> dict[str, Any]:
    data = build_stub_outline(topic).model_dump(by_alias=True)
    data["_stub"] = True
    return data


def build_stub_seo(topic: str) -> SEOMetadata:
    return SEOMetadata(
        title=topic[:70],
        description=(
            f"{topic} — full walkthrough.\n\n"
            "In this video we cover the essentials step by step.\n\n"
            "Chapters:\n"
            "(generated in the chapters stage)\n\n"
            "#tutorial\n"
        ),
        tags=[topic.lower()[:40], "tutorial", "guide", "explained"],
        hashtags=["#Tutorial"],
        category_hint="Education",
        thumbnail_text=topic[:40],
        hook_line=f"Here is a clear way to understand {topic}.",
    )


def _read_source_material(project: Project) -> str:
    source = project.context.get("source_file") or project.checkpoint.options.get(
        "source_file"
    )
    if not source:
        return ""
    path = Path(str(source))
    if not path.is_absolute():
        cand = project.config.repo_root / path
        path = cand if cand.exists() else path
    if not path.exists():
        log.warning("Source file not found: %s", path)
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    # Cap context size to keep prompts bounded
    max_chars = 40_000
    if len(text) > max_chars:
        log.warning("Source file truncated from %d to %d chars", len(text), max_chars)
        text = text[:max_chars]
    return text


def generate_outline_with_claude(project: Project, topic: str) -> SlideOutline:
    client = client_from_config(project.config)
    system = load_prompt("outline_prompt.md")
    source = _read_source_material(project)
    audience = project.checkpoint.options.get("audience") or "general technical audience"
    duration = project.checkpoint.options.get("target_duration_minutes") or 10

    user_parts = [
        f"Topic: {topic}",
        f"Target duration (minutes): {duration}",
        f"Audience: {audience}",
    ]
    if source:
        user_parts.append("Source material:\n" + source)
    keywords = project.checkpoint.options.get("keywords") or []
    if keywords:
        user_parts.append("Target keywords: " + ", ".join(str(k) for k in keywords))

    return client.complete_json(
        system=system,
        user="\n\n".join(user_parts),
        schema=SlideOutline,
    )


def generate_seo_with_claude(
    project: Project, topic: str, outline: SlideOutline
) -> SEOMetadata:
    client = client_from_config(project.config)
    system = load_prompt("seo_metadata_prompt.md")
    keywords = project.checkpoint.options.get("keywords") or []
    slide_summary = "\n".join(
        f"- {s.index}. {s.title}: {', '.join(s.bullets[:3])}" for s in outline.slides
    )
    user = (
        f"Working title: {outline.title}\n"
        f"Topic: {topic}\n"
        f"Audience: {outline.audience}\n"
        f"Target duration (minutes): {outline.target_duration_minutes}\n"
        f"Keywords: {', '.join(str(k) for k in keywords) if keywords else '(none)'}\n\n"
        f"Slide outline:\n{slide_summary}\n"
    )
    return client.complete_json(
        system=system,
        user=user,
        schema=SEOMetadata,
    )


class ScriptwriterStage:
    """Generate slide outline + SEO metadata via Anthropic Claude."""

    name = "scriptwriter"

    def run(self, project: Project) -> StageResult:
        topic = project.topic or "Untitled topic"
        force_stub = (
            os.getenv("YT_STUDIO_STUB_LLM") == "1"
            or project.checkpoint.options.get("stub_llm") is True
        )
        llm_client = client_from_config(project.config)
        use_real = (
            not force_stub
            and llm_client.available
            and os.getenv("YT_STUDIO_FORCE_STUB") != "1"
        )

        if use_real:
            log.info(
                "Scriptwriter (%s) topic=%r model=%s",
                type(llm_client).__name__,
                topic,
                llm_client.model,
            )
            try:
                outline = generate_outline_with_claude(project, topic)
                seo = generate_seo_with_claude(project, topic, outline)
                stub = False
            except LLMError as exc:
                # Production behavior: fail loudly unless allow_stub_fallback is set
                if project.checkpoint.options.get("allow_stub_fallback") or os.getenv(
                    "YT_STUDIO_ALLOW_LLM_FALLBACK"
                ) == "1":
                    log.error("LLM call failed (%s); falling back to stub outline", exc)
                    outline = build_stub_outline(topic)
                    seo = build_stub_seo(topic)
                    stub = True
                else:
                    raise
        else:
            reason = "no API key configured" if not llm_client.available else "stub forced"
            log.info("Scriptwriter (stub: %s) topic=%r", reason, topic)
            outline = build_stub_outline(topic)
            seo = build_stub_seo(topic)
            stub = True

        outline_data = outline.model_dump(by_alias=True)
        seo_data = seo.model_dump(by_alias=True)
        if stub:
            outline_data["_stub"] = True
            seo_data["_stub"] = True
        write_json(project.paths.outline, outline_data)
        write_json(project.paths.seo, seo_data)

        return StageResult(
            stage=self.name,
            artifacts=[
                project.rel(project.paths.outline),
                project.rel(project.paths.seo),
            ],
            meta={
                "slide_count": len(outline.slides),
                "stub": stub,
                "title": outline.title,
                "seo_title": seo.title,
            },
            message=(
                f"{'stub' if stub else 'claude'} outline with {len(outline.slides)} slides"
            ),
        )
