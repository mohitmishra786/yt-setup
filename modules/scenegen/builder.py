"""HTML/CSS/JS scene builder using design tokens and diagram primitives."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from core.schemas import StoryboardBeat, VisualElement

from modules.scenegen.components import (
    all_components_css,
    render_arrow,
    render_box,
    render_memory_grid,
    render_queue,
    render_state_machine,
    render_timeline,
)
from modules.scenegen.tokens import DEFAULT_DESIGN_TOKENS, DesignTokens


def _resolve_element_coords(
    elements: list[VisualElement],
) -> dict[str, dict[str, float]]:
    """Map element ID to center coordinates (cx, cy, width, height)."""
    coords: dict[str, dict[str, float]] = {}
    for el in elements:
        w = el.width or 280.0
        h = el.height or 140.0
        x = el.x
        y = el.y
        coords[el.id] = {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "cx": x + w / 2,
            "cy": y + h / 2,
        }
    return coords


def build_scene_html(
    beat: StoryboardBeat,
    tokens: DesignTokens | None = None,
) -> str:
    """
    Construct a complete, self-contained HTML scene for a storyboard beat.

    Embeds:
    - Design tokens as CSS variables
    - Unified component CSS
    - Semantic DOM elements for boxes, arrows, queues, timelines, memory grids
    - Deterministic JS seekTo(t) animation controller for frame-by-frame and real-time playback
    """
    tok = tokens or DEFAULT_DESIGN_TOKENS
    coords = _resolve_element_coords(beat.elements)

    elements_html: list[str] = []
    arrows_html: list[str] = []

    # Map accent name to CSS variable
    accent_var = (
        f"var(--{beat.live_accent.replace('_', '-')})"
        if beat.live_accent
        else "var(--accent-primary)"
    )

    for el in beat.elements:
        el_type = (el.type or "box").lower()
        init_hidden = el.initial_state != "visible"

        if el_type == "box":
            elements_html.append(
                render_box(
                    id=el.id,
                    label=el.label,
                    x=el.x,
                    y=el.y,
                    width=el.width or 280,
                    height=el.height or 140,
                    accent=accent_var,
                    initial_hidden=init_hidden,
                )
            )
        elif el_type == "arrow":
            # Determine start and end points
            if el.from_id and el.from_id in coords and el.to_id and el.to_id in coords:
                src = coords[el.from_id]
                dst = coords[el.to_id]
                if dst["cx"] > src["cx"] + src["w"] / 2:
                    x1 = src["x"] + src["w"]
                    y1 = src["cy"]
                    x2 = dst["x"]
                    y2 = dst["cy"]
                elif src["cx"] > dst["cx"] + dst["w"] / 2:
                    x1 = src["x"]
                    y1 = src["cy"]
                    x2 = dst["x"] + dst["w"]
                    y2 = dst["cy"]
                else:
                    x1 = src["cx"]
                    y1 = src["y"] + src["h"]
                    x2 = dst["cx"]
                    y2 = dst["y"]
            else:
                x1 = el.x
                y1 = el.y
                x2 = el.width or (el.x + 300)
                y2 = el.height or el.y

            arrows_html.append(
                render_arrow(
                    id=el.id,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    label=el.label,
                    accent=accent_var,
                    initial_hidden=init_hidden,
                )
            )
        elif el_type == "queue":
            elements_html.append(
                render_queue(
                    id=el.id,
                    x=el.x,
                    y=el.y,
                    items=el.items,
                    label=el.label or "Buffer Queue",
                    accent=accent_var,
                    initial_hidden=init_hidden,
                )
            )
        elif el_type == "timeline":
            elements_html.append(
                render_timeline(
                    id=el.id,
                    x=el.x,
                    y=el.y,
                    width=el.width or 1200,
                    steps=el.items,
                    label=el.label or "Execution Pipeline",
                    accent=accent_var,
                    initial_hidden=init_hidden,
                )
            )
        elif el_type in ("grid", "memory"):
            cells = [("0x00", item) for item in el.items] if el.items else None
            elements_html.append(
                render_memory_grid(
                    id=el.id,
                    x=el.x,
                    y=el.y,
                    cells=cells,
                    label=el.label or "Memory Layout",
                    accent=accent_var,
                    initial_hidden=init_hidden,
                )
            )
        elif el_type in ("state", "state_machine"):
            elements_html.append(
                render_state_machine(
                    id=el.id,
                    x=el.x,
                    y=el.y,
                    states=el.items or None,
                    label=el.label or "State Transition",
                    accent=accent_var,
                    initial_hidden=init_hidden,
                )
            )
        elif el_type == "label":
            hidden_cls = "hidden-initial" if init_hidden else ""
            label_style = (
                f"position: absolute; left: {el.x}px; top: {el.y}px; "
                f"width: {el.width or 400}px; z-index: 12;"
            )
            span_style = (
                f"color: {accent_var}; font-family: var(--code-font-family); "
                f"font-size: var(--font-size-label); font-weight: 600;"
            )
            elements_html.append(
                f'<div id="{escape(el.id)}" class="scene-label {hidden_cls}" '
                f'style="{label_style}">'
                f'<span class="label-text" style="{span_style}">{escape(el.label)}</span></div>'
            )

    actions_json_list: list[dict[str, Any]] = []
    for a in beat.actions:
        actions_json_list.append(
            {
                "action": a.action,
                "target_id": a.target_id,
                "start_time": a.start_time,
                "duration": a.duration,
                "params": a.params,
            }
        )
    actions_script = json.dumps(actions_json_list)
    total_duration = max(beat.duration_estimate, 1.0)
    caption_text = beat.narration_text[:140] + ("..." if len(beat.narration_text) > 140 else "")

    css_vars = tok.to_css_variables()
    comp_css = all_components_css()

    base_css = """
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      width: var(--scene-width);
      height: var(--scene-height);
      background-color: var(--bg-color);
      font-family: var(--font-family);
      color: var(--text-primary);
      overflow: hidden;
      position: relative;
      -webkit-font-smoothing: antialiased;
    }

    .scene-top-bar {
      position: absolute;
      top: 48px;
      left: 64px;
      right: 64px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 20;
    }

    .scene-meta {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .scene-badge {
      font-family: var(--code-font-family);
      font-size: 13px;
      font-weight: 700;
      background: var(--shape-neutral-1);
      border: 1px solid var(--border-color);
      border-radius: var(--corner-radius-sm);
      padding: 4px 10px;
      letter-spacing: 0.05em;
    }

    .scene-title {
      font-family: var(--font-family);
      font-size: 26px;
      font-weight: 600;
      color: var(--text-muted);
    }

    .scene-time-display {
      font-family: var(--code-font-family);
      font-size: 14px;
      color: var(--text-muted);
      opacity: 0.6;
    }

    .scene-caption-bar {
      position: absolute;
      bottom: 44px;
      left: 64px;
      right: 64px;
      display: flex;
      justify-content: center;
      z-index: 20;
      pointer-events: none;
    }

    .scene-caption-pill {
      background: rgba(27, 34, 48, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(51, 65, 85, 0.6);
      border-radius: 9999px;
      padding: 10px 28px;
      font-size: 18px;
      color: var(--text-muted);
      max-width: 1200px;
      text-align: center;
      line-height: 1.4;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }

    .scene-label {
      transition: opacity var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1),
                  transform var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1);
    }

    .scene-label.hidden-initial {
      opacity: 0;
      transform: translateY(10px);
    }

    .scene-label.visible {
      opacity: 1;
      transform: translateY(0);
    }
    """

    js_code = f"""
    const ACTIONS = {actions_script};
    const TOTAL_DURATION = {total_duration};

    window.seekTo = function(t) {{
      const td = document.getElementById('time-display');
      if (td) td.textContent = t.toFixed(1) + 's / ' + TOTAL_DURATION.toFixed(1) + 's';

      ACTIONS.forEach(act => {{
        const el = document.getElementById(act.target_id);
        if (!el) return;

        const isPastStart = t >= act.start_time;

        if (act.action === 'enter' || act.action === 'fade_in') {{
          if (isPastStart) {{
            el.classList.add('visible');
            el.classList.remove('hidden-initial');
          }} else {{
            el.classList.remove('visible');
            el.classList.add('hidden-initial');
          }}
        }} else if (act.action === 'draw') {{
          if (isPastStart) {{
            el.classList.add('drawn');
            el.classList.add('visible');
            el.classList.remove('hidden-initial');
          }} else {{
            el.classList.remove('drawn');
            el.classList.remove('visible');
            el.classList.add('hidden-initial');
          }}
        }} else if (act.action === 'highlight') {{
          if (isPastStart) {{
            el.classList.add('highlighted');
          }} else {{
            el.classList.remove('highlighted');
          }}
        }} else if (act.action === 'exit' || act.action === 'fade_out') {{
          if (isPastStart) {{
            el.style.opacity = '0';
          }} else {{
            el.style.opacity = '';
          }}
        }} else if (act.action === 'move') {{
          if (isPastStart && act.params) {{
            const dx = act.params.dx || 0;
            const dy = act.params.dy || 0;
            el.style.transform = 'translate(' + dx + 'px, ' + dy + 'px)';
          }} else {{
            el.style.transform = '';
          }}
        }}
      }});
    }};

    let startTime = null;
    function animLoop(timestamp) {{
      if (!startTime) startTime = timestamp;
      const elapsed = (timestamp - startTime) / 1000.0;
      window.seekTo(elapsed);
      if (elapsed < TOTAL_DURATION + 0.5) {{
        requestAnimationFrame(animLoop);
      }}
    }}

    window.startAnimation = function() {{
      startTime = null;
      requestAnimationFrame(animLoop);
    }};

    if (window.navigator.webdriver === undefined || !window.navigator.webdriver) {{
      window.addEventListener('DOMContentLoaded', () => {{
        setTimeout(window.startAnimation, 300);
      }});
    }}
    """

    arrows_block = "\n  ".join(arrows_html)
    elements_block = "\n  ".join(elements_html)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=1920, height=1080, initial-scale=1.0">
  <title>{escape(beat.title or beat.id)}</title>
  <style>
{css_vars}
{base_css}
{comp_css}
  </style>
</head>
<body>
  <div class="scene-top-bar">
    <div class="scene-meta">
      <span class="scene-badge" style="color: {accent_var};">SCENE {beat.index:02d}</span>
      <span class="scene-title">{escape(beat.title)}</span>
    </div>
    <div class="scene-time-display" id="time-display">0.0s / {total_duration:.1f}s</div>
  </div>

  <!-- Connection arrows -->
  {arrows_block}

  <!-- Diagram primitives -->
  {elements_block}

  <div class="scene-caption-bar">
    <div class="scene-caption-pill">
      {escape(caption_text)}
    </div>
  </div>

  <script>
{js_code}
  </script>
</body>
</html>
"""
    return html


def save_scene_html(
    beat: StoryboardBeat, output_path: Path, tokens: DesignTokens | None = None
) -> Path:
    """Render and write scene HTML file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = build_scene_html(beat, tokens)
    output_path.write_text(html, encoding="utf-8")
    return output_path
