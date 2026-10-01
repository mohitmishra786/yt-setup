"""Shared pydantic schemas for pipeline artifacts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Slide(BaseModel):
    index: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    bullets: list[str] = Field(default_factory=list, max_length=8)
    speaker_notes: str = Field(min_length=1)
    visual_hint: str = ""
    visual_beat: str = ""

    @field_validator("bullets")
    @classmethod
    def clean_bullets(cls, v: list[str]) -> list[str]:
        cleaned = [b.strip() for b in v if b and str(b).strip()]
        return cleaned[:8]

    @field_validator("title", "speaker_notes", "visual_hint", "visual_beat")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class VisualAction(BaseModel):
    """An individual animation step on a visual element."""

    action: str = Field(description="enter, exit, move, highlight, draw, update, fade_in, fade_out")
    target_id: str = Field(description="ID of the visual element to animate")
    start_time: float = Field(
        default=0.0, ge=0.0, description="Offset in seconds from start of beat"
    )
    duration: float = Field(default=0.5, ge=0.0, description="Duration in seconds of the animation")
    params: dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")


class VisualElement(BaseModel):
    """A diagram primitive on the canvas (box, arrow, queue, grid, timeline, etc.)."""

    id: str = Field(description="Unique ID of the element within this beat")
    type: str = Field(description="box, arrow, label, queue, grid, timeline, group, container")
    label: str = Field(default="", description="Text label or header")
    x: float = Field(default=0.0, description="X position (pixels or percentage)")
    y: float = Field(default=0.0, description="Y position (pixels or percentage)")
    width: float = Field(default=0.0, description="Element width")
    height: float = Field(default=0.0, description="Element height")
    style: dict[str, Any] = Field(default_factory=dict, description="Optional style overrides")
    from_id: str | None = Field(default=None, description="Source element ID for arrows/connectors")
    to_id: str | None = Field(default=None, description="Target element ID for arrows/connectors")
    items: list[str] = Field(
        default_factory=list, description="Ordered items for queue/stack/grid cells"
    )
    initial_state: str = Field(default="hidden", description="hidden or visible at beat start")


class StoryboardBeat(BaseModel):
    """One storyboard beat/scene corresponding to a narrative reveal and narration block."""

    id: str = Field(description="Unique beat ID (e.g. scene_01, beat_01)")
    index: int = Field(ge=1, description="1-based sequence index")
    title: str = Field(default="", description="Beat title / mental model concept")
    narration_text: str = Field(min_length=1, description="Spoken narration script (speaker notes)")
    duration_estimate: float = Field(
        default=10.0, ge=1.0, description="Estimated duration in seconds"
    )
    live_accent: str = Field(
        default="accent_primary", description="Which accent token is currently active"
    )
    visual_beat: str = Field(default="", description="What is visually happening on screen")
    elements: list[VisualElement] = Field(
        default_factory=list, description="Visual primitives in this scene"
    )
    actions: list[VisualAction] = Field(
        default_factory=list, description="Choreographed animations"
    )


class Storyboard(BaseModel):
    """Full video storyboard: ordered list of animated diagram beats."""

    title: str = Field(min_length=1, max_length=300)
    topic: str = ""
    target_duration_minutes: float = Field(default=10.0, ge=1.0, le=120.0)
    audience: str = "general technical audience"
    beats: list[StoryboardBeat] = Field(min_length=1, max_length=50)
    total_duration_estimate: float = 0.0
    stub: bool = Field(default=False, alias="_stub")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @model_validator(mode="after")
    def compute_totals_and_numbering(self) -> Storyboard:
        for i, beat in enumerate(self.beats, start=1):
            beat.index = i
            if not beat.id:
                beat.id = f"scene_{i:02d}"
        self.total_duration_estimate = round(sum(b.duration_estimate for b in self.beats), 2)
        return self


class ChapterSkeletonItem(BaseModel):
    title: str
    approx_minute: float = 0.0


class SlideOutline(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    target_duration_minutes: float = Field(default=10.0, ge=1.0, le=120.0)
    audience: str = "general audience"
    slides: list[Slide] = Field(min_length=3, max_length=40)
    chapter_skeleton: list[ChapterSkeletonItem] = Field(default_factory=list)
    # retained only for stub / debug markers; never required from LLM
    stub: bool = Field(default=False, alias="_stub")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @model_validator(mode="after")
    def renumber_slides(self) -> SlideOutline:
        for i, slide in enumerate(self.slides, start=1):
            slide.index = i
        if not self.chapter_skeleton:
            self.chapter_skeleton = [
                ChapterSkeletonItem(title=self.slides[0].title, approx_minute=0.0),
                ChapterSkeletonItem(
                    title=self.slides[len(self.slides) // 2].title,
                    approx_minute=max(1.0, self.target_duration_minutes * 0.4),
                ),
                ChapterSkeletonItem(
                    title=self.slides[-1].title,
                    approx_minute=max(2.0, self.target_duration_minutes * 0.85),
                ),
            ]
        return self


class SEOMetadata(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    category_hint: str = "Education"
    thumbnail_text: str = ""
    hook_line: str = ""
    stub: bool = Field(default=False, alias="_stub")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for t in v:
            key = t.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(t.strip())
        return out[:30]

    @field_validator("title")
    @classmethod
    def title_len(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 100:
            return v[:97] + "..."
        return v


class TranscriptWord(BaseModel):
    word: str
    start: float
    end: float


class TranscriptSegment(BaseModel):
    id: int = 0
    start: float
    end: float
    text: str
    words: list[TranscriptWord] = Field(default_factory=list)


class Transcript(BaseModel):
    language: str = "en"
    engine: str = "unknown"
    segments: list[TranscriptSegment] = Field(default_factory=list)
    duration: float | None = None
    stub: bool = Field(default=False, alias="_stub")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class ChapterMarker(BaseModel):
    start_seconds: float = Field(ge=0)
    title: str = Field(min_length=1, max_length=100)


class ChaptersDocument(BaseModel):
    chapters: list[ChapterMarker] = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_youtube_rules(self) -> ChaptersDocument:
        if not self.chapters:
            raise ValueError("at least one chapter required")
        # First must be 0:00
        self.chapters[0].start_seconds = 0.0
        # Sort and de-dupe times
        self.chapters.sort(key=lambda c: c.start_seconds)
        cleaned: list[ChapterMarker] = []
        last_t = -1.0
        for ch in self.chapters:
            if cleaned and ch.start_seconds <= last_t:
                continue
            cleaned.append(ch)
            last_t = ch.start_seconds
        if cleaned[0].start_seconds != 0.0:
            cleaned[0].start_seconds = 0.0
        self.chapters = cleaned
        return self

    def to_youtube_text(self) -> str:
        lines: list[str] = []
        for ch in self.chapters:
            total = int(ch.start_seconds)
            h, rem = divmod(total, 3600)
            m, s = divmod(rem, 60)
            ts = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
            lines.append(f"{ts} {ch.title.strip()}")
        return "\n".join(lines) + "\n"


def outline_from_dict(data: dict[str, Any]) -> SlideOutline:
    return SlideOutline.model_validate(data)


def storyboard_from_dict(data: dict[str, Any]) -> Storyboard:
    return Storyboard.model_validate(data)


def seo_from_dict(data: dict[str, Any]) -> SEOMetadata:
    return SEOMetadata.model_validate(data)
