"""Stage 8 — YouTube Data API v3 upload (private/draft by default)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from core.config import AppConfig
from core.logging_setup import get_logger
from core.project import Project
from core.stages import StageResult
from core.stub_utils import write_json

from modules.thumbnail.generate_thumbnail import generate_thumbnail

log = get_logger(__name__)

# upload: videos.insert + thumbnails.set; force-ssl: captions, playlists, comments, videos.list
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def _resolve(config: AppConfig, p: Path) -> Path:
    return p if p.is_absolute() else (config.repo_root / p).resolve()


def _resolve_path(project: Project, p: Path) -> Path:
    return _resolve(project.config, p)


def youtube_service(config: AppConfig, *, force_login: bool = False) -> Any:
    """OAuth desktop flow; caches the token under .credentials/ and refreshes it silently.

    Opens a browser only when there is no usable token (first run, revoked, or a token that
    predates a scope added to SCOPES) or when `force_login` is set.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token_path = _resolve(config, config.publisher.token_path)
    secrets = _resolve(config, config.publisher.client_secrets_path)
    if not secrets.exists():
        raise FileNotFoundError(
            f"YouTube OAuth client secrets not found: {secrets}. "
            "Create a Desktop OAuth client in Google Cloud Console and save JSON there."
        )

    creds: Credentials | None = None
    if token_path.exists() and not force_login:
        creds = Credentials.from_authorized_user_file(str(token_path))
        if not creds.has_scopes(SCOPES):
            log.info("Saved YouTube token lacks required scopes; logging in again")
            creds = None
    changed = False
    if creds and not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        changed = True
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
        # prompt=consent guarantees a refresh token even if this account consented before
        creds = flow.run_local_server(port=0, prompt="consent")
        changed = True
    if changed:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        token_path.chmod(0o600)

    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def get_youtube_service(project: Project) -> Any:
    return youtube_service(project.config)


def upload_video(
    youtube: Any,
    *,
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    category_id: str,
    privacy: str,
) -> str:
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": str(category_id),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log.info("Upload progress %.1f%%", status.progress() * 100)
    video_id = response["id"]
    log.info("Uploaded youtube video id=%s", video_id)
    return video_id


def set_thumbnail(youtube: Any, video_id: str, thumb_path: Path) -> None:
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(thumb_path))
    youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
    log.info("Thumbnail set for %s", video_id)


class PublisherStage:
    """Upload long-form video as private with title/description/tags/chapters."""

    name = "publisher"

    def run(self, project: Project) -> StageResult:
        if not project.paths.final_video.exists():
            raise FileNotFoundError(
                f"Missing final.mp4 — run video_assembler first: {project.paths.final_video}"
            )

        seo: dict = {}
        if project.paths.seo.exists():
            with project.paths.seo.open(encoding="utf-8") as fh:
                seo = json.load(fh)

        chapters = ""
        if project.paths.chapters.exists():
            chapters = project.paths.chapters.read_text(encoding="utf-8").strip()

        title = str(seo.get("title") or project.topic or project.project_id)
        description = str(seo.get("description") or "")
        if chapters:
            if "Chapters:" not in description:
                description = description.rstrip() + "\n\nChapters:\n" + chapters + "\n"
            elif "(generated in the chapters stage)" in description:
                description = description.replace(
                    "(generated in the chapters stage)", chapters
                )

        tags = list(seo.get("tags") or [])
        privacy = project.config.publisher.default_privacy
        # Allow override but never surprise-public without explicit option
        privacy = str(project.checkpoint.options.get("privacy") or privacy)
        if privacy == "public" and os.getenv("YT_STUDIO_ALLOW_PUBLIC") != "1":
            if not project.checkpoint.options.get("confirm_public"):
                log.warning(
                    "Refusing public upload without confirm_public option or "
                    "YT_STUDIO_ALLOW_PUBLIC=1; using private"
                )
                privacy = "private"

        thumb_text = str(seo.get("thumbnail_text") or title)
        generate_thumbnail(
            project.paths.thumbnail,
            title=thumb_text[: project.config.thumbnail.max_title_chars],
            width=project.config.thumbnail.width,
            height=project.config.thumbnail.height,
        )

        dry_run = (
            project.checkpoint.options.get("dry_run") is True
            or os.getenv("YT_STUDIO_PUBLISH_DRY_RUN") == "1"
            or os.getenv("YT_STUDIO_FORCE_STUB") == "1"
        )
        secrets = _resolve_path(project, project.config.publisher.client_secrets_path)
        if not secrets.exists():
            dry_run = True
            log.info("No YouTube client secrets at %s — dry-run manifest only", secrets)

        video_id: str | None = None
        status = "not_uploaded"
        error: str | None = None

        if not dry_run:
            try:
                youtube = get_youtube_service(project)
                video_id = upload_video(
                    youtube,
                    video_path=project.paths.final_video,
                    title=title,
                    description=description,
                    tags=tags,
                    category_id=project.config.publisher.category_id,
                    privacy=privacy,
                )
                if project.paths.thumbnail.exists():
                    try:
                        set_thumbnail(youtube, video_id, project.paths.thumbnail)
                    except Exception as exc:  # noqa: BLE001
                        log.warning("Thumbnail upload failed: %s", exc)
                status = "uploaded"
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"
                log.error("YouTube upload failed: %s", error)
                status = "failed"
                if not project.checkpoint.options.get("allow_publish_failure"):
                    raise

        manifest = {
            "privacy": privacy,
            "title": title,
            "description": description,
            "tags": tags,
            "category_id": project.config.publisher.category_id,
            "video_path": project.rel(project.paths.final_video),
            "thumbnail_path": project.rel(project.paths.thumbnail),
            "youtube_video_id": video_id,
            "status": status,
            "dry_run": dry_run,
            "error": error,
            "url": f"https://youtu.be/{video_id}" if video_id else None,
        }
        manifest_path = project.paths.root / "publish_manifest.json"
        write_json(manifest_path, manifest)

        return StageResult(
            stage=self.name,
            artifacts=[
                project.rel(manifest_path),
                project.rel(project.paths.thumbnail),
            ],
            meta={
                "privacy": privacy,
                "status": status,
                "youtube_video_id": video_id,
                "dry_run": dry_run,
                "stub": dry_run and status == "not_uploaded",
            },
            message=(
                f"uploaded {video_id} ({privacy})"
                if video_id
                else f"publish manifest ({status}, privacy={privacy})"
            ),
        )
