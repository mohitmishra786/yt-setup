"""Stage 5 — assemble scene renders + narration audio into final.mp4 via FFmpeg."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from core.logging_setup import get_logger
from core.project import Project
from core.schemas import SlideOutline, Storyboard
from core.stages import StageResult

from modules.video_assembler.transitions import build_scene_concat_filter
from modules.voice.engine import probe_audio_duration

log = get_logger(__name__)


def _ffmpeg(configured: str = "ffmpeg") -> str:
    found = shutil.which(configured) or shutil.which("ffmpeg")
    if not found:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install FFmpeg: https://ffmpeg.org/download.html"
        )
    return found


def _probe_video_duration(path: Path) -> float:
    """Probe video duration via ffprobe or fall back to audio duration probe."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe and path.exists():
        cmd = [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            try:
                return float(proc.stdout.strip())
            except ValueError:
                pass
    return probe_audio_duration(path)


def _mux_scene_and_audio(
    ffmpeg: str,
    scene_video: Path,
    narration_audio: Path,
    out_clip: Path,
    *,
    fps: int,
    video_codec: str,
    audio_codec: str,
    crf: int,
    preset: str,
) -> float:
    """
    Mux scene animation with narration audio.

    If video is shorter than audio, pads (freezes) the final video frame to hold
    the completed diagram on screen while narration finishes.
    """
    audio_dur = max(0.5, probe_audio_duration(narration_audio))
    video_dur = max(0.5, _probe_video_duration(scene_video))

    out_clip.parent.mkdir(parents=True, exist_ok=True)

    if video_dur < audio_dur - 0.1:
        # Freeze last frame to cover remaining narration
        pad_seconds = audio_dur - video_dur
        log.info(
            "Holding last frame of %s for %.2fs to match narration (%.2fs)",
            scene_video.name,
            pad_seconds,
            audio_dur,
        )
        vf_filter = f"tpad=stop_mode=clone:stop_duration={pad_seconds:.3f},fps={fps},format=yuv420p"
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(scene_video),
            "-i",
            str(narration_audio),
            "-vf",
            vf_filter,
            "-c:v",
            video_codec,
            "-preset",
            preset,
            "-crf",
            str(crf),
            "-c:a",
            audio_codec,
            "-b:a",
            "192k",
            "-t",
            f"{audio_dur:.3f}",
            str(out_clip),
        ]
    else:
        # Direct mux trimmed to audio duration
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(scene_video),
            "-i",
            str(narration_audio),
            "-c:v",
            video_codec,
            "-preset",
            preset,
            "-crf",
            str(crf),
            "-c:a",
            audio_codec,
            "-b:a",
            "192k",
            "-t",
            f"{audio_dur:.3f}",
            str(out_clip),
        ]

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg mux failed for {scene_video.name}: {proc.stderr[-1000:]}")

    return audio_dur


def _concat_clips(
    ffmpeg: str,
    clips: list[Path],
    output: Path,
    durations: list[float],
    *,
    crossfade: float,
    fps: int,
    video_codec: str,
    audio_codec: str,
    crf: int,
    preset: str,
) -> None:
    """Concatenate prepared scene clips into the final video."""
    if not clips:
        raise ValueError("No scene clips to concatenate")

    output.parent.mkdir(parents=True, exist_ok=True)

    if crossfade <= 0 or len(clips) == 1:
        # Lossless fast demuxer concat
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as fh:
            for c in clips:
                p = str(c.resolve()).replace("'", r"'\''")
                fh.write(f"file '{p}'\n")
            list_path = fh.name

        try:
            cmd = [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-c",
                "copy",
                str(output),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                # Transcode fallback if stream headers vary
                cmd = [
                    ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    list_path,
                    "-c:v",
                    video_codec,
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    audio_codec,
                    "-crf",
                    str(crf),
                    "-preset",
                    preset,
                    str(output),
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if proc.returncode != 0:
                    raise RuntimeError(f"ffmpeg concat failed: {proc.stderr[-1000:]}")
        finally:
            Path(list_path).unlink(missing_ok=True)
        return

    # Filter complex transition concat
    filter_parts, cur_v, cur_a = build_scene_concat_filter(
        len(clips),
        durations,
        transition="crossfade",
        crossfade_duration=crossfade,
    )
    inputs = []
    for c in clips:
        inputs.extend(["-i", str(c)])

    cmd = [
        ffmpeg,
        "-y",
        *inputs,
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        cur_v,
        "-map",
        cur_a,
        "-c:v",
        video_codec,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        audio_codec,
        "-b:a",
        "192k",
        "-crf",
        str(crf),
        "-preset",
        preset,
        "-r",
        str(fps),
        str(output),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        log.warning(
            "Soft crossfade concat failed (%s); falling back to direct concat", proc.stderr[-500:]
        )
        _concat_clips(
            ffmpeg,
            clips,
            output,
            durations,
            crossfade=0.0,
            fps=fps,
            video_codec=video_codec,
            audio_codec=audio_codec,
            crf=crf,
            preset=preset,
        )


class VideoAssemblerStage:
    """Stage 5 — assemble scene renders + narration audio into final.mp4."""

    name = "video_assembler"

    def run(self, project: Project) -> StageResult:
        cfg = project.config
        scenes_dir = project.paths.root / "scenes"
        storyboard_path = project.paths.root / "storyboard.json"

        # Determine count of scenes
        if storyboard_path.exists():
            with storyboard_path.open(encoding="utf-8") as fh:
                sb_data = json.load(fh)
            storyboard = Storyboard.model_validate(sb_data)
            total_scenes = len(storyboard.beats)
        elif project.paths.outline.exists():
            with project.paths.outline.open(encoding="utf-8") as fh:
                out_data = json.load(fh)
            outline = SlideOutline.model_validate(out_data)
            total_scenes = len(outline.slides)
        else:
            raise FileNotFoundError("Missing storyboard.json or outline.json")

        if total_scenes < 1:
            raise ValueError("No scenes found to assemble")

        ffmpeg = _ffmpeg(cfg.video.ffmpeg_bin)
        clips_dir = project.paths.root / ".clips"
        if clips_dir.exists():
            shutil.rmtree(clips_dir)
        clips_dir.mkdir(parents=True)

        clips: list[Path] = []
        clip_durations: list[float] = []

        log.info("Muxing %d animated scenes with narration audio", total_scenes)

        for i in range(1, total_scenes + 1):
            scene_mp4 = scenes_dir / f"scene_{i:02d}.mp4"
            if not scene_mp4.exists():
                raise FileNotFoundError(
                    f"Missing scene render: {scene_mp4} — run scenegen stage first"
                )

            audio_mp3 = project.paths.audio_for_slide(i)
            if not audio_mp3.exists():
                raise FileNotFoundError(
                    f"Missing audio narration for scene {i}: {audio_mp3} — run voice stage first"
                )

            out_clip = clips_dir / f"clip_{i:02d}.mp4"
            dur = _mux_scene_and_audio(
                ffmpeg,
                scene_mp4,
                audio_mp3,
                out_clip,
                fps=cfg.project.fps,
                video_codec=cfg.video.video_codec,
                audio_codec=cfg.video.audio_codec,
                crf=cfg.video.crf,
                preset=cfg.video.preset,
            )
            clips.append(out_clip)
            clip_durations.append(dur)

        crossfade = float(cfg.video.crossfade_seconds)
        if clips:
            shortest = min(clip_durations)
            if crossfade * 2 >= shortest:
                crossfade = max(0.0, shortest / 3.0)

        log.info("Concatenating %d clips -> %s", len(clips), project.paths.final_video.name)
        _concat_clips(
            ffmpeg,
            clips,
            project.paths.final_video,
            clip_durations,
            crossfade=crossfade,
            fps=cfg.project.fps,
            video_codec=cfg.video.video_codec,
            audio_codec=cfg.video.audio_codec,
            crf=cfg.video.crf,
            preset=cfg.video.preset,
        )

        if not project.paths.final_video.exists():
            raise RuntimeError("final.mp4 was not created")

        # Optional background music bed
        music_cfg = project.config.music
        music_path_str = music_cfg.track_path or project.checkpoint.options.get("music_track")
        if music_cfg.enabled and music_path_str:
            music_path = Path(str(music_path_str))
            if not music_path.is_absolute():
                music_path = project.config.repo_root / music_path
            if music_path.exists():
                from modules.video_assembler.bgm import mix_background_music

                mixed = project.paths.root / "final_bgm.mp4"
                try:
                    mix_background_music(
                        project.paths.final_video,
                        music_path,
                        mixed,
                        ffmpeg_bin=cfg.video.ffmpeg_bin,
                        music_volume=music_cfg.music_volume,
                    )
                    mixed.replace(project.paths.final_video)
                    log.info("BGM mixed into final.mp4")
                except Exception as exc:  # noqa: BLE001
                    log.warning("BGM mix skipped: %s", exc)
            else:
                log.warning("Music track not found: %s", music_path)

        # Cleanup temp clips
        shutil.rmtree(clips_dir, ignore_errors=True)

        total_dur = sum(clip_durations)
        return StageResult(
            stage=self.name,
            artifacts=[project.rel(project.paths.final_video)],
            meta={
                "clip_count": len(clips),
                "duration_seconds": round(total_dur, 3),
                "crossfade": crossfade,
                "stub": False,
            },
            message=f"final.mp4 ({len(clips)} animated scenes, ~{total_dur:.1f}s)",
        )
