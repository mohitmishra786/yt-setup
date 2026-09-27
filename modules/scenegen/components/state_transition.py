"""State transition primitive: visual entity moving between discrete system states."""

from __future__ import annotations

from html import escape


def render_state_machine(
    id: str,
    x: float,
    y: float,
    states: list[str] | None = None,
    *,
    active_state_index: int = 0,
    label: str = "Lifecycle State Machine",
    accent: str = "var(--accent-primary)",
    initial_hidden: bool = True,
) -> str:
    """
    Render a horizontal state machine with connected states and an active token marker.
    """
    if states is None:
        states = ["READY", "RUNNING", "BLOCKED"]

    hidden_cls = "hidden-initial" if initial_hidden else ""
    states_html: list[str] = []

    for i, s in enumerate(states):
        is_active = "active" if i == active_state_index else ""
        token_html = '<div class="state-token"></div>' if i == active_state_index else ""
        states_html.append(
            f"""
      <div class="state-node {is_active}" id="{escape(id)}-state-{i}">
        <span class="state-name">{escape(s)}</span>
        {token_html}
      </div>
""".strip()
        )
        if i < len(states) - 1:
            states_html.append('<div class="state-connector">→</div>')

    current_name = states[min(active_state_index, len(states) - 1)]
    return f"""
<div id="{escape(id)}" class="cs-state-machine {hidden_cls}"
     style="left: {x}px; top: {y}px; --state-accent: {accent};">
  <div class="sm-header">
    <span class="sm-title">{escape(label)}</span>
    <span class="sm-current">CURRENT: {escape(current_name)}</span>
  </div>
  <div class="sm-track">
    {"".join(states_html)}
  </div>
</div>
""".strip()


def state_transition_css() -> str:
    """CSS styles for cs-state-machine elements."""
    return """
.cs-state-machine {
  position: absolute;
  box-sizing: border-box;
  background-color: var(--shape-neutral-1);
  border: var(--stroke-width) solid var(--border-color);
  border-radius: var(--corner-radius);
  padding: 20px 28px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
  transition: transform var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1),
              opacity var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 10;
}

.cs-state-machine.hidden-initial {
  opacity: 0;
  transform: translateY(18px) scale(0.96);
}

.cs-state-machine.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.cs-state-machine .sm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--shape-neutral-2);
  padding-bottom: 10px;
  margin-bottom: 20px;
}

.cs-state-machine .sm-title {
  font-family: var(--font-family);
  font-size: var(--font-size-label);
  font-weight: 600;
  color: var(--text-primary);
}

.cs-state-machine .sm-current {
  font-family: var(--code-font-family);
  font-size: 12px;
  color: var(--state-accent, var(--accent-primary));
  font-weight: 700;
}

.cs-state-machine .sm-track {
  display: flex;
  align-items: center;
  gap: 16px;
}

.cs-state-machine .state-node {
  position: relative;
  width: 140px;
  height: 70px;
  background-color: var(--shape-neutral-2);
  border: 2px solid var(--border-color);
  border-radius: var(--corner-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.cs-state-machine .state-name {
  font-family: var(--code-font-family);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
}

.cs-state-machine .state-node.active {
  border-color: var(--state-accent, var(--accent-primary));
  background-color: rgba(56, 189, 248, 0.12);
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.35);
  transform: scale(1.05);
}

.cs-state-machine .state-node.active .state-name {
  color: var(--text-primary);
}

.cs-state-machine .state-connector {
  font-family: var(--code-font-family);
  font-size: 20px;
  color: var(--border-color);
}
""".strip()
