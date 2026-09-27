"""Upload Shorts clips via YouTube Data API v3."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.logging_setup import get_logger
from modules.publisher.youtube_upload import set_thumbnail, upload_video

log = get_logger(__name__)


def upload_short(
    youtube: Any,
    video_path: Path,
    *,
    title: str,
    description: str,
    tags: list[str] | None = None,
    privacy: str = "private",
    category_id: str = "27",
    thumbnail_path: Path | None = None,
) -> dict[str, Any]:
    """
    Upload a vertical short.

    YouTube treats Shorts primarily by aspect ratio + duration; include #Shorts
    in title or description when that matches your workflow.
    """
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    short_title = title if "#Shorts" in title or "#shorts" in title else f"{title} #Shorts"
    short_desc = description
    if "#Shorts" not in short_desc and "#shorts" not in short_desc:
        short_desc = (short_desc.rstrip() + "\n\n#Shorts\n").lstrip()

    video_id = upload_video(
        youtube,
        video_path=video_path,
        title=short_title[:100],
        description=short_desc,
        tags=list(tags or []),
        category_id=category_id,
        privacy=privacy,
    )
    if thumbnail_path and thumbnail_path.exists():
        try:
            set_thumbnail(youtube, video_id, thumbnail_path)
        except Exception as exc:  # noqa: BLE001
            log.warning("Short thumbnail failed: %s", exc)

    return {
        "youtube_video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "privacy": privacy,
        "title": short_title,
    }
