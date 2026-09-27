"""Slide theme tokens for branded PPTX output."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlideTheme:
    """RGB colors and layout metrics (EMU-friendly inches)."""

    # Brand palette (deep navy / electric accent / clean white)
    background_rgb: tuple[int, int, int] = (15, 23, 42)  # slate-900
    surface_rgb: tuple[int, int, int] = (30, 41, 59)  # slate-800
    accent_rgb: tuple[int, int, int] = (56, 189, 248)  # sky-400
    accent_secondary_rgb: tuple[int, int, int] = (167, 139, 250)  # violet-400
    title_rgb: tuple[int, int, int] = (248, 250, 252)  # slate-50
    body_rgb: tuple[int, int, int] = (226, 232, 240)  # slate-200
    muted_rgb: tuple[int, int, int] = (148, 163, 184)  # slate-400

    font_title: str = "Calibri"
    font_body: str = "Calibri"

    # 16:9 widescreen
    width_in: float = 13.333
    height_in: float = 7.5

    margin_left_in: float = 0.7
    margin_right_in: float = 0.7
    margin_top_in: float = 0.55
    accent_bar_height_in: float = 0.12
    title_font_pt: int = 36
    bullet_font_pt: int = 22
    footer_font_pt: int = 12


DEFAULT_THEME = SlideTheme()
