"""Stage 2 — Slidebuilder: outline.json -> branded slides.pptx via python-pptx."""

from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from core.logging_setup import get_logger
from core.project import Project
from core.schemas import SlideOutline
from core.stages import StageResult
from modules.slidebuilder.theme import DEFAULT_THEME, SlideTheme

log = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _rgb(rgb: tuple[int, int, int]) -> RGBColor:
    return RGBColor(rgb[0], rgb[1], rgb[2])


def _set_run_font(run, *, name: str, size_pt: int, bold: bool, color: RGBColor) -> None:
    run.font.name = name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.color.rgb = color
    # Ensure East Asian / complex script fonts match
    rpr = run._r.get_or_add_rPr()
    for tag in ("latin", "ea", "cs"):
        el = rpr.find(qn(f"a:{tag}"))
        if el is None:
            el = rpr.makeelement(qn(f"a:{tag}"), {})
            rpr.append(el)
        el.set("typeface", name)


def _add_background(slide, theme: SlideTheme, prs: Presentation) -> None:
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Emu(0),
        Emu(0),
        prs.slide_width,
        prs.slide_height,
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(theme.background_rgb)
    shape.line.fill.background()


def _add_accent_bar(slide, theme: SlideTheme, prs: Presentation) -> None:
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Emu(0),
        Emu(0),
        prs.slide_width,
        Inches(theme.accent_bar_height_in),
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = _rgb(theme.accent_rgb)
    bar.line.fill.background()


def _add_footer(
    slide,
    theme: SlideTheme,
    prs: Presentation,
    *,
    deck_title: str,
    page: int,
    total: int,
) -> None:
    left = Inches(theme.margin_left_in)
    width = prs.slide_width - Inches(theme.margin_left_in + theme.margin_right_in)
    top = prs.slide_height - Inches(0.45)
    box = slide.shapes.add_textbox(left, top, width, Inches(0.35))
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = f"{deck_title[:60]}  |  {page}/{total}"
    _set_run_font(
        run,
        name=theme.font_body,
        size_pt=theme.footer_font_pt,
        bold=False,
        color=_rgb(theme.muted_rgb),
    )


def _set_speaker_notes(slide, notes: str) -> None:
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = notes.strip()


def _add_title_block(slide, theme: SlideTheme, title: str) -> None:
    left = Inches(theme.margin_left_in)
    top = Inches(theme.margin_top_in + 0.15)
    width = Inches(theme.width_in - theme.margin_left_in - theme.margin_right_in)
    box = slide.shapes.add_textbox(left, top, width, Inches(1.2))
    tf = box.text_frame
    tf.word_wrap = True
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = title
    _set_run_font(
        run,
        name=theme.font_title,
        size_pt=theme.title_font_pt,
        bold=True,
        color=_rgb(theme.title_rgb),
    )


def _add_bullets(slide, theme: SlideTheme, bullets: list[str]) -> None:
    if not bullets:
        return
    left = Inches(theme.margin_left_in)
    top = Inches(2.0)
    width = Inches(theme.width_in - theme.margin_left_in - theme.margin_right_in)
    height = Inches(4.5)
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.clear()

    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.level = 0
        p.space_after = Pt(14)
        # Accent bullet character for consistent cross-platform look
        run = p.add_run()
        run.text = f"  {bullet}"
        _set_run_font(
            run,
            name=theme.font_body,
            size_pt=theme.bullet_font_pt,
            bold=False,
            color=_rgb(theme.body_rgb),
        )


def _add_side_panel(slide, theme: SlideTheme, prs: Presentation) -> None:
    """Subtle right accent panel for visual depth."""
    panel_w = Inches(0.18)
    panel = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        prs.slide_width - panel_w,
        Inches(theme.accent_bar_height_in),
        panel_w,
        prs.slide_height - Inches(theme.accent_bar_height_in),
    )
    panel.fill.solid()
    panel.fill.fore_color.rgb = _rgb(theme.accent_secondary_rgb)
    panel.line.fill.background()


def build_presentation(
    outline: SlideOutline,
    output_path: Path,
    *,
    theme: SlideTheme | None = None,
    template_path: Path | None = None,
) -> Path:
    """
    Build a branded 16:9 PPTX from a validated outline.

    If template_path exists, use it as the base presentation (slide master branding).
    Otherwise construct a blank widescreen deck and apply theme drawing primitives.
    """
    theme = theme or DEFAULT_THEME
    if template_path and template_path.exists():
        prs = Presentation(str(template_path))
    else:
        prs = Presentation()
        prs.slide_width = Inches(theme.width_in)
        prs.slide_height = Inches(theme.height_in)

    # Use blank layout when available
    blank_idx = 6 if len(prs.slide_layouts) > 6 else len(prs.slide_layouts) - 1
    blank = prs.slide_layouts[blank_idx]

    total = len(outline.slides)
    for slide_data in outline.slides:
        slide = prs.slides.add_slide(blank)
        # Remove any residual placeholders
        for shape in list(slide.shapes):
            sp = shape._element
            sp.getparent().remove(sp)

        _add_background(slide, theme, prs)
        _add_accent_bar(slide, theme, prs)
        _add_side_panel(slide, theme, prs)
        _add_title_block(slide, theme, slide_data.title)
        _add_bullets(slide, theme, slide_data.bullets)
        _add_footer(
            slide,
            theme,
            prs,
            deck_title=outline.title,
            page=slide_data.index,
            total=total,
        )
        _set_speaker_notes(slide, slide_data.speaker_notes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    return output_path


def resolve_template(project: Project) -> Path | None:
    opt = project.checkpoint.options.get("template") or project.context.get("template")
    if opt:
        p = Path(str(opt))
        if not p.is_absolute():
            p = TEMPLATES_DIR / p
        if p.exists():
            return p
        log.warning("Template not found: %s", p)
    default = TEMPLATES_DIR / "default.pptx"
    return default if default.exists() else None


class SlidebuilderStage:
    """Render outline.json into slides.pptx using a branded theme/template."""

    name = "slidebuilder"

    def run(self, project: Project) -> StageResult:
        if not project.paths.outline.exists():
            raise FileNotFoundError(
                f"Missing outline.json — run scriptwriter first: {project.paths.outline}"
            )

        with project.paths.outline.open(encoding="utf-8") as fh:
            raw = json.load(fh)
        outline = SlideOutline.model_validate(raw)

        template = resolve_template(project)
        log.info(
            "Slidebuilder slides=%d template=%s",
            len(outline.slides),
            template.name if template else "built-in theme",
        )

        build_presentation(
            outline,
            project.paths.slides,
            template_path=template,
        )

        # Sanity: re-open and count slides
        prs = Presentation(str(project.paths.slides))
        n = len(prs.slides)
        if n != len(outline.slides):
            raise RuntimeError(
                f"PPTX slide count mismatch: expected {len(outline.slides)}, got {n}"
            )

        return StageResult(
            stage=self.name,
            artifacts=[project.rel(project.paths.slides)],
            meta={
                "slide_count": n,
                "template": template.name if template else None,
                "stub": False,
            },
            message=f"wrote slides.pptx ({n} slides)",
        )
