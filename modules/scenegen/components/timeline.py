"""Timeline / sequence diagram primitive for workflow execution."""

from __future__ import annotations

from html import escape


def render_timeline(
    id: str,
    x: float,
    y: float,
    width: float = 1200,
    steps: list[str] | None = None,
    *,
    label: str = "Execution Pipeline",
    active_step: int = 0,
    accent: str = "var(--accent-primary)",
    initial_hidden: bool = True,
) -> str:
    """
    Render a horizontal execution timeline with ordered steps and progress rail.
    """
    if steps is None:
        steps = ["Stage 1", "Stage 2", "Stage 3"]

    hidden_cls = "hidden-initial" if initial_hidden else ""
    steps_html: list[str] = []

    for i, step in enumerate(steps):
        state_cls = (
            "completed" if i < active_step else ("active" if i == active_step else "pending")
        )
        marker = "✓" if i < active_step else str(i + 1)
        steps_html.append(
            f"""
      <div class="timeline-step {state_cls}" id="{escape(id)}-step-{i}">
        <div class="step-node">{marker}</div>
        <div class="step-label">{escape(step)}</div>
      </div>
""".strip()
        )

    return f"""
<div id="{escape(id)}" class="cs-timeline {hidden_cls}"
     style="left: {x}px; top: {y}px; width: {width}px; --timeline-accent: {accent};">
  <div class="timeline-header">
    <span class="timeline-title">{escape(label)}</span>
    <span class="timeline-badge">STEP {min(active_step + 1, len(steps))} OF {len(steps)}</span>
  </div>
  <div class="timeline-track-wrapper">
    <div class="timeline-track"></div>
    <div class="timeline-steps">
      {"".join(steps_html)}
    </div>
  </div>
</div>
""".strip()


def timeline_css() -> str:
    """CSS styles for cs-timeline elements."""
    return """
.cs-timeline {
  position: absolute;
  box-sizing: border-box;
  background-color: var(--shape-neutral-1);
  border: var(--stroke-width) solid var(--border-color);
  border-radius: var(--corner-radius);
  padding: 24px 32px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
  transition: transform var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1),
              opacity var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 10;
}

.cs-timeline.hidden-initial {
  opacity: 0;
  transform: translateY(18px) scale(0.96);
}

.cs-timeline.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.cs-timeline .timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.cs-timeline .timeline-title {
  font-family: var(--font-family);
  font-size: var(--font-size-label);
  font-weight: 600;
  color: var(--text-primary);
}

.cs-timeline .timeline-badge {
  font-family: var(--code-font-family);
  font-size: 11px;
  color: var(--timeline-accent, var(--accent-primary));
  background-color: var(--shape-neutral-2);
  padding: 3px 8px;
  border-radius: var(--corner-radius-sm);
  letter-spacing: 0.05em;
}

.cs-timeline .timeline-track-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.cs-timeline .timeline-track {
  position: absolute;
  top: 20px;
  left: 40px;
  right: 40px;
  height: 4px;
  background-color: var(--shape-neutral-2);
  z-index: 1;
}

.cs-timeline .timeline-steps {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.cs-timeline .timeline-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  width: 140px;
}

.cs-timeline .step-node {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: var(--shape-neutral-1);
  border: 3px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--code-font-family);
  font-size: 14px;
  font-weight: 700;
  color: var(--text-muted);
  transition: all 0.3s ease;
}

.cs-timeline .timeline-step.active .step-node {
  border-color: var(--timeline-accent, var(--accent-primary));
  color: var(--text-primary);
  background-color: rgba(56, 189, 248, 0.15);
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.4);
  transform: scale(1.1);
}

.cs-timeline .timeline-step.completed .step-node {
  border-color: var(--accent-success);
  background-color: rgba(52, 211, 153, 0.15);
  color: var(--accent-success);
}

.cs-timeline .step-label {
  font-family: var(--font-family);
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.2;
}

.cs-timeline .timeline-step.active .step-label {
  color: var(--text-primary);
  font-weight: 600;
}
""".strip()
