"""Stage 2 — Storyboard: Outline -> choreographed visual beats (storyboard.json)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from core.llm import LLMError, client_from_config
from core.logging_setup import get_logger
from core.project import Project
from core.schemas import (
    SlideOutline,
    Storyboard,
    StoryboardBeat,
    VisualAction,
    VisualElement,
)
from core.stages import StageResult
from core.stub_utils import write_json

from modules.scenegen.tokens import TOKENS

log = get_logger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def build_stub_storyboard(outline: SlideOutline) -> Storyboard:
    """
    Generate a deterministic, high-quality storyboard from an outline.

    Enforces CoreDumpped / 3B1B design grammar:
    - One idea revealed at a time with staggered timing
    - 1.5–3.0s pause after each reveal for readability
    - Meaningful state transitions (movement, draw, highlight)
    - Token palette compliance
    """
    beats: list[StoryboardBeat] = []

    for i, slide in enumerate(outline.slides, start=1):
        beat_id = f"scene_{i:02d}"
        notes = slide.speaker_notes or slide.title
        reading_dur = TOKENS.estimate_reading_duration(notes)

        # Base layout coordinates on standard 1920x1080 canvas
        elements: list[VisualElement] = []
        actions: list[VisualAction] = []
        live_accent = "accent_primary"

        if i == 1:
            # Beat 1: Intro / Concept Anchor
            live_accent = "accent_primary"
            elements.append(
                VisualElement(
                    id="title_box",
                    type="box",
                    label=slide.title,
                    x=460,
                    y=380,
                    width=1000,
                    height=200,
                    initial_state="hidden",
                )
            )
            elements.append(
                VisualElement(
                    id="subtitle_badge",
                    type="label",
                    label=f"Mental Model • {outline.title}",
                    x=560,
                    y=610,
                    width=800,
                    height=60,
                    initial_state="hidden",
                )
            )
            actions.append(
                VisualAction(action="enter", target_id="title_box", start_time=0.8, duration=0.6)
            )
            actions.append(
                VisualAction(
                    action="enter", target_id="subtitle_badge", start_time=3.0, duration=0.5
                )
            )
            actions.append(
                VisualAction(
                    action="highlight", target_id="title_box", start_time=5.5, duration=0.4
                )
            )

        elif i == len(outline.slides):
            # Final Beat: Summary / Next Steps timeline
            live_accent = "accent_success"
            elements.append(
                VisualElement(
                    id="summary_lane",
                    type="timeline",
                    label="Key Takeaways",
                    x=360,
                    y=320,
                    width=1200,
                    height=180,
                    items=[b.strip() for b in slide.bullets[:3]]
                    or ["Foundations", "Architecture", "Best Practices"],
                    initial_state="hidden",
                )
            )
            elements.append(
                VisualElement(
                    id="next_step_box",
                    type="box",
                    label="Next: Practical Implementation",
                    x=660,
                    y=620,
                    width=600,
                    height=140,
                    initial_state="hidden",
                )
            )
            actions.append(
                VisualAction(action="enter", target_id="summary_lane", start_time=1.0, duration=0.6)
            )
            actions.append(
                VisualAction(
                    action="enter", target_id="next_step_box", start_time=3.8, duration=0.5
                )
            )
            actions.append(
                VisualAction(
                    action="highlight", target_id="next_step_box", start_time=6.2, duration=0.4
                )
            )

        else:
            # Intermediate Beats: Systems/CS diagram (nodes, arrows, queue/state transition)
            accent_choices = [
                "accent_primary",
                "accent_purple",
                "accent_warning",
                "accent_secondary",
            ]
            live_accent = accent_choices[(i - 2) % len(accent_choices)]

            # 3-node connected flow or queue visualization
            elements.append(
                VisualElement(
                    id="node_left",
                    type="box",
                    label=slide.bullets[0] if len(slide.bullets) > 0 else "Source / Input",
                    x=280,
                    y=460,
                    width=340,
                    height=160,
                    initial_state="hidden",
                )
            )
            elements.append(
                VisualElement(
                    id="arrow_flow_1",
                    type="arrow",
                    label="dispatch",
                    from_id="node_left",
                    to_id="node_center",
                    initial_state="hidden",
                )
            )
            elements.append(
                VisualElement(
                    id="node_center",
                    type="box",
                    label=slide.bullets[1] if len(slide.bullets) > 1 else slide.title,
                    x=790,
                    y=460,
                    width=340,
                    height=160,
                    initial_state="hidden",
                )
            )
            elements.append(
                VisualElement(
                    id="arrow_flow_2",
                    type="arrow",
                    label="commit",
                    from_id="node_center",
                    to_id="node_right",
                    initial_state="hidden",
                )
            )
            elements.append(
                VisualElement(
                    id="node_right",
                    type="box",
                    label=slide.bullets[2] if len(slide.bullets) > 2 else "Resolved State",
                    x=1300,
                    y=460,
                    width=340,
                    height=160,
                    initial_state="hidden",
                )
            )

            # Choreograph sequential reveal with pauses
            actions.append(
                VisualAction(action="enter", target_id="node_left", start_time=0.8, duration=0.5)
            )
            actions.append(
                VisualAction(action="draw", target_id="arrow_flow_1", start_time=2.8, duration=0.6)
            )
            actions.append(
                VisualAction(action="enter", target_id="node_center", start_time=4.6, duration=0.5)
            )
            actions.append(
                VisualAction(action="draw", target_id="arrow_flow_2", start_time=6.8, duration=0.6)
            )
            actions.append(
                VisualAction(action="enter", target_id="node_right", start_time=8.6, duration=0.5)
            )
            actions.append(
                VisualAction(
                    action="highlight", target_id="node_center", start_time=10.8, duration=0.5
                )
            )

        # Ensure duration estimate accommodates both narration and choreographed action holds
        last_action_end = max((a.start_time + a.duration for a in actions), default=5.0)
        duration_est = max(reading_dur, last_action_end + TOKENS.default_hold_per_reveal)

        beats.append(
            StoryboardBeat(
                id=beat_id,
                index=i,
                title=slide.title,
                narration_text=notes,
                duration_estimate=round(duration_est, 2),
                live_accent=live_accent,
                visual_beat=slide.visual_beat or f"Diagram progression for {slide.title}",
                elements=elements,
                actions=actions,
            )
        )

    return Storyboard(
        title=outline.title,
        topic=outline.title,
        target_duration_minutes=outline.target_duration_minutes,
        audience=outline.audience,
        beats=beats,
        _stub=True,
    )


def generate_storyboard_with_llm(project: Project, outline: SlideOutline) -> Storyboard:
    """Call director LLM to design the visual choreography from outline."""
    client = client_from_config(project.config)
    system = load_prompt("storyboard_prompt.md")

    slides_summary = []
    for s in outline.slides:
        slides_summary.append(
            f"Beat {s.index}: {s.title}\n"
            f"Visual Hint / Beat: {s.visual_beat or s.visual_hint or '(diagram)'}\n"
            f"Spoken Narration: {s.speaker_notes}\n"
            f"Key Points: {', '.join(s.bullets)}\n"
        )

    user = (
        f"Video Title: {outline.title}\n"
        f"Audience: {outline.audience}\n"
        f"Target Duration (min): {outline.target_duration_minutes}\n\n"
        f"Narrative Beats from Outline:\n\n"
        + "\n---\n".join(slides_summary)
        + "\n\nProduce the full, synchronized Storyboard with sequential element "
        "reveals and pacing holds."
    )

    return client.complete_json(
        system=system,
        user=user,
        schema=Storyboard,
    )


class StoryboardStage:
    """Stage 2 — Storyboard: Consumes outline.json, generates storyboard.json."""

    name = "storyboard"

    def run(self, project: Project) -> StageResult:
        if not project.paths.outline.exists():
            raise FileNotFoundError(
                f"Missing outline.json — run scriptwriter stage first: {project.paths.outline}"
            )

        with project.paths.outline.open(encoding="utf-8") as fh:
            outline_data = json.load(fh)
        outline = SlideOutline.model_validate(outline_data)

        force_stub = (
            os.getenv("YT_STUDIO_STUB_LLM") == "1"
            or project.checkpoint.options.get("stub_llm") is True
            or project.checkpoint.options.get("stub_storyboard") is True
        )
        llm_client = client_from_config(project.config)
        use_real = (
            not force_stub and llm_client.available and os.getenv("YT_STUDIO_FORCE_STUB") != "1"
        )

        storyboard_path = project.paths.root / "storyboard.json"

        if use_real:
            log.info("Storyboard (Director %s) topic=%r", type(llm_client).__name__, outline.title)
            try:
                storyboard = generate_storyboard_with_llm(project, outline)
                stub = False
            except LLMError as exc:
                if (
                    project.checkpoint.options.get("allow_stub_fallback")
                    or os.getenv("YT_STUDIO_ALLOW_LLM_FALLBACK") == "1"
                ):
                    log.error("Director LLM failed (%s); falling back to stub storyboard", exc)
                    storyboard = build_stub_storyboard(outline)
                    stub = True
                else:
                    raise
        else:
            reason = "no API key configured" if not llm_client.available else "stub forced"
            log.info("Storyboard (stub: %s) beats=%d", reason, len(outline.slides))
            storyboard = build_stub_storyboard(outline)
            stub = True

        sb_data = storyboard.model_dump(by_alias=True)
        if stub:
            sb_data["_stub"] = True
        write_json(storyboard_path, sb_data)

        return StageResult(
            stage=self.name,
            artifacts=[project.rel(storyboard_path)],
            meta={
                "beat_count": len(storyboard.beats),
                "total_duration_estimate": storyboard.total_duration_estimate,
                "stub": stub,
            },
            message=(
                f"{'stub' if stub else 'llm'} storyboard with "
                f"{len(storyboard.beats)} beats ({storyboard.total_duration_estimate:.1f}s est)"
            ),
        )
