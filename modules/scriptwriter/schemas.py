"""Re-export outline/SEO schemas for the scriptwriter module."""

from core.schemas import (
    ChapterSkeletonItem,
    SEOMetadata,
    Slide,
    SlideOutline,
    outline_from_dict,
    seo_from_dict,
)

__all__ = [
    "ChapterSkeletonItem",
    "SEOMetadata",
    "Slide",
    "SlideOutline",
    "outline_from_dict",
    "seo_from_dict",
]
