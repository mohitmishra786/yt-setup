"""Labeled box / node diagram primitive for CS concepts."""

from __future__ import annotations

from html import escape


def render_box(
    id: str,
    label: str,
    x: float,
    y: float,
    width: float = 280,
    height: float = 140,
    *,
    subtitle: str = "",
    tag: str = "",
    state: str = "idle",  # idle, active, success, warning, error
    accent: str = "var(--accent-primary)",
    initial_hidden: bool = True,
) -> str:
    """
    Render a minimalist CS diagram box with clean typography and subtle elevation.

    States:
    - idle: standard neutral shape
    - active: highlighted with accent border and subtle glow
    - success: emerald border
    - warning: amber border
    - error: crimson/secondary border
    """
    hidden_cls = "hidden-initial" if initial_hidden else ""
    state_cls = f"state-{state}"
    tag_html = f'<div class="box-tag">{escape(tag)}</div>' if tag else ""
    sub_html = f'<div class="box-subtitle">{escape(subtitle)}</div>' if subtitle else ""

    return f"""
<div id="{escape(id)}" class="cs-box {hidden_cls} {state_cls}"
     style="left: {x}px; top: {y}px; width: {width}px; height: {height}px; --box-accent: {accent};">
  {tag_html}
  <div class="box-content">
    <div class="box-label">{escape(label)}</div>
    {sub_html}
  </div>
</div>
""".strip()


def box_css() -> str:
    """CSS styles for cs-box elements."""
    return """
.cs-box {
  position: absolute;
  box-sizing: border-box;
  background-color: var(--shape-neutral-1);
  border: var(--stroke-width) solid var(--border-color);
  border-radius: var(--corner-radius);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 16px 20px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.4);
  transition: transform var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1),
              opacity var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1),
              border-color 0.3s ease, box-shadow 0.3s ease;
  z-index: 10;
}

.cs-box.hidden-initial {
  opacity: 0;
  transform: translateY(18px) scale(0.96);
  pointer-events: none;
}

.cs-box.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
  pointer-events: auto;
}

.cs-box .box-content {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.cs-box .box-label {
  font-family: var(--font-family);
  font-size: var(--font-size-label);
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}

.cs-box .box-subtitle {
  font-family: var(--font-family);
  font-size: var(--font-size-caption);
  color: var(--text-muted);
}

.cs-box .box-tag {
  position: absolute;
  top: -12px;
  right: 16px;
  font-family: var(--code-font-family);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  background-color: var(--shape-neutral-2);
  color: var(--box-accent, var(--accent-primary));
  border: 1px solid var(--box-accent, var(--accent-primary));
  border-radius: var(--corner-radius-sm);
  padding: 2px 8px;
}

.cs-box.state-active, .cs-box.highlighted {
  border-color: var(--box-accent, var(--accent-primary));
  box-shadow: 0 0 20px -2px rgba(56, 189, 248, 0.25), 0 10px 25px -5px rgba(0, 0, 0, 0.5);
}

.cs-box.state-success {
  border-color: var(--accent-success);
  box-shadow: 0 0 20px -2px rgba(52, 211, 153, 0.25);
}

.cs-box.state-warning {
  border-color: var(--accent-warning);
  box-shadow: 0 0 20px -2px rgba(251, 191, 36, 0.25);
}

.cs-box.state-error {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 20px -2px rgba(244, 63, 94, 0.25);
}
""".strip()
