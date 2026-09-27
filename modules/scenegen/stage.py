"""Stage 3 — Scenegen: Storyboard -> rendered animated scenes (scenes/scene_XX.mp4)."""

from __future__ import annotations

import json
import os
from typing import Any

from core.logging_setup import get_logger
from core.project import Project
from core.schemas import Storyboard
from core.stages import StageResult
from core.stub_utils import write_json

from modules.scenegen.builder import save_scene_html
from modules.scenegen.qa import validate_storyboard_qa
from modules.scenegen.renderer import render_scene
from modules.scenegen.tokens import TOKENS

log = get_logger(__name__)


class ScenegenStage:
    """Render animated HTML diagram scenes into per-beat MP4 clips."""

    name = "scenegen"

    def run(self, project: Project) -> StageResult:
        storyboard_file = project.paths.root / "storyboard.json"
        if not storyboard_file.exists():
            raise FileNotFoundError(
                f"Missing storyboard.json — run storyboard stage first: {storyboard_file}"
            )

        with storyboard_file.open(encoding="utf-8") as fh:
            data = json.load(fh)
        storyboard = Storyboard.model_validate(data)

        cfg = project.config
        scenes_dir = project.paths.root / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)

        # Check if audio durations already exist from voice stage
        audio_durations_file = project.paths.audio_dir / "durations.json"
        known_audio_durs: list[float] = []
        if audio_durations_file.exists():
            try:
                adata = json.loads(audio_durations_file.read_text(encoding="utf-8"))
                known_audio_durs = [float(x) for x in adata.get("durations") or []]
            except Exception:  # noqa: BLE001
                pass

        artifacts: list[str] = []
        manifest_scenes: list[dict[str, Any]] = []
        force = bool(project.checkpoint.options.get("force", False))

        for idx, beat in enumerate(storyboard.beats, start=1):
            scene_name = f"scene_{idx:02d}"
            html_path = scenes_dir / f"{scene_name}.html"
            mp4_path = scenes_dir / f"{scene_name}.mp4"

            # Generate HTML scene with design tokens
            save_scene_html(beat, html_path, TOKENS)
            artifacts.append(project.rel(html_path))

            # Duration: prefer matching existing audio duration if available,
            # else storyboard estimate
            if idx - 1 < len(known_audio_durs) and known_audio_durs[idx - 1] > 0.5:
                scene_dur = known_audio_durs[idx - 1]
            else:
                scene_dur = beat.duration_estimate

            # Render scene clip (resumable per-scene)
            rendered_clip = render_scene(
                html_path,
                mp4_path,
                scene_dur,
                force=force,
                fps=cfg.project.fps,
                width=cfg.project.video_width,
                height=cfg.project.video_height,
                ffmpeg_bin=cfg.video.ffmpeg_bin,
            )
            artifacts.append(project.rel(rendered_clip))

            still_png = mp4_path.with_suffix(".png")
            if still_png.exists():
                artifacts.append(project.rel(still_png))

            manifest_scenes.append(
                {
                    "id": beat.id,
                    "index": idx,
                    "title": beat.title,
                    "html": project.rel(html_path),
                    "mp4": project.rel(rendered_clip),
                    "duration": round(scene_dur, 2),
                }
            )

        # Automated Visual QA verification before marking complete
        strict_qa = os.getenv("YT_STUDIO_STRICT_QA") == "1"
        qa_results = validate_storyboard_qa(
            storyboard,
            scenes_dir=scenes_dir,
            tokens=TOKENS,
            raise_on_failure=strict_qa,
        )

        passed_count = sum(1 for r in qa_results if r.passed)
        qa_summary = {
            "total_scenes": len(qa_results),
            "passed_scenes": passed_count,
            "failed_scenes": len(qa_results) - passed_count,
            "results": [
                {
                    "scene_id": r.scene_id,
                    "passed": r.passed,
                    "violations": r.violations,
                    "metrics": r.metrics,
                }
                for r in qa_results
            ],
        }
        qa_report_path = scenes_dir / "qa_report.json"
        write_json(qa_report_path, qa_summary)
        artifacts.append(project.rel(qa_report_path))

        manifest_path = scenes_dir / "manifest.json"
        write_json(
            manifest_path, {"scenes": manifest_scenes, "qa_passed": passed_count == len(qa_results)}
        )
        artifacts.append(project.rel(manifest_path))

        return StageResult(
            stage=self.name,
            artifacts=artifacts,
            meta={
                "scene_count": len(manifest_scenes),
                "total_duration": round(sum(s["duration"] for s in manifest_scenes), 2),
                "qa_passed": passed_count == len(qa_results),
                "stub": os.getenv("YT_STUDIO_STUB_SCENES") == "1",
            },
            message=(
                f"{len(manifest_scenes)} scenes rendered & QA verified "
                f"({passed_count}/{len(qa_results)} passed)"
            ),
        )
