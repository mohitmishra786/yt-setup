"""Memory grid / cache layout diagram primitive."""

from __future__ import annotations

from html import escape


def render_memory_grid(
    id: str,
    x: float,
    y: float,
    cells: list[tuple[str, str]] | None = None,
    *,
    label: str = "Memory Layout",
    active_index: int | None = None,
    accent: str = "var(--accent-primary)",
    initial_hidden: bool = True,
) -> str:
    """
    Render a contiguous memory grid with addresses and byte/word values.
    `cells`: list of (address, value) pairs e.g. [("0x00", "0xFA3C"), ("0x08", "0x0012")]
    """
    if cells is None:
        cells = [
            ("0x00", "HEAD"),
            ("0x08", "NEXT"),
            ("0x10", "DATA"),
            ("0x18", "NULL"),
        ]

    hidden_cls = "hidden-initial" if initial_hidden else ""
    cells_html: list[str] = []

    for i, (addr, val) in enumerate(cells):
        is_active = "active" if i == active_index else ""
        cells_html.append(
            f"""
      <div class="mem-row {is_active}" id="{escape(id)}-cell-{i}">
        <span class="mem-addr">{escape(addr)}</span>
        <span class="mem-val">{escape(val)}</span>
      </div>
""".strip()
        )

    return f"""
<div id="{escape(id)}" class="cs-memory-grid {hidden_cls}"
     style="left: {x}px; top: {y}px; --mem-accent: {accent};">
  <div class="mem-header">
    <span class="mem-title">{escape(label)}</span>
    <span class="mem-tag">STACK / HEAP</span>
  </div>
  <div class="mem-cells">
    {"".join(cells_html)}
  </div>
</div>
""".strip()


def memory_grid_css() -> str:
    """CSS styles for cs-memory-grid elements."""
    return """
.cs-memory-grid {
  position: absolute;
  box-sizing: border-box;
  background-color: var(--shape-neutral-1);
  border: var(--stroke-width) solid var(--border-color);
  border-radius: var(--corner-radius);
  padding: 16px 20px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
  transition: transform var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1),
              opacity var(--transition-duration) cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 10;
  width: 320px;
}

.cs-memory-grid.hidden-initial {
  opacity: 0;
  transform: translateY(18px) scale(0.96);
}

.cs-memory-grid.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.cs-memory-grid .mem-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--shape-neutral-2);
  padding-bottom: 8px;
  margin-bottom: 12px;
}

.cs-memory-grid .mem-title {
  font-family: var(--font-family);
  font-size: var(--font-size-label);
  font-weight: 600;
  color: var(--text-primary);
}

.cs-memory-grid .mem-tag {
  font-family: var(--code-font-family);
  font-size: 11px;
  color: var(--mem-accent, var(--accent-primary));
  background-color: var(--shape-neutral-2);
  padding: 2px 6px;
  border-radius: var(--corner-radius-sm);
}

.cs-memory-grid .mem-cells {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cs-memory-grid .mem-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--shape-neutral-2);
  border: 1px solid var(--border-color);
  border-radius: var(--corner-radius-sm);
  padding: 8px 12px;
  font-family: var(--code-font-family);
  font-size: 14px;
  transition: all 0.3s ease;
}

.cs-memory-grid .mem-addr {
  color: var(--text-muted);
  font-size: 12px;
}

.cs-memory-grid .mem-val {
  color: var(--text-primary);
  font-weight: 600;
}

.cs-memory-grid .mem-row.active {
  border-color: var(--mem-accent, var(--accent-primary));
  background-color: rgba(56, 189, 248, 0.15);
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);
}
""".strip()
