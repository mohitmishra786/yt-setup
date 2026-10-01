"""Directional arrow / connector primitive with animated draw-in."""

from __future__ import annotations

import math
from html import escape


def render_arrow(
    id: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    label: str = "",
    accent: str = "var(--accent-primary)",
    curve: float = 0.0,
    stroke_width: float = 3,
    initial_hidden: bool = True,
) -> str:
    """
    Render a crisp SVG arrow from (x1, y1) to (x2, y2).

    If curve != 0, creates a quadratic bezier curve.
    Draw-in animation is supported via stroke-dashoffset transitions.
    """
    # Calculate path length for stroke-dasharray
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    total_len = max(100.0, dist * (1.15 if curve else 1.0))

    if curve != 0:
        # Midpoint with perpendicular offset
        mx = (x1 + x2) / 2 - dy * curve
        my = (y1 + y2) / 2 + dx * curve
        path_d = f"M {x1:.1f} {y1:.1f} Q {mx:.1f} {my:.1f} {x2:.1f} {y2:.1f}"
        lx, ly = mx, my
    else:
        path_d = f"M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}"
        lx, ly = (x1 + x2) / 2, (y1 + y2) / 2

    marker_id = f"arrowhead-{escape(id)}"
    label_html = ""
    if label:
        label_html = f"""
  <text x="{lx:.1f}" y="{ly - 12:.1f}" class="arrow-label" text-anchor="middle">
    {escape(label)}
  </text>
""".strip()

    hidden_cls = "hidden-initial" if initial_hidden else ""
    dash_offset = f"{total_len:.1f}" if initial_hidden else "0"

    return f"""
<svg id="{escape(id)}" class="cs-arrow {hidden_cls}"
     style="position: absolute; left: 0; top: 0; width: 100%; height: 100%;
            pointer-events: none; z-index: 5;"
     data-length="{total_len:.1f}">
  <defs>
    <marker id="{marker_id}" markerWidth="10" markerHeight="10" refX="7" refY="3.5" orient="auto">
      <polygon points="0 0, 8 3.5, 0 7" fill="{accent}" />
    </marker>
  </defs>
  <path class="arrow-path" d="{path_d}" fill="none" stroke="{accent}"
        stroke-width="{stroke_width}" stroke-linecap="round" marker-end="url(#{marker_id})"
        style="stroke-dasharray: {total_len:.1f}; stroke-dashoffset: {dash_offset};" />
  {label_html}
</svg>
""".strip()


def arrow_css() -> str:
    """CSS styles for cs-arrow elements."""
    return """
.cs-arrow {
  overflow: visible;
  transition: opacity 0.3s ease;
}

.cs-arrow.hidden-initial {
  opacity: 0;
}

.cs-arrow.visible {
  opacity: 1;
}

.cs-arrow .arrow-path {
  transition: stroke-dashoffset 0.6s cubic-bezier(0.16, 1, 0.3, 1),
              stroke 0.3s ease;
}

.cs-arrow.drawn .arrow-path {
  stroke-dashoffset: 0 !important;
}

.cs-arrow .arrow-label {
  font-family: var(--code-font-family);
  font-size: var(--font-size-caption);
  fill: var(--text-muted);
  font-weight: 500;
  letter-spacing: 0.04em;
  transition: opacity 0.4s ease 0.2s, fill 0.3s ease;
}

.cs-arrow.drawn .arrow-label {
  fill: var(--text-primary);
}
""".strip()
