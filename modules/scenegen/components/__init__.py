"""Reusable CS-diagram component library."""

from __future__ import annotations

from modules.scenegen.components.arrow import arrow_css, render_arrow
from modules.scenegen.components.box import box_css, render_box
from modules.scenegen.components.memory_grid import memory_grid_css, render_memory_grid
from modules.scenegen.components.queue import queue_css, render_queue
from modules.scenegen.components.state_transition import render_state_machine, state_transition_css
from modules.scenegen.components.timeline import render_timeline, timeline_css


def all_components_css() -> str:
    """Concatenate CSS rules for all diagram components."""
    return "\n\n".join(
        [
            box_css(),
            arrow_css(),
            queue_css(),
            timeline_css(),
            memory_grid_css(),
            state_transition_css(),
        ]
    )


__all__ = [
    "render_box",
    "box_css",
    "render_arrow",
    "arrow_css",
    "render_queue",
    "queue_css",
    "render_timeline",
    "timeline_css",
    "render_memory_grid",
    "memory_grid_css",
    "render_state_machine",
    "state_transition_css",
    "all_components_css",
]
