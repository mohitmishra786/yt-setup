"""Upload and schedule a project's videos and Shorts from `publish/upload.json`.

YouTube does the scheduling: each item is uploaded as private with `status.publishAt`, and
YouTube flips it public at that time, so nothing has to run at post time. Progress is recorded
in `publish/uploaded.json` after every API call, so a re-run resumes instead of re-uploading
(each upload spends quota from the separate 100/day video-upload bucket).

Plan format: skills/upload-video/references/plan-format.md.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core.config import AppConfig
from core.logging_setup import get_logger
from core.project import Project

log = get_logger(__name__)

PLACEHOLDER = re.compile(r"\{url:([A-Za-z0-9_\-]+)\}")
MIN_LEAD = timedelta(minutes=15)  # publishAt in the past publishes immediately: refuse that
SHORT_MAX_S = 180.0
STEPS = ("thumbnail", "captions", "playlist")


class PlanError(ValueError):
    pass


@dataclass
class Item:
    key: str
    file: Path
    title: str
    description: str
    tags: list[str]
    publish_at: datetime | None  # UTC
    privacy: str = "private"
    kind: str = "video"  # video | short (from the file's shape; YouTube decides the same way)
    thumbnail: Path | None = None
    captions: Path | None = None
    playlist: bool = False
    duration: float = 0.0
    width: int = 0
    height: int = 0


@dataclass
class Plan:
    items: list[Item]
    timezone: str
    synthetic: bool
    made_for_kids: bool
    category_id: str
    language: str
    playlist: str
    create_playlist: bool
    warnings: list[str] = field(default_factory=list)


def probe(path: Path) -> tuple[float, int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    st = (data.get("streams") or [{}])[0]
    return float(data["format"]["duration"]), int(st.get("width", 0)), int(st.get("height", 0))


def parse_when(value: str, tz: str) -> datetime:
    """'2026-10-09 19:30' (in `tz`) or an ISO time with an offset -> aware UTC datetime."""
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    return dt.astimezone(UTC)


def rfc3339(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def tags_length(tags: list[str]) -> int:
    """YouTube's 500-character tag budget: commas between tags count, and a tag with a space
    counts as if it were wrapped in quotes."""
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1)


def load_plan(
    config: AppConfig, project: Project, plan_path: Path, *, now: datetime | None = None,
    no_schedule: bool = False,
) -> Plan:
    raw = json.loads(plan_path.read_text(encoding="utf-8"))
    pub = config.publisher
    tz = str(raw.get("timezone") or config.channel.timezone)
    synthetic = raw.get("contains_synthetic_media", pub.contains_synthetic_media)
    if synthetic is None:
        raise PlanError(
            "contains_synthetic_media is not set. Ask the creator whether to disclose "
            "AI-altered/synthetic content (e.g. a cloned voice), then set it in upload.json "
            "or config.yaml publisher.contains_synthetic_media."
        )
    plan = Plan(
        items=[], timezone=tz, synthetic=bool(synthetic),
        made_for_kids=bool(raw.get("made_for_kids", pub.made_for_kids)),
        category_id=str(raw.get("category_id") or pub.category_id),
        language=str(raw.get("language") or pub.default_language),
        playlist=str(raw.get("playlist") or pub.playlist or ""),
        create_playlist=bool(raw.get("create_playlist", False)),
    )
    now = now or datetime.now(UTC)
    root = project.paths.root
    keys: list[str] = []
    errors: list[str] = []
    for n, entry in enumerate(raw.get("items") or [], start=1):
        key = str(entry.get("key") or f"item_{n}")
        where = f"item {key!r}"
        if key in keys:
            errors.append(f"{where}: duplicate key")
        keys.append(key)
        file = root / str(entry.get("file", ""))
        if not file.is_file():
            errors.append(f"{where}: file not found: {file}")
            continue
        title = str(entry.get("title") or "").strip()
        desc = str(entry.get("description") or "")
        tags = [str(t).strip() for t in entry.get("tags") or [] if str(t).strip()]
        if not title or len(title) > 100:
            errors.append(f"{where}: title must be 1-100 characters (has {len(title)})")
        if len(desc) > 5000:
            errors.append(f"{where}: description over 5000 characters ({len(desc)})")
        for label, text in (("title", title), ("description", desc)):
            if "<" in text or ">" in text:
                errors.append(f"{where}: {label} contains < or >, which YouTube rejects "
                              "(write unique_ptr, not unique_ptr<int>; fill <...> placeholders)")
        if tags_length(tags) > 500:
            errors.append(f"{where}: tags exceed 500 characters ({tags_length(tags)})")
        for ref in PLACEHOLDER.findall(desc):
            if ref not in keys[:-1]:
                errors.append(f"{where}: {{url:{ref}}} must name an earlier item's key")
        when = entry.get("publish_at")
        publish_at = None if no_schedule or not when else parse_when(str(when), tz)
        if publish_at is not None and publish_at < now + MIN_LEAD:
            errors.append(
                f"{where}: publish_at {when} is in the past or under 15 min away "
                "(YouTube would publish it immediately)"
            )
        privacy = "private" if publish_at else str(entry.get("privacy") or pub.default_privacy)
        if privacy not in ("private", "unlisted", "public"):
            errors.append(f"{where}: privacy must be private, unlisted or public")
        dur, w, h = probe(file)
        is_short = h >= w and dur <= SHORT_MAX_S
        kind = "short" if is_short else "video"
        if entry.get("kind") == "short" and not is_short:
            errors.append(
                f"{where}: marked short but is {w}x{h}, {dur:.0f}s "
                "(YouTube needs vertical/square and <= 3 min)"
            )
        if entry.get("kind") == "video" and is_short:
            plan.warnings.append(
                f"{where}: vertical and <= 3 min, so YouTube will treat it as a Short")
        thumb = root / str(entry["thumbnail"]) if entry.get("thumbnail") else None
        caps = root / str(entry["captions"]) if entry.get("captions") else None
        for label, p in (("thumbnail", thumb), ("captions", caps)):
            if p is not None and not p.is_file():
                errors.append(f"{where}: {label} not found: {p}")
        if thumb is not None and thumb.is_file() and thumb.stat().st_size > 2 * 1024 * 1024:
            errors.append(f"{where}: thumbnail over the API's 2 MB limit")
        if kind == "short" and thumb is not None:
            plan.warnings.append(
                f"{where}: Shorts thumbnails via the API show only on some surfaces")
        plan.items.append(Item(
            key=key, file=file, title=title, description=desc, tags=tags,
            publish_at=publish_at, privacy=privacy, kind=kind, thumbnail=thumb, captions=caps,
            playlist=bool(entry.get("playlist", False)) and bool(plan.playlist),
            duration=dur, width=w, height=h,
        ))
    if not raw.get("items"):
        errors.append("plan has no items")
    if errors:
        raise PlanError("\n".join(errors))
    return plan


# ---- state ----------------------------------------------------------------------------------

def load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    return {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def resolve_description(desc: str, state: dict[str, Any]) -> str:
    def url(m: re.Match[str]) -> str:
        entry = state.get(m.group(1)) or {}
        if not entry.get("video_id"):
            raise PlanError(f"{{url:{m.group(1)}}}: that item has not been uploaded yet")
        return f"https://youtu.be/{entry['video_id']}"

    return PLACEHOLDER.sub(url, desc)


# ---- API calls ------------------------------------------------------------------------------

def _media(path: Path, mimetype: str | None = None, resumable: bool = False) -> Any:
    from googleapiclient.http import MediaFileUpload

    if resumable:
        return MediaFileUpload(str(path), chunksize=8 * 1024 * 1024, resumable=True,
                               mimetype=mimetype)
    return MediaFileUpload(str(path), mimetype=mimetype)


def insert_video(yt: Any, plan: Plan, item: Item, description: str) -> str:
    status: dict[str, Any] = {
        "privacyStatus": item.privacy,
        "selfDeclaredMadeForKids": plan.made_for_kids,
        "containsSyntheticMedia": plan.synthetic,
    }
    if item.publish_at is not None:
        status["publishAt"] = rfc3339(item.publish_at)
    body = {
        "snippet": {
            "title": item.title,
            "description": description,
            "tags": item.tags,
            "categoryId": plan.category_id,
            "defaultLanguage": plan.language,
            "defaultAudioLanguage": plan.language,
        },
        "status": status,
    }
    request = yt.videos().insert(
        part="snippet,status", body=body,
        media_body=_media(item.file, "video/*", resumable=True),
    )
    response = None
    while response is None:
        progress, response = request.next_chunk()
        if progress:
            log.info("%s: upload %.0f%%", item.key, progress.progress() * 100)
    return str(response["id"])


def find_playlist(yt: Any, title: str, create: bool) -> str | None:
    token = None
    while True:
        resp = yt.playlists().list(part="snippet", mine=True, maxResults=50,
                                   pageToken=token).execute()
        for pl in resp.get("items") or []:
            if pl["snippet"]["title"].strip().lower() == title.strip().lower():
                return str(pl["id"])
        token = resp.get("nextPageToken")
        if not token:
            break
    if not create:
        return None
    pl = yt.playlists().insert(
        part="snippet,status",
        body={"snippet": {"title": title}, "status": {"privacyStatus": "public"}},
    ).execute()
    return str(pl["id"])


def run_step(yt: Any, plan: Plan, item: Item, step: str, video_id: str,
             playlist_id: str | None) -> bool:
    if step == "thumbnail" and item.thumbnail:
        yt.thumbnails().set(videoId=video_id, media_body=_media(item.thumbnail)).execute()
        return True
    if step == "captions" and item.captions:
        yt.captions().insert(
            part="snippet",
            body={"snippet": {"videoId": video_id, "language": plan.language,
                              "name": "", "isDraft": False}},
            media_body=_media(item.captions, "application/octet-stream"),
        ).execute()
        return True
    if step == "playlist" and item.playlist and playlist_id:
        yt.playlistItems().insert(
            part="snippet",
            body={"snippet": {"playlistId": playlist_id,
                              "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
        ).execute()
        return True
    return False


def wanted(item: Item, step: str) -> bool:
    return {"thumbnail": item.thumbnail is not None, "captions": item.captions is not None,
            "playlist": item.playlist}[step]


def execute(
    yt: Any, plan: Plan, state_path: Path, *, only: set[str] | None = None
) -> dict[str, Any]:
    """Upload every pending item, then its pending side steps. Safe to re-run."""
    state = load_state(state_path)
    playlist_id: str | None = state.get("_playlist_id")
    if plan.playlist and any(i.playlist for i in plan.items) and not playlist_id:
        playlist_id = find_playlist(yt, plan.playlist, plan.create_playlist)
        if playlist_id is None:
            log.warning("Playlist %r not found (set create_playlist: true to create it)",
                        plan.playlist)
        else:
            state["_playlist_id"] = playlist_id
            save_state(state_path, state)
    for item in plan.items:
        if only and item.key not in only:
            continue
        entry = state.setdefault(item.key, {})
        if not entry.get("video_id"):
            description = resolve_description(item.description, state)
            video_id = insert_video(yt, plan, item, description)
            entry.update({
                "video_id": video_id, "url": f"https://youtu.be/{video_id}",
                "file": item.file.name, "kind": item.kind, "title": item.title,
                "privacy": item.privacy,
                "publish_at": rfc3339(item.publish_at) if item.publish_at else None,
                "uploaded_at": rfc3339(datetime.now(UTC)), "steps": {},
            })
            save_state(state_path, state)  # record the id before anything else can fail
            log.info("%s: uploaded %s", item.key, video_id)
        steps = entry.setdefault("steps", {})
        for step in STEPS:
            if steps.get(step) is True or not wanted(item, step):
                continue
            try:
                steps[step] = run_step(yt, plan, item, step, entry["video_id"], playlist_id)
            except Exception as exc:  # noqa: BLE001 — a side step must not lose the upload
                steps[step] = f"failed: {type(exc).__name__}: {exc}"[:300]
                log.warning("%s: %s failed: %s", item.key, step, exc)
            save_state(state_path, state)
    return state


def verify(yt: Any, state: dict[str, Any]) -> list[dict[str, Any]]:
    ids = [v["video_id"] for k, v in state.items() if not k.startswith("_") and v.get("video_id")]
    rows: list[dict[str, Any]] = []
    for i in range(0, len(ids), 50):
        resp = yt.videos().list(part="status,processingDetails",
                                id=",".join(ids[i:i + 50])).execute()
        for v in resp.get("items") or []:
            st = v.get("status") or {}
            rows.append({
                "video_id": v["id"],
                "privacy": st.get("privacyStatus"),
                "publish_at": st.get("publishAt"),
                "upload": st.get("uploadStatus"),
                "problem": st.get("rejectionReason") or st.get("failureReason")
                or (v.get("processingDetails") or {}).get("processingFailureReason"),
            })
    found = {r["video_id"] for r in rows}
    rows += [{"video_id": i, "privacy": None, "publish_at": None, "upload": "missing",
              "problem": "not returned (deleted, or not visible to this login)"}
             for i in ids if i not in found]
    return rows
