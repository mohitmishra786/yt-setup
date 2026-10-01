"""Design tokens for minimalist CoreDumpped / 3Blue1Brown-style diagram scenes.

Single source of truth for:
- Canvas background
- Neutral shape fills and borders
- Accent tracking colors
- Typography and sizing
- Stroke width, corner radius, arrow geometry
- Pacing rules (hold duration after reveals, per-word reading pace)

Every scene MUST import and obey these tokens. No scene may hardcode a color or font.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DesignTokens:
    """Design token specification for all animated visual scenes."""

    # Canvas dimensions & frame rate
    width: int = 1920
    height: int = 1080
    fps: int = 30
    width_in: float = 13.333
    height_in: float = 7.5

    # Vertical format (Shorts / Reels)
    shorts_width: int = 1080
    shorts_height: int = 1920

    # Color Palette: deep, restrained, high-contrast matte slate
    bg_color: str = "#0f141c"  # Deep matte slate (canvas background)
    shape_neutral_1: str = "#1b2230"  # Box / card fill (subtle elevation)
    shape_neutral_2: str = "#273248"  # Border / secondary fill / divider
    border_color: str = "#334155"  # Crisp structural outline

    # Text colors
    text_primary: str = "#f8fafc"  # High-contrast title and active labels
    text_muted: str = "#94a3b8"  # Secondary notes, addresses, indices
    text_accent: str = "#38bdf8"  # Spoken/focused text highlight

    # Accent colors (used sparingly for 'the thing we are tracking right now')
    accent_primary: str = "#38bdf8"  # Electric cyan (active pointer, live state)
    accent_secondary: str = "#f43f5e"  # Rose / crimson (alert, eviction, error)
    accent_success: str = "#34d399"  # Emerald green (committed, match, success)
    accent_warning: str = "#fbbf24"  # Amber (pending, lock, waiting)
    accent_purple: str = "#a855f7"  # Violet (memory segment, transform)

    # Typography
    font_family: str = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    code_font_family: str = "'JetBrains Mono', 'Fira Code', Menlo, Monaco, 'Courier New', monospace"
    font_size_title: int = 48  # Main scene title
    font_size_subtitle: int = 32  # Section or group header
    font_size_body: int = 24  # Explanatory caption or note
    font_size_label: int = 20  # Box / node label
    font_size_code: int = 22  # Code / hex / register text
    font_size_caption: int = 16  # Small indices / byte offsets

    # Geometry & Styling
    stroke_width: int = 3  # Standard line / arrow / box border thickness
    stroke_width_thick: int = 4  # Highlighted path / active border
    corner_radius: int = 12  # Rounded rect radius
    corner_radius_sm: int = 6  # Small tag / badge radius

    # Arrow & Connector styling
    arrow_head_size: int = 10  # SVG marker size
    arrow_stroke_width: int = 3  # Connection line thickness

    # Core Pacing & Perception Laws
    default_hold_per_reveal: float = (
        2.0  # Minimum seconds to pause camera/scene after an element reveals
    )
    per_word_reading_pace: float = 0.30  # Seconds per word for any on-screen text reading
    transition_duration: float = 0.45  # Standard enter/exit animation duration

    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    @property
    def background_rgb(self) -> tuple[int, int, int]:
        return self.hex_to_rgb(self.bg_color)

    @property
    def surface_rgb(self) -> tuple[int, int, int]:
        return self.hex_to_rgb(self.shape_neutral_1)

    @property
    def accent_rgb(self) -> tuple[int, int, int]:
        return self.hex_to_rgb(self.accent_primary)

    @property
    def title_rgb(self) -> tuple[int, int, int]:
        return self.hex_to_rgb(self.text_primary)

    @property
    def body_rgb(self) -> tuple[int, int, int]:
        return self.hex_to_rgb(self.text_primary)

    @property
    def muted_rgb(self) -> tuple[int, int, int]:
        return self.hex_to_rgb(self.text_muted)

    def to_dict(self) -> dict[str, Any]:
        """Export tokens as dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Export tokens as formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_css_variables(self) -> str:
        """Generate CSS custom properties for direct inclusion in HTML/SVG scenes."""
        return f"""
:root {{
  --scene-width: {self.width}px;
  --scene-height: {self.height}px;
  --scene-fps: {self.fps};

  /* Colors */
  --bg-color: {self.bg_color};
  --shape-neutral-1: {self.shape_neutral_1};
  --shape-neutral-2: {self.shape_neutral_2};
  --border-color: {self.border_color};
  --text-primary: {self.text_primary};
  --text-muted: {self.text_muted};
  --text-accent: {self.text_accent};

  --accent-primary: {self.accent_primary};
  --accent-secondary: {self.accent_secondary};
  --accent-success: {self.accent_success};
  --accent-warning: {self.accent_warning};
  --accent-purple: {self.accent_purple};

  /* Typography */
  --font-family: {self.font_family};
  --code-font-family: {self.code_font_family};
  --font-size-title: {self.font_size_title}px;
  --font-size-subtitle: {self.font_size_subtitle}px;
  --font-size-body: {self.font_size_body}px;
  --font-size-label: {self.font_size_label}px;
  --font-size-code: {self.font_size_code}px;
  --font-size-caption: {self.font_size_caption}px;

  /* Geometry */
  --stroke-width: {self.stroke_width}px;
  --stroke-width-thick: {self.stroke_width_thick}px;
  --corner-radius: {self.corner_radius}px;
  --corner-radius-sm: {self.corner_radius_sm}px;
  --arrow-head-size: {self.arrow_head_size}px;

  /* Animation timing */
  --transition-duration: {self.transition_duration}s;
  --default-hold: {self.default_hold_per_reveal}s;
}}
""".strip()

    def estimate_reading_duration(self, text: str) -> float:
        """Calculate minimum readable hold duration based on word count."""
        words = len(text.split())
        return max(self.default_hold_per_reveal, words * self.per_word_reading_pace + 1.0)


# Canonical singleton used everywhere
DEFAULT_DESIGN_TOKENS = DesignTokens()
TOKENS = DEFAULT_DESIGN_TOKENS


def save_tokens_json(path: Path | str) -> Path:
    """Write tokens.json to disk."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(DEFAULT_DESIGN_TOKENS.to_json() + "\n", encoding="utf-8")
    return p
