"""Generate a YouTube thumbnail with Pillow (branded text overlay)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from core.logging_setup import get_logger
from modules.scenegen.tokens import TOKENS as DEFAULT_THEME

log = get_logger(__name__)


def _font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates += [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
        ]
    candidates += [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    cur = words[0]
    for w in words[1:]:
        trial = f"{cur} {w}"
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines[:3]


def generate_thumbnail(
    output_path: Path,
    *,
    title: str,
    width: int = 1280,
    height: int = 720,
    accent: tuple[int, int, int] | None = None,
    background: tuple[int, int, int] | None = None,
) -> Path:
    """
    Compose a high-contrast YouTube thumbnail:

    - dark brand background
    - diagonal accent panel
    - large title text (wrapped)
    - subtle frame
    """
    theme = DEFAULT_THEME
    bg = background or theme.background_rgb
    acc = accent or theme.accent_rgb
    title_color = theme.title_rgb

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Diagonal accent band
    band = [
        (int(width * 0.55), 0),
        (width, 0),
        (width, height),
        (int(width * 0.35), height),
    ]
    draw.polygon(band, fill=theme.surface_rgb)

    # Accent bar left
    draw.rectangle([0, 0, int(width * 0.02), height], fill=acc)

    # Top accent line
    draw.rectangle([0, 0, width, int(height * 0.02)], fill=acc)

    font = _font(max(42, int(height * 0.09)), bold=True)
    margin = int(width * 0.07)
    max_w = int(width * 0.55)
    lines = _wrap(draw, title.strip() or "Untitled", font, max_w)

    # Center text block vertically on left half
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])
    total_h = sum(line_heights) + 16 * (len(lines) - 1)
    y = (height - total_h) // 2
    for i, line in enumerate(lines):
        # soft shadow
        draw.text((margin + 3, y + 3), line, font=font, fill=(0, 0, 0))
        draw.text((margin, y), line, font=font, fill=title_color)
        y += line_heights[i] + 16

    # Bottom label
    small = _font(max(18, int(height * 0.035)), bold=False)
    draw.text(
        (margin, height - int(height * 0.1)),
        "WATCH NOW",
        font=small,
        fill=acc,
    )

    # Outer border
    draw.rectangle([0, 0, width - 1, height - 1], outline=theme.muted_rgb, width=2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Always write real JPEG for YouTube
    if output_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        output_path = output_path.with_suffix(".jpg")
    if output_path.suffix.lower() == ".png":
        img.save(output_path, format="PNG", optimize=True)
    else:
        img.save(output_path, format="JPEG", quality=92, optimize=True)

    log.info("Thumbnail written %s (%dx%d)", output_path.name, width, height)
    return output_path
