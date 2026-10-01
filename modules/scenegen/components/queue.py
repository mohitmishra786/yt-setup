"""Queue / buffer / pipeline visualization primitive."""

from __future__ import annotations

from html import escape


def render_queue(
    id: str,
    x: float,
    y: float,
    items: list[str],
    *,
    label: str = "Ready Queue",
    max_slots: int = 5,
    accent: str = "var(--accent-primary)",
    initial_hidden: bool = True,
) -> str:
    """
    Render a horizontal queue / channel buffer with discrete slots.
    """
    hidden_cls = "hidden-initial" if initial_hidden else ""
    slots_html: list[str] = []

    for i in range(max_slots):
        item_val = items[i] if i < len(items) else ""
        occupied = "occupied" if item_val else "empty"
        slot_content = (
            f'<span class="slot-text">{escape(item_val)}</span>'
            if item_val
            else '<span class="slot-empty">·</span>'
        )
        slots_html.append(
            f'<div class="queue-slot {occupied}" id="{escape(id)}-slot-{i}">{slot_content}</div>'
        )

    return f"""
<div id="{escape(id)}" class="cs-queue {hidden_cls}"
     style="left: {x}px; top: {y}px; --queue-accent: {accent};">
  <div class="queue-header">
    <span class="queue-title">{escape(label)}</span>
    <div class="queue-meta">
      <span class="queue-tag">FIFO BUFFER</span>
      <span class="queue-count">{len(items)} / {max_slots}</span>
    </div>
  </div>
  <div class="queue-body">
    <div class="queue-slots">
      {"".join(slots_html)}
    </div>
  </div>
  <div class="queue-pointers">
    <span class="pointer-head">▲ HEAD</span>
    <span class="pointer-tail">▲ TAIL</span>
  </div>
</div>
""".strip()


def queue_css() -> str:
    """CSS styles for cs-queue elements."""
    return """
.cs-queue {
  position: absolute;
  box-sizing: border-box;
  background-color: var(--shape-neutral-1);
  border: var(--stroke-width) solid var(--border-color);
  border-radius: var(--corner-radius);
  padding: 16px 20px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
  transition: transform var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1),
              opacity var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1),
              border-color 0.3s ease;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cs-queue.hidden-initial {
  opacity: 0;
  transform: translateY(18px) scale(0.96);
  pointer-events: none;
}

.cs-queue.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.cs-queue .queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--shape-neutral-2);
  padding-bottom: 8px;
}

.cs-queue .queue-title {
  font-family: var(--font-family);
  font-size: var(--font-size-label);
  font-weight: 600;
  color: var(--text-primary);
}

.cs-queue .queue-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cs-queue .queue-tag {
  font-family: var(--code-font-family);
  font-size: 11px;
  color: var(--queue-accent, var(--accent-primary));
  background-color: var(--shape-neutral-2);
  padding: 2px 6px;
  border-radius: var(--corner-radius-sm);
}

.cs-queue .queue-count {
  font-family: var(--code-font-family);
  font-size: 12px;
  color: var(--text-muted);
}

.cs-queue .queue-slots {
  display: flex;
  gap: 8px;
}

.cs-queue .queue-slot {
  width: 90px;
  height: 60px;
  background-color: var(--shape-neutral-2);
  border: 1px dashed var(--border-color);
  border-radius: var(--corner-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--code-font-family);
  font-size: 14px;
  color: var(--text-muted);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.cs-queue .queue-slot.occupied {
  background-color: rgba(56, 189, 248, 0.1);
  border: 2px solid var(--queue-accent, var(--accent-primary));
  color: var(--text-primary);
  font-weight: 600;
  transform: scale(1.02);
}

.cs-queue .queue-pointers {
  display: flex;
  justify-content: space-between;
  font-family: var(--code-font-family);
  font-size: 11px;
  color: var(--text-muted);
}
""".strip()
