"""Stage 4 — assemble slide frames + audio into final.mp4 via FFmpeg."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from core.logging_setup import get_logger
from core.project import Project
from core.schemas import SlideOutline
from core.stages import StageResult
from modules.video_assembler.frame_renderer import render_outline_frames
from modules.video_assembler.pptx_to_images import find_libreoffice, pptx_to_pngs
from modules.voice.engine import probe_audio_duration

log = get_logger(__name__)


def _ffmpeg(configured: str = "ffmpeg") -> str:
    found = shutil.which(configured) or shutil.which("ffmpeg")
    if not found:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install FFmpeg: https://ffmpeg.org/download.html"
        )
    return found


def _load_durations(project: Project, slide_count: int) -> list[float]:
    meta = project.paths.audio_dir / "durations.json"
    if meta.exists():
        data = json.loads(meta.read_text(encoding="utf-8"))
        durs = [float(x) for x in data.get("durations") or []]
        if len(durs) >= slide_count:
            return durs[:slide_count]
    durs = []
    for i in range(1, slide_count + 1):
        audio = project.paths.audio_for_slide(i)
        if audio.exists():
            durs.append(probe_audio_duration(audio))
        else:
            durs.append(3.0)
    return durs


def _export_frames(project: Project, outline: SlideOutline) -> list[Path]:
    """Prefer LibreOffice PPTX conversion; fall back to Pillow renderer."""
    cfg = project.config
    lo = find_libreoffice(cfg.video.libreoffice_bin)
    if lo and project.paths.slides.exists():
        try:
            tmp_dir = project.paths.root / ".lo_export"
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)
            tmp_dir.mkdir(parents=True)
            raw_frames = pptx_to_pngs(
                project.paths.slides,
                tmp_dir,
                libreoffice_bin=lo,
            )
            # Normalize names to slide_XX.png and scale to target resolution
            project.paths.frames_dir.mkdir(parents=True, exist_ok=True)
            for old in project.paths.frames_dir.glob("slide_*.png"):
                old.unlink()
            out_paths: list[Path] = []
            for i, src in enumerate(sorted(raw_frames), start=1):
                dest = project.paths.frame_for_slide(i)
                _scale_frame(
                    src,
                    dest,
                    cfg.project.video_width,
                    cfg.project.video_height,
                    ffmpeg_bin=cfg.video.ffmpeg_bin,
                )
                out_paths.append(dest)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            if out_paths:
                log.info("Frames via LibreOffice: %d", len(out_paths))
                return out_paths
        except Exception as exc:  # noqa: BLE001
            log.warning("LibreOffice frame export failed (%s); using Pillow", exc)

    log.info("Rendering frames via Pillow")
    return render_outline_frames(
        outline,
        project.paths.frames_dir,
        width=cfg.project.video_width,
        height=cfg.project.video_height,
    )


def _scale_frame(
    src: Path,
    dest: Path,
    width: int,
    height: int,
    *,
    ffmpeg_bin: str,
) -> None:
    ff = _ffmpeg(ffmpeg_bin)
    cmd = [
        ff,
        "-y",
        "-i",
        str(src),
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        # Pillow fallback copy/resize
        from PIL import Image

        img = Image.open(src).convert("RGB")
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, format="PNG")


def _make_slide_clip(
    ffmpeg: str,
    frame: Path,
    audio: Path,
    duration: float,
    out_clip: Path,
    *,
    fps: int,
    video_codec: str,
    audio_codec: str,
    crf: int,
    preset: str,
) -> None:
    """Create a single slide video clip: still image + audio for exact duration."""
    # -loop 1 -t duration -i image -i audio -shortest with explicit -t
    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-framerate",
        str(fps),
        "-t",
        f"{duration:.3f}",
        "-i",
        str(frame),
        "-i",
        str(audio),
        "-c:v",
        video_codec,
        "-tune",
        "stillimage",
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
        "-t",
        f"{duration:.3f}",
        "-shortest",
        str(out_clip),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg slide clip failed for {frame.name}: {proc.stderr[-2000:]}"
        )


def _concat_clips(
    ffmpeg: str,
    clips: list[Path],
    output: Path,
    *,
    crossfade: float,
    fps: int,
    video_codec: str,
    audio_codec: str,
    crf: int,
    preset: str,
) -> None:
    if not clips:
        raise ValueError("no clips to concat")

    if crossfade <= 0 or len(clips) == 1:
        # demuxer concat
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as fh:
            for c in clips:
                # Escape single quotes for concat demuxer
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
                # re-encode fallback
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
                    raise RuntimeError(f"ffmpeg concat failed: {proc.stderr[-2000:]}")
        finally:
            Path(list_path).unlink(missing_ok=True)
        return

    # xfade + acrossfade filter graph for soft transitions
    # Build complex filter; cap crossfade to half of shortest clip later in caller
    inputs: list[str] = []
    for c in clips:
        inputs.extend(["-i", str(c)])

    v_labels = [f"[{i}:v]" for i in range(len(clips))]
    a_labels = [f"[{i}:a]" for i in range(len(clips))]
    filter_parts: list[str] = []
    cur_v = v_labels[0]
    cur_a = a_labels[0]
    # Approximate offsets using equal segment assumption is wrong; use cumulative
    # Without probing each clip again, use progressive offset via xfade offset param
    # We re-probe durations:
    durs = [probe_audio_duration(c) for c in clips]
    offset = 0.0
    for i in range(1, len(clips)):
        offset += max(0.1, durs[i - 1] - crossfade)
        out_v = f"v{i}"
        out_a = f"a{i}"
        filter_parts.append(
            f"{cur_v}{v_labels[i]}xfade=transition=fade:duration={crossfade:.3f}:offset={offset:.3f}[{out_v}]"
        )
        filter_parts.append(
            f"{cur_a}{a_labels[i]}acrossfade=d={crossfade:.3f}[{out_a}]"
        )
        cur_v = f"[{out_v}]"
        cur_a = f"[{out_a}]"

    filter_complex = ";".join(filter_parts)
    cmd = [
        ffmpeg,
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
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
        log.warning("xfade concat failed (%s); hard-cut concat", proc.stderr[-500:])
        _concat_clips(
            ffmpeg,
            clips,
            output,
            crossfade=0.0,
            fps=fps,
            video_codec=video_codec,
            audio_codec=audio_codec,
            crf=crf,
            preset=preset,
        )


class VideoAssemblerStage:
    """LibreOffice/Pillow frames + FFmpeg image+audio per slide -> final.mp4."""

    name = "video_assembler"

    def run(self, project: Project) -> StageResult:
        if not project.paths.slides.exists():
            raise FileNotFoundError(
                f"Missing slides.pptx — run slidebuilder first: {project.paths.slides}"
            )
        if not project.paths.outline.exists():
            raise FileNotFoundError(f"Missing outline.json: {project.paths.outline}")

        with project.paths.outline.open(encoding="utf-8") as fh:
            outline = SlideOutline.model_validate(json.load(fh))

        cfg = project.config
        frames = _export_frames(project, outline)
        if len(frames) != len(outline.slides):
            log.warning(
                "frame count %d != slide count %d",
                len(frames),
                len(outline.slides),
            )

        durations = _load_durations(project, len(outline.slides))
        # Ensure audio exists for each slide
        for i, slide in enumerate(outline.slides, start=1):
            audio = project.paths.audio_for_slide(i)
            if not audio.exists():
                raise FileNotFoundError(
                    f"Missing audio for slide {i}: {audio} — run voice stage first"
                )

        ffmpeg = _ffmpeg(cfg.video.ffmpeg_bin)
        clips_dir = project.paths.root / ".clips"
        if clips_dir.exists():
            shutil.rmtree(clips_dir)
        clips_dir.mkdir(parents=True)

        clips: list[Path] = []
        artifacts: list[str] = [project.rel(f) for f in frames]

        min_dwell = 1.0
        crossfade = float(cfg.video.crossfade_seconds)
        # Cap crossfade so clips remain valid
        for i, slide in enumerate(outline.slides, start=1):
            frame = project.paths.frame_for_slide(i)
            if not frame.exists():
                # use available frames by order
                frame = frames[min(i - 1, len(frames) - 1)]
            audio = project.paths.audio_for_slide(i)
            dur = max(min_dwell, durations[i - 1] if i - 1 < len(durations) else 3.0)
            clip = clips_dir / f"clip_{i:02d}.mp4"
            log.info("Building clip %02d duration=%.2fs", i, dur)
            _make_slide_clip(
                ffmpeg,
                frame,
                audio,
                dur,
                clip,
                fps=cfg.project.fps,
                video_codec=cfg.video.video_codec,
                audio_codec=cfg.video.audio_codec,
                crf=cfg.video.crf,
                preset=cfg.video.preset,
            )
            clips.append(clip)

        # Adjust crossfade against shortest clip
        if clips:
            shortest = min(probe_audio_duration(c) for c in clips)
            if crossfade * 2 >= shortest:
                crossfade = max(0.0, shortest / 3.0)
                log.info("Adjusted crossfade to %.2fs", crossfade)

        log.info("Concatenating %d clips -> final.mp4", len(clips))
        _concat_clips(
            ffmpeg,
            clips,
            project.paths.final_video,
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

        # Cleanup intermediate clips to save disk (keep frames + audio)
        shutil.rmtree(clips_dir, ignore_errors=True)

        total = sum(durations)
        artifacts.append(project.rel(project.paths.final_video))
        return StageResult(
            stage=self.name,
            artifacts=artifacts,
            meta={
                "frame_count": len(frames),
                "clip_count": len(clips),
                "duration_seconds": round(total, 3),
                "crossfade": crossfade,
                "stub": False,
            },
            message=f"final.mp4 ({len(clips)} clips, ~{total:.1f}s)",
        )
