"""Render slide frames to PNG via Pillow (LibreOffice-independent path)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from core.logging_setup import get_logger
from core.schemas import Slide, SlideOutline
from modules.slidebuilder.theme import DEFAULT_THEME, SlideTheme

log = get_logger(__name__)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/ArialBold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "C:\\Windows\\Fonts\\arialbd.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_slide_frame(
    slide: Slide,
    output_path: Path,
    *,
    outline_title: str,
    page: int,
    total: int,
    width: int = 1920,
    height: int = 1080,
    theme: SlideTheme | None = None,
) -> Path:
    theme = theme or DEFAULT_THEME
    img = Image.new("RGB", (width, height), theme.background_rgb)
    draw = ImageDraw.Draw(img)

    # Top accent bar
    bar_h = max(8, int(height * 0.016))
    draw.rectangle([0, 0, width, bar_h], fill=theme.accent_rgb)

    # Right accent strip
    strip_w = max(10, int(width * 0.012))
    draw.rectangle([width - strip_w, bar_h, width, height], fill=theme.accent_secondary_rgb)

    margin_x = int(width * 0.055)
    title_font = _load_font(int(height * 0.055), bold=True)
    body_font = _load_font(int(height * 0.032), bold=False)
    footer_font = _load_font(int(height * 0.018), bold=False)

    # Title
    title_top = int(height * 0.10)
    max_text_w = width - margin_x * 2 - strip_w
    title_lines = _wrap_text(draw, slide.title, title_font, max_text_w)
    y = title_top
    for line in title_lines[:3]:
        draw.text((margin_x, y), line, font=title_font, fill=theme.title_rgb)
        bbox = draw.textbbox((0, 0), line, font=title_font)
        y += (bbox[3] - bbox[1]) + 10

    # Bullets
    y = max(y + int(height * 0.04), int(height * 0.28))
    bullet_gap = int(height * 0.055)
    for bullet in slide.bullets[:6]:
        lines = _wrap_text(draw, f"  {bullet}", body_font, max_text_w)
        # Accent dot
        dot_r = 6
        draw.ellipse(
            [margin_x, y + 12, margin_x + dot_r * 2, y + 12 + dot_r * 2],
            fill=theme.accent_rgb,
        )
        tx = margin_x + 28
        for j, line in enumerate(lines[:3]):
            draw.text((tx if j else tx, y), line if j else line.lstrip(), font=body_font, fill=theme.body_rgb)
            bbox = draw.textbbox((0, 0), line, font=body_font)
            y += (bbox[3] - bbox[1]) + 6
        y += bullet_gap - 10
        if y > height - int(height * 0.12):
            break

    # Footer
    footer = f"{outline_title[:50]}  |  {page}/{total}"
    draw.text(
        (margin_x, height - int(height * 0.06)),
        footer,
        font=footer_font,
        fill=theme.muted_rgb,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG", optimize=True)
    return output_path


def render_outline_frames(
    outline: SlideOutline,
    frames_dir: Path,
    *,
    width: int = 1920,
    height: int = 1080,
) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    # Clear old frames
    for old in frames_dir.glob("slide_*.png"):
        old.unlink()

    paths: list[Path] = []
    total = len(outline.slides)
    for slide in outline.slides:
        out = frames_dir / f"slide_{slide.index:02d}.png"
        render_slide_frame(
            slide,
            out,
            outline_title=outline.title,
            page=slide.index,
            total=total,
            width=width,
            height=height,
        )
        paths.append(out)
        log.debug("frame %s", out.name)
    return paths
