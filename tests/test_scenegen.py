"""Tests for modules/scenegen: tokens, storyboard schema, components, and visual QA."""

from __future__ import annotations

from pathlib import Path

from core.schemas import (
    Storyboard,
    StoryboardBeat,
    VisualAction,
    VisualElement,
    storyboard_from_dict,
)
from modules.scenegen.builder import build_scene_html
from modules.scenegen.components import (
    render_arrow,
    render_box,
    render_memory_grid,
    render_queue,
    render_state_machine,
    render_timeline,
)
from modules.scenegen.qa import (
    check_palette_compliance,
    check_sequential_reveals,
)
from modules.scenegen.renderer import render_scene_stub
from modules.scenegen.tokens import DEFAULT_DESIGN_TOKENS, TOKENS


def test_design_tokens_properties() -> None:
    tokens = DEFAULT_DESIGN_TOKENS
    assert tokens.width == 1920
    assert tokens.height == 1080
    assert tokens.fps == 30
    assert tokens.bg_color.startswith("#")
    assert tokens.accent_primary.startswith("#")
    assert tokens.default_hold_per_reveal >= 1.5
    assert tokens.per_word_reading_pace > 0.0

    css = tokens.to_css_variables()
    assert ":root" in css
    assert "--bg-color:" in css
    assert "--accent-primary:" in css
    assert f"{tokens.bg_color}" in css


def test_tokens_reading_pace_calculation() -> None:
    short_text = "Hello world"
    long_text = " ".join(["word"] * 50)
    dur_short = TOKENS.estimate_reading_duration(short_text)
    dur_long = TOKENS.estimate_reading_duration(long_text)
    assert dur_short >= TOKENS.default_hold_per_reveal
    assert dur_long > dur_short
    assert dur_long >= 50 * TOKENS.per_word_reading_pace


def test_storyboard_schema_validation() -> None:
    beat = StoryboardBeat(
        id="scene_01",
        index=1,
        title="Architecture Overview",
        narration_text="In this diagram, the client connects directly to the gateway server.",
        duration_estimate=12.0,
        live_accent="accent_primary",
        visual_beat="Two nodes with connecting arrow",
        elements=[
            VisualElement(
                id="client", type="box", label="Client", x=200, y=400, width=240, height=120
            ),
            VisualElement(
                id="gateway", type="box", label="Gateway", x=800, y=400, width=240, height=120
            ),
            VisualElement(id="conn", type="arrow", label="TCP", from_id="client", to_id="gateway"),
        ],
        actions=[
            VisualAction(action="enter", target_id="client", start_time=1.0, duration=0.5),
            VisualAction(action="enter", target_id="gateway", start_time=3.5, duration=0.5),
            VisualAction(action="draw", target_id="conn", start_time=6.0, duration=0.8),
        ],
    )

    sb = Storyboard(
        title="System Architecture Explained",
        topic="Architecture",
        beats=[beat],
    )
    assert sb.beats[0].id == "scene_01"
    assert sb.total_duration_estimate == 12.0

    # Serialization roundtrip
    dumped = sb.model_dump()
    loaded = storyboard_from_dict(dumped)
    assert loaded.title == sb.title
    assert len(loaded.beats) == 1
    assert loaded.beats[0].elements[0].label == "Client"


def test_component_rendering() -> None:
    box_html = render_box("box1", "Database", 100, 200, state="active")
    assert 'id="box1"' in box_html
    assert "Database" in box_html
    assert "cs-box" in box_html

    arrow_html = render_arrow("arr1", 100, 100, 400, 100, label="query")
    assert 'id="arr1"' in arrow_html
    assert "query" in arrow_html
    assert "<path" in arrow_html

    queue_html = render_queue("q1", 100, 300, ["msg1", "msg2"], label="Ingest Queue")
    assert "Ingest Queue" in queue_html
    assert "msg1" in queue_html

    tl_html = render_timeline("tl1", 100, 500, steps=["Parse", "Validate", "Execute"])
    assert "Validate" in tl_html

    grid_html = render_memory_grid("mem1", 100, 700, cells=[("0x00", "VAL_A"), ("0x04", "VAL_B")])
    assert "0x00" in grid_html
    assert "VAL_A" in grid_html

    sm_html = render_state_machine("sm1", 100, 800, states=["INIT", "RUN", "HALT"])
    assert "RUN" in sm_html


def test_build_scene_html() -> None:
    beat = StoryboardBeat(
        id="scene_02",
        index=2,
        title="Packet Routing",
        narration_text=(
            "The kernel inspects the incoming frame header before copying to user memory."
        ),
        duration_estimate=15.0,
        live_accent="accent_primary",
        elements=[
            VisualElement(id="nic", type="box", label="NIC", x=300, y=400, width=200, height=120),
            VisualElement(
                id="ring", type="queue", label="Ring Buffer", x=700, y=400, items=["pkt_1"]
            ),
        ],
        actions=[
            VisualAction(action="enter", target_id="nic", start_time=1.0, duration=0.5),
            VisualAction(action="enter", target_id="ring", start_time=3.5, duration=0.5),
        ],
    )

    html = build_scene_html(beat)
    assert "<!DOCTYPE html>" in html
    assert "SCENE 02" in html
    assert "Packet Routing" in html
    assert 'id="nic"' in html
    assert 'id="ring"' in html
    assert "window.seekTo" in html


def test_visual_qa_sequential_reveals_heuristic() -> None:
    # Violates single reveal: two elements entering simultaneously
    bad_beat = StoryboardBeat(
        id="scene_bad",
        index=1,
        title="Bad Timing",
        narration_text="Narration here.",
        duration_estimate=10.0,
        actions=[
            VisualAction(action="enter", target_id="node_a", start_time=1.0, duration=0.5),
            VisualAction(
                action="enter", target_id="node_b", start_time=1.2, duration=0.5
            ),  # only 0.2s delta!
        ],
    )
    violations = check_sequential_reveals(bad_beat, min_stagger_seconds=1.0)
    assert len(violations) > 0
    assert "enter too quickly" in violations[0]

    # Compliant: staggered by 2.0s
    good_beat = StoryboardBeat(
        id="scene_good",
        index=1,
        title="Good Timing",
        narration_text="Narration here.",
        duration_estimate=10.0,
        actions=[
            VisualAction(action="enter", target_id="node_a", start_time=1.0, duration=0.5),
            VisualAction(action="enter", target_id="node_b", start_time=3.2, duration=0.5),
        ],
    )
    assert len(check_sequential_reveals(good_beat, min_stagger_seconds=1.0)) == 0


def test_visual_qa_palette_compliance() -> None:
    # Valid tokens
    clean_html = (
        f"<div style='background-color: {TOKENS.bg_color}; color: {TOKENS.text_primary};'></div>"
    )
    assert len(check_palette_compliance(clean_html, TOKENS)) == 0

    # Off-brand color
    dirty_html = "<div style='background-color: #ff00ff; color: #123456;'></div>"
    violations = check_palette_compliance(dirty_html, TOKENS)
    assert len(violations) > 0


def test_scene_render_stub(tmp_path: Path) -> None:
    mp4_out = tmp_path / "test_scene.mp4"
    render_scene_stub(mp4_out, duration=2.0)
    assert mp4_out.exists()
    assert mp4_out.stat().st_size > 500
