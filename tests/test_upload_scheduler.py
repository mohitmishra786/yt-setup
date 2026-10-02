"""`cli.py upload` engine: plan validation, publishAt conversion, link placeholders, resume."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from core.config import AppConfig, ProjectSettings
from core.project import Project
from modules.publisher import scheduler as sch

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def _clip(path: Path, w: int, h: int, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=10",
         "-t", str(seconds), "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )


@pytest.fixture()
def project(tmp_path: Path) -> Project:
    cfg = AppConfig(project=ProjectSettings(root=tmp_path / "projects"))
    cfg.repo_root = tmp_path
    cfg.channel.timezone = "Asia/Kolkata"
    cfg.publisher.contains_synthetic_media = True
    proj = Project.create(cfg, "Upload Test")
    _clip(proj.paths.root / "final.mp4", 320, 180, 2)
    _clip(proj.paths.root / "shorts" / "short_01.mp4", 180, 320, 2)
    (proj.paths.root / "poster.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    (proj.paths.root / "publish").mkdir(exist_ok=True)
    return proj


def _plan(proj: Project, **over: Any) -> Path:
    plan = {
        "playlist": "Deep Dives",
        "items": [
            {"key": "video", "file": "final.mp4", "publish_at": "2026-10-09 19:30",
             "title": "Pointers in C", "description": "Long one.", "tags": ["c", "pointers"],
             "thumbnail": "poster.jpg", "playlist": True},
            {"key": "short_01", "file": "shorts/short_01.mp4", "publish_at": "2026-10-10 19:30",
             "title": "Short one #shorts", "description": "Full video: {url:video}",
             "tags": ["c"]},
        ],
    }
    plan.update(over)
    path = proj.paths.root / "publish" / "upload.json"
    path.write_text(json.dumps(plan))
    return path


class _Req:
    def __init__(self, result: dict[str, Any], log: list[tuple[str, Any]], name: str,
                 body: Any) -> None:
        self.result, self.log, self.name, self.body = result, log, name, body

    def execute(self) -> dict[str, Any]:
        self.log.append((self.name, self.body))
        return self.result

    def next_chunk(self) -> tuple[None, dict[str, Any]]:
        return None, self.execute()


class FakeYT:
    """Just enough of the googleapiclient surface; records every call."""

    def __init__(self, fail_thumbnail: bool = False) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.n = 0
        self.fail_thumbnail = fail_thumbnail

    def _res(self, name: str) -> Any:
        fake = self

        class R:
            def insert(self, **kw: Any) -> _Req:
                if name == "videos":
                    fake.n += 1
                    return _Req({"id": f"VID{fake.n}"}, fake.calls, "videos.insert", kw["body"])
                return _Req({"id": f"{name}-new"}, fake.calls, f"{name}.insert", kw.get("body"))

            def set(self, **kw: Any) -> _Req:
                if fake.fail_thumbnail:
                    raise RuntimeError("thumbnail boom")
                return _Req({}, fake.calls, f"{name}.set", kw["videoId"])

            def list(self, **kw: Any) -> _Req:
                if name == "playlists":
                    items = [{"id": "PL1", "snippet": {"title": "Deep Dives"}}]
                    return _Req({"items": items}, fake.calls, "playlists.list", None)
                ids = kw["id"].split(",")
                items = [{"id": i, "status": {"privacyStatus": "private",
                                              "uploadStatus": "uploaded"}} for i in ids]
                return _Req({"items": items}, fake.calls, "videos.list", None)

        return R()

    def __getattr__(self, name: str) -> Any:
        return lambda: self._res(name)


def test_plan_converts_local_time_and_detects_short(project: Project) -> None:
    plan = sch.load_plan(project.config, project, _plan(project), now=NOW)
    video, short = plan.items
    assert sch.rfc3339(video.publish_at) == "2026-10-09T14:00:00Z"  # 19:30 IST
    assert (video.kind, short.kind) == ("video", "short")
    assert plan.synthetic is True and plan.language == "en"


def test_plan_rejects_bad_input(project: Project) -> None:
    bad = {"key": "x", "file": "final.mp4", "publish_at": "2026-10-03 10:00",
           "title": "a" * 101, "description": "see <FULL VIDEO LINK> {url:later}",
           "tags": ["t" * 501]}
    with pytest.raises(sch.PlanError) as err:
        sch.load_plan(project.config, project, _plan(project, items=[bad]), now=NOW)
    text = str(err.value)
    for needle in ("title must be", "contains < or >", "500 characters",
                   "earlier item", "in the past"):
        assert needle in text


def test_plan_requires_synthetic_decision(project: Project) -> None:
    project.config.publisher.contains_synthetic_media = None
    with pytest.raises(sch.PlanError, match="contains_synthetic_media"):
        sch.load_plan(project.config, project, _plan(project), now=NOW)
    plan = sch.load_plan(project.config, project,
                         _plan(project, contains_synthetic_media=False), now=NOW)
    assert plan.synthetic is False


def test_no_schedule_uploads_private_drafts(project: Project) -> None:
    plan = sch.load_plan(project.config, project, _plan(project), now=NOW, no_schedule=True)
    assert all(i.publish_at is None and i.privacy == "private" for i in plan.items)


def test_tags_length_counts_commas_and_quotes() -> None:
    assert sch.tags_length(["ab", "c d"]) == 2 + (3 + 2) + 1


def test_execute_uploads_links_and_resumes(project: Project) -> None:
    plan = sch.load_plan(project.config, project, _plan(project), now=NOW)
    state_path = project.paths.root / "publish" / "uploaded.json"
    yt = FakeYT(fail_thumbnail=True)
    state = sch.execute(yt, plan, state_path)

    inserts = [b for n, b in yt.calls if n == "videos.insert"]
    assert inserts[0]["status"] == {
        "privacyStatus": "private", "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True, "publishAt": "2026-10-09T14:00:00Z"}
    assert inserts[1]["snippet"]["description"] == "Full video: https://youtu.be/VID1"
    assert state["video"]["steps"]["thumbnail"].startswith("failed")
    assert state["video"]["steps"]["playlist"] is True
    assert json.loads(state_path.read_text())["short_01"]["video_id"] == "VID2"

    # re-run: no new uploads, only the failed thumbnail is retried
    yt2 = FakeYT()
    state = sch.execute(yt2, plan, state_path)
    assert [n for n, _ in yt2.calls] == ["thumbnails.set"]
    assert state["video"]["steps"]["thumbnail"] is True
    rows = sch.verify(yt2, state)
    assert {r["video_id"] for r in rows} == {"VID1", "VID2"}
