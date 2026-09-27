"""Stage 5 — transcription via faster-whisper (default) or WhisperX when available."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from core.logging_setup import get_logger
from core.project import Project
from core.schemas import Transcript, TranscriptSegment, TranscriptWord
from core.stages import StageResult
from core.stub_utils import write_json, write_text
from modules.transcriber.export_srt_vtt import segments_to_srt, segments_to_vtt

log = get_logger(__name__)


def extract_audio(video_path: Path, wav_path: Path, *, ffmpeg_bin: str = "ffmpeg") -> Path:
    ff = shutil.which(ffmpeg_bin) or shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("ffmpeg required to extract audio for transcription")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ff,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(wav_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"audio extract failed: {proc.stderr[-1500:]}")
    return wav_path


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            # faster-whisper typically wants cpu/cuda; mps -> cpu
            return "cpu"
    except Exception:  # noqa: BLE001
        pass
    return "cpu"


def transcribe_faster_whisper(
    audio_path: Path,
    *,
    model_name: str,
    device: str,
    compute_type: str,
    language: str,
) -> Transcript:
    from faster_whisper import WhisperModel

    dev = resolve_device(device)
    ctype = compute_type
    if dev == "cpu" and ctype in {"float16", "float32"}:
        ctype = "int8"
    log.info(
        "faster-whisper model=%s device=%s compute_type=%s",
        model_name,
        dev,
        ctype,
    )
    model = WhisperModel(model_name, device=dev, compute_type=ctype)
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language or None,
        word_timestamps=True,
        vad_filter=True,
    )
    segments: list[TranscriptSegment] = []
    for i, seg in enumerate(segments_iter):
        words: list[TranscriptWord] = []
        for w in seg.words or []:
            words.append(
                TranscriptWord(
                    word=str(w.word).strip(),
                    start=float(w.start),
                    end=float(w.end),
                )
            )
        segments.append(
            TranscriptSegment(
                id=i,
                start=float(seg.start),
                end=float(seg.end),
                text=str(seg.text).strip(),
                words=words,
            )
        )
    duration = float(getattr(info, "duration", 0.0) or 0.0)
    if not duration and segments:
        duration = segments[-1].end
    return Transcript(
        language=str(getattr(info, "language", language) or language),
        engine="faster-whisper",
        segments=segments,
        duration=duration,
    )


def transcribe_whisperx(
    audio_path: Path,
    *,
    model_name: str,
    device: str,
    language: str,
    align: bool,
    diarize: bool,
    hf_token: str | None,
) -> Transcript:
    from modules.transcriber.transcribe_aligned import transcribe_aligned

    data = transcribe_aligned(
        audio_path,
        model_name=model_name,
        device=resolve_device(device),
        language=language,
        diarize=diarize,
        align=align,
        hf_token=hf_token,
    )
    return Transcript.model_validate(data)


def build_stub_transcript(project: Project) -> Transcript:
    topic = project.topic or "this topic"
    segments = [
        TranscriptSegment(
            id=0,
            start=0.0,
            end=4.5,
            text=f"Welcome. Today we cover {topic}.",
            words=[
                TranscriptWord(word="Welcome.", start=0.0, end=0.6),
                TranscriptWord(word="Today", start=0.7, end=1.0),
            ],
        ),
        TranscriptSegment(
            id=1,
            start=4.5,
            end=10.0,
            text="Here are the core concepts you need to know.",
            words=[],
        ),
        TranscriptSegment(
            id=2,
            start=10.0,
            end=15.0,
            text="Thanks for watching, and see you in the next one.",
            words=[],
        ),
    ]
    return Transcript(
        language=project.config.transcription.language,
        engine="stub",
        segments=segments,
        duration=15.0,
    )


class TranscriberStage:
    """Transcribe final.mp4 audio -> transcript.json + SRT/VTT."""

    name = "transcriber"

    def run(self, project: Project) -> StageResult:
        if not project.paths.final_video.exists():
            raise FileNotFoundError(
                f"Missing final.mp4 — run video_assembler first: {project.paths.final_video}"
            )

        cfg = project.config.transcription
        force_stub = os.getenv("YT_STUDIO_STUB_TRANSCRIBE") == "1"
        transcript: Transcript

        if force_stub:
            log.info("Transcriber stub forced")
            transcript = build_stub_transcript(project)
        else:
            wav = project.paths.root / "audio_extract.wav"
            try:
                extract_audio(
                    project.paths.final_video,
                    wav,
                    ffmpeg_bin=project.config.video.ffmpeg_bin,
                )
                engine = cfg.engine
                if engine == "whisperx":
                    try:
                        transcript = transcribe_whisperx(
                            wav,
                            model_name=cfg.model,
                            device=cfg.device,
                            language=cfg.language,
                            align=cfg.align,
                            diarize=cfg.diarize,
                            hf_token=os.getenv("HF_TOKEN"),
                        )
                    except Exception as exc:  # noqa: BLE001
                        log.warning(
                            "WhisperX failed (%s); falling back to faster-whisper",
                            exc,
                        )
                        transcript = transcribe_faster_whisper(
                            wav,
                            model_name=cfg.model if cfg.model != "large-v3" else "base",
                            device=cfg.device,
                            compute_type=cfg.compute_type,
                            language=cfg.language,
                        )
                else:
                    # For CI speed, allow small model via env
                    model = os.getenv("YT_STUDIO_WHISPER_MODEL") or cfg.model
                    if os.getenv("YT_STUDIO_FAST_TRANSCRIBE") == "1":
                        model = "tiny"
                    transcript = transcribe_faster_whisper(
                        wav,
                        model_name=model,
                        device=cfg.device,
                        compute_type=cfg.compute_type,
                        language=cfg.language,
                    )
            except Exception as exc:  # noqa: BLE001
                if (
                    project.checkpoint.options.get("allow_stub_fallback")
                    or os.getenv("YT_STUDIO_ALLOW_TRANSCRIBE_FALLBACK") == "1"
                ):
                    log.error("Transcription failed (%s); using stub", exc)
                    transcript = build_stub_transcript(project)
                else:
                    raise RuntimeError(f"Transcription failed: {exc}") from exc
            finally:
                if wav.exists() and os.getenv("YT_STUDIO_KEEP_EXTRACT") != "1":
                    wav.unlink(missing_ok=True)

        segs: list[dict[str, Any]] = [
            s.model_dump() for s in transcript.segments
        ]
        payload = transcript.model_dump(by_alias=True)
        if transcript.engine == "stub":
            payload["_stub"] = True
        write_json(
            project.paths.transcript_json,
            payload,
        )
        write_text(project.paths.transcript_srt, segments_to_srt(segs))
        write_text(project.paths.transcript_vtt, segments_to_vtt(segs))

        # Optional burn-in of long-form subtitles as a side artifact
        if project.checkpoint.options.get("burn_subtitles") or os.getenv(
            "YT_STUDIO_BURN_SUBTITLES"
        ) == "1":
            try:
                from modules.subtitles.burn_in import burn_subtitles

                burn_subtitles(
                    project.paths.final_video,
                    project.paths.transcript_srt,
                    project.paths.final_video_subtitled,
                    ffmpeg_bin=project.config.video.ffmpeg_bin,
                    font=project.config.subtitles.font,
                    font_size=project.config.subtitles.font_size,
                    margin_v=project.config.subtitles.margin_v,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Subtitle burn-in skipped: %s", exc)

        stub = transcript.engine == "stub"
        return StageResult(
            stage=self.name,
            artifacts=[
                project.rel(project.paths.transcript_json),
                project.rel(project.paths.transcript_srt),
                project.rel(project.paths.transcript_vtt),
            ],
            meta={
                "segment_count": len(transcript.segments),
                "engine": transcript.engine,
                "language": transcript.language,
                "duration": transcript.duration,
                "stub": stub,
            },
            message=f"{transcript.engine} transcript with {len(transcript.segments)} segment(s)",
        )
