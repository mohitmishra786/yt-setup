"""Pluggable voice engine interface + pipeline stage."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import wave
from abc import ABC, abstractmethod
from pathlib import Path

from core.logging_setup import get_logger
from core.project import Project
from core.stages import StageResult

log = get_logger(__name__)


class VoiceEngine(ABC):
    """Contract for TTS / voice-cloning backends."""

    name: str

    @abstractmethod
    def synthesize(self, text: str, voice_id: str, output_path: Path) -> Path:
        """Render `text` with `voice_id` to `output_path`. Returns path written."""

    def warmup(self) -> None:
        """Optional model load / GPU init."""


class VoiceEngineError(RuntimeError):
    pass


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def convert_to_mp3(src: Path, dest: Path, *, sample_rate: int = 24000) -> Path:
    """Convert wav/aiff/m4a to mp3 via ffmpeg."""
    _ensure_parent(dest)
    cmd = [
        _ffmpeg_bin(),
        "-y",
        "-i",
        str(src),
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        "-codec:a",
        "libmp3lame",
        "-qscale:a",
        "2",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise VoiceEngineError(f"ffmpeg audio convert failed: {proc.stderr[-1500:]}")
    return dest


def write_silence_mp3(path: Path, duration_seconds: float = 1.0, sample_rate: int = 24000) -> Path:
    """Generate silent MP3 (last-resort fallback for CI without TTS)."""
    _ensure_parent(path)
    cmd = [
        _ffmpeg_bin(),
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r={sample_rate}:cl=mono",
        "-t",
        f"{max(0.3, duration_seconds):.3f}",
        "-q:a",
        "9",
        "-acodec",
        "libmp3lame",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        # Absolute last resort: minimal valid-ish frame
        from core.stub_utils import write_minimal_mp3

        write_minimal_mp3(path)
    return path


class EdgeTTSEngine(VoiceEngine):
    """
    High-quality free cloud TTS via edge-tts (Microsoft neural voices).

    Production-ready default when local Chatterbox weights are not installed.
    """

    name = "edge_tts"

    def __init__(self, *, default_voice: str = "en-US-GuyNeural") -> None:
        self.default_voice = default_voice

    def synthesize(self, text: str, voice_id: str, output_path: Path) -> Path:
        try:
            import asyncio

            import edge_tts
        except ImportError as exc:
            raise VoiceEngineError(
                "edge-tts is not installed. pip install edge-tts"
            ) from exc

        voice = voice_id if voice_id and voice_id != "default" else self.default_voice
        # Map short ids to neural voices
        aliases = {
            "default": self.default_voice,
            "male": "en-US-GuyNeural",
            "female": "en-US-JennyNeural",
            "mohit": "en-IN-PrabhatNeural",
        }
        voice = aliases.get(voice.lower(), voice)

        _ensure_parent(output_path)
        # edge-tts writes mp3 directly
        tmp = output_path if output_path.suffix.lower() == ".mp3" else output_path.with_suffix(".mp3")

        async def _run() -> None:
            communicate = edge_tts.Communicate(text.strip() or " ", voice)
            await communicate.save(str(tmp))

        try:
            asyncio.run(_run())
        except RuntimeError:
            # Nested event loop environments
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_run())
            finally:
                loop.close()

        if tmp != output_path:
            tmp.replace(output_path)
        if not output_path.exists() or output_path.stat().st_size < 100:
            raise VoiceEngineError(f"edge-tts produced empty file: {output_path}")
        return output_path


class MacSayEngine(VoiceEngine):
    """Offline macOS `say` + ffmpeg conversion."""

    name = "mac_say"

    def synthesize(self, text: str, voice_id: str, output_path: Path) -> Path:
        if not shutil.which("say"):
            raise VoiceEngineError("macOS say not available")
        _ensure_parent(output_path)
        aiff = output_path.with_suffix(".aiff")
        voice = None if voice_id in ("", "default") else voice_id
        cmd = ["say", "-o", str(aiff)]
        if voice:
            cmd.extend(["-v", voice])
        cmd.append(text.strip() or " ")
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise VoiceEngineError(f"say failed: {proc.stderr}")
        try:
            convert_to_mp3(aiff, output_path)
        finally:
            aiff.unlink(missing_ok=True)
        return output_path


class SilenceEngine(VoiceEngine):
    """CI / offline last resort: duration scaled by text length."""

    name = "silence"

    def synthesize(self, text: str, voice_id: str, output_path: Path) -> Path:
        _ = voice_id
        words = max(1, len((text or "").split()))
        # ~2.5 words/sec rough narration pace, min 1.2s
        duration = max(1.2, words / 2.5)
        return write_silence_mp3(output_path, duration_seconds=duration)


def get_engine(
    engine_name: str,
    *,
    require_clone: bool = True,
    chatterbox_exaggeration: float | None = None,
    chatterbox_cfg_weight: float | None = None,
) -> VoiceEngine:
    """
    Factory for configured voice backends.

    If require_clone is True (default for production narration), failure to load
    a real cloning engine raises instead of falling back to robotic generic TTS.
    """
    name = (engine_name or "chatterbox").lower()
    errors: list[str] = []
    clone_engines = {"chatterbox", "xtts", "elevenlabs"}

    def try_primary() -> VoiceEngine | None:
        if name == "chatterbox":
            try:
                from modules.voice.chatterbox_engine import ChatterboxEngine

                return ChatterboxEngine(
                    exaggeration=chatterbox_exaggeration,
                    cfg_weight=chatterbox_cfg_weight,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"chatterbox: {exc}")
                return None
        if name == "xtts":
            try:
                from modules.voice.xtts_engine import XTTSEngine

                return XTTSEngine()
            except Exception as exc:  # noqa: BLE001
                errors.append(f"xtts: {exc}")
                return None
        if name == "elevenlabs":
            try:
                from modules.voice.elevenlabs_engine import ElevenLabsEngine

                return ElevenLabsEngine()
            except Exception as exc:  # noqa: BLE001
                errors.append(f"elevenlabs: {exc}")
                return None
        if name in {"edge_tts", "edge-tts"}:
            try:
                voice = "en-US-GuyNeural"
                try:
                    from core.config import load_config

                    voice = load_config().voice.edge_tts_voice or voice
                except Exception:  # noqa: BLE001
                    pass
                return EdgeTTSEngine(default_voice=voice)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"edge_tts: {exc}")
                return None
        if name == "mac_say":
            return MacSayEngine()
        if name == "silence":
            return SilenceEngine()
        errors.append(f"unknown engine {name!r}")
        return None

    engine = try_primary()
    if engine is not None:
        return engine

    detail = "; ".join(errors) or "n/a"
    if require_clone and name in clone_engines:
        raise VoiceEngineError(
            f"Clone engine {name!r} is unavailable ({detail}).\n"
            "Install Chatterbox for local pro voice cloning:\n"
            "  pip install chatterbox-tts\n"
            "  # or see https://github.com/resemble-ai/chatterbox\n"
            "Prepare your voice:\n"
            "  python cli.py prepare-voice --voice YOUR_ID --audio clean.wav --consent\n"
            "Docs: docs/VOICE_CLONING.md\n"
            "To allow generic robotic TTS temporarily: set voice.require_clone: false "
            "or YT_STUDIO_ALLOW_GENERIC_TTS=1"
        )

    # Explicit generic fallbacks only when allowed
    for factory in (EdgeTTSEngine, MacSayEngine, SilenceEngine):
        try:
            eng = factory()  # type: ignore[call-arg]
            log.warning(
                "Voice engine %r unavailable (%s); using generic %s",
                name,
                detail,
                eng.name,
            )
            return eng
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{factory.__name__}: {exc}")
            continue

    raise VoiceEngineError(f"All voice engines failed: {errors}")


def probe_audio_duration(path: Path) -> float:
    """Return duration seconds using ffprobe, wave, or estimate."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
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
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                return max(0.1, float(proc.stdout.strip()))
            except ValueError:
                pass
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wf:
                return max(0.1, wf.getnframes() / float(wf.getframerate()))
        except Exception:  # noqa: BLE001
            pass
    # Fallback estimate from size (very rough for mp3 ~16KB/s at 128k)
    size = path.stat().st_size if path.exists() else 0
    return max(1.0, size / 16000.0)


class VoiceStage:
    """Stage 3 — synthesize one audio file per slide from speaker_notes."""

    name = "voice"

    def run(self, project: Project) -> StageResult:
        if not project.paths.outline.exists():
            raise FileNotFoundError(
                f"Missing outline.json — run scriptwriter or import-pptx first: "
                f"{project.paths.outline}"
            )

        with project.paths.outline.open(encoding="utf-8") as fh:
            outline = json.load(fh)

        slides = outline.get("slides") or []
        if not slides:
            raise ValueError("outline.json has no slides")

        configured = project.config.voice.engine
        engine_name = str(
            project.checkpoint.options.get("voice_engine") or configured
        )
        require_clone = bool(project.config.voice.require_clone)
        if os.getenv("YT_STUDIO_ALLOW_GENERIC_TTS") == "1":
            require_clone = False
        if os.getenv("YT_STUDIO_STUB_VOICE") == "1":
            engine: VoiceEngine = SilenceEngine()
        else:
            engine = get_engine(
                engine_name,
                require_clone=require_clone,
                chatterbox_exaggeration=project.config.voice.chatterbox_exaggeration,
                chatterbox_cfg_weight=project.config.voice.chatterbox_cfg_weight,
            )

        voice_id = project.voice_id
        # Validate clone profile early for chatterbox/xtts
        if engine.name in {"chatterbox", "xtts"} and voice_id not in {"", "default"}:
            from modules.voice.profile import get_profile, validate_profile_for_cloning

            profile = get_profile(voice_id)
            warnings = validate_profile_for_cloning(profile)
            for w in warnings:
                log.warning("%s", w)
            if not profile.exists():
                raise VoiceEngineError(
                    f"No voice profile for voice_id={voice_id!r}.\n"
                    f"Record clean audio, then:\n"
                    f"  python cli.py prepare-voice --voice {voice_id} "
                    f"--audio /path/to/clean.wav --consent\n"
                    f"See docs/VOICE_CLONING.md and docs/VOICE_RECORDING_SCRIPT.md"
                )
        elif engine.name == "chatterbox" and voice_id in {"", "default"}:
            from modules.voice.profile import get_profile

            if not get_profile("default").exists() and not get_profile(voice_id or "default").exists():
                raise VoiceEngineError(
                    "Chatterbox needs a prepared voice profile.\n"
                    "  python cli.py prepare-voice --voice myname --audio clean.wav --consent\n"
                    "  python cli.py run ... --voice myname\n"
                    "See docs/VOICE_CLONING.md"
                )

        if engine.name in {"edge_tts", "mac_say"}:
            log.warning(
                "Using generic TTS engine %s — this will NOT sound like your cloned voice. "
                "For pro cloning use chatterbox + prepare-voice (docs/VOICE_CLONING.md).",
                engine.name,
            )

        artifacts: list[str] = []
        durations: list[float] = []
        project.paths.audio_dir.mkdir(parents=True, exist_ok=True)

        log.info(
            "Voice engine=%s voice_id=%s slides=%d require_clone=%s",
            engine.name,
            voice_id,
            len(slides),
            require_clone,
        )

        fail_hard = require_clone and engine.name in {"chatterbox", "xtts", "elevenlabs"}
        for slide in slides:
            idx = int(slide.get("index") or (len(artifacts) + 1))
            notes = str(slide.get("speaker_notes") or slide.get("title") or " ").strip()
            out = project.paths.audio_for_slide(idx)
            try:
                engine.synthesize(notes, voice_id, out)
            except Exception as exc:  # noqa: BLE001
                if fail_hard:
                    raise VoiceEngineError(
                        f"Clone synthesis failed on slide {idx}: {exc}"
                    ) from exc
                log.error("synthesize failed slide %d (%s); silence fallback", idx, exc)
                SilenceEngine().synthesize(notes, voice_id, out)
            dur = probe_audio_duration(out)
            durations.append(dur)
            artifacts.append(project.rel(out))
            log.info("audio slide_%02d duration=%.2fs -> %s", idx, dur, out.name)

        meta_path = project.paths.audio_dir / "durations.json"
        meta_path.write_text(
            json.dumps(
                {
                    "engine": engine.name,
                    "voice_id": voice_id,
                    "durations": durations,
                    "files": artifacts,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        artifacts.append(project.rel(meta_path))

        return StageResult(
            stage=self.name,
            artifacts=artifacts,
            meta={
                "engine": engine.name,
                "voice_id": voice_id,
                "clip_count": len(slides),
                "total_duration": round(sum(durations), 3),
                "stub": engine.name == "silence",
                "cloned": engine.name in {"chatterbox", "xtts", "elevenlabs"},
            },
            message=f"{len(slides)} clip(s) via {engine.name} ({sum(durations):.1f}s)",
        )
