"""Configuration loading and validation for yt-studio."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class ProjectSettings(BaseModel):
    root: Path = Path("projects")
    video_width: int = 1920
    video_height: int = 1080
    shorts_width: int = 1080
    shorts_height: int = 1920
    fps: int = 30


class LLMSettings(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192
    temperature: float = 0.4


class ElevenLabsSettings(BaseModel):
    model_id: str = "eleven_multilingual_v2"
    stability: float = 0.5
    similarity_boost: float = 0.75


class VoiceSettings(BaseModel):
    # chatterbox = local pro clone (recommended)
    # elevenlabs = paid PVC/IVC voice_id
    # edge_tts / mac_say = generic (not a personal clone)
    # silence = CI only
    engine: Literal[
        "chatterbox", "xtts", "elevenlabs", "edge_tts", "mac_say", "silence"
    ] = "chatterbox"
    default_voice: str = "default"
    sample_rate: int = 24000
    # When true, never fall back to robotic generic TTS if clone engine fails
    require_clone: bool = True
    # Free generic neural TTS (NOT a personal clone) — only used if require_clone=false
    edge_tts_voice: str = "en-US-GuyNeural"
    # Optional expressiveness for Chatterbox (engine-dependent)
    chatterbox_exaggeration: float | None = None
    chatterbox_cfg_weight: float | None = None
    elevenlabs: ElevenLabsSettings = Field(default_factory=ElevenLabsSettings)


class MusicSettings(BaseModel):
    enabled: bool = False
    # Path to bed track (wav/mp3); empty = no music
    track_path: str = ""
    # Voice-over volume multiplier when ducking (0-1 music under voice)
    music_volume: float = 0.12
    duck_voice_threshold: float = 0.02


class VideoSettings(BaseModel):
    libreoffice_bin: str = ""
    ffmpeg_bin: str = "ffmpeg"
    crossfade_seconds: float = 0.35
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    crf: int = 18
    preset: str = "medium"


class TranscriptionSettings(BaseModel):
    engine: Literal["whisperx", "faster-whisper"] = "whisperx"
    model: str = "large-v3"
    device: Literal["cuda", "cpu", "auto"] = "auto"
    compute_type: str = "float16"
    language: str = "en"
    align: bool = True
    diarize: bool = False


class ChaptersSettings(BaseModel):
    min_chapter_gap_seconds: int = 20
    max_chapters: int = 40


class ShortsSettings(BaseModel):
    vantage_api_url: str = "http://127.0.0.1:8080"
    timeout_seconds: int = 600
    default_keywords: list[str] = Field(default_factory=list)


class SubtitlesSettings(BaseModel):
    font: str = "Arial"
    font_size: int = 42
    font_size_shorts: int = 56
    primary_color: str = "&H00FFFFFF"
    outline_color: str = "&H00000000"
    outline: int = 2
    margin_v: int = 60


class ThumbnailSettings(BaseModel):
    width: int = 1280
    height: int = 720
    font: str = "Arial"
    max_title_chars: int = 60


class PublisherSettings(BaseModel):
    default_privacy: Literal["private", "unlisted", "public"] = "private"
    category_id: str = "27"
    token_path: Path = Path(".credentials/youtube_token.json")
    client_secrets_path: Path = Path(".credentials/client_secret.json")


class PipelineSettings(BaseModel):
    stages: list[str] = Field(
        default_factory=lambda: [
            "scriptwriter",
            "slidebuilder",
            "voice",
            "video_assembler",
            "transcriber",
            "chapters",
            "shorts",
            "publisher",
        ]
    )
    fail_fast: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("stages")
    @classmethod
    def stages_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("pipeline.stages must not be empty")
        return v


class AppConfig(BaseModel):
    """Validated application configuration."""

    project: ProjectSettings = Field(default_factory=ProjectSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    video: VideoSettings = Field(default_factory=VideoSettings)
    music: MusicSettings = Field(default_factory=MusicSettings)
    transcription: TranscriptionSettings = Field(default_factory=TranscriptionSettings)
    chapters: ChaptersSettings = Field(default_factory=ChaptersSettings)
    shorts: ShortsSettings = Field(default_factory=ShortsSettings)
    subtitles: SubtitlesSettings = Field(default_factory=SubtitlesSettings)
    thumbnail: ThumbnailSettings = Field(default_factory=ThumbnailSettings)
    publisher: PublisherSettings = Field(default_factory=PublisherSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)

    # Resolved at load time
    repo_root: Path = Field(default_factory=lambda: Path.cwd())

    def projects_dir(self) -> Path:
        root = self.project.root
        if root.is_absolute():
            return root
        return (self.repo_root / root).resolve()


def _find_repo_root(start: Path | None = None) -> Path:
    """Walk upward looking for pyproject.toml or config.yaml.example."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "pyproject.toml").exists() or (
            candidate / "config.yaml.example"
        ).exists():
            return candidate
    return cur


def load_config(
    config_path: Path | str | None = None,
    *,
    env_file: Path | str | None = None,
) -> AppConfig:
    """
    Load YAML config + .env secrets into a validated AppConfig.

    Precedence: explicit path > ./config.yaml > defaults from AppConfig.
    """
    repo_root = _find_repo_root()
    load_dotenv(env_file or (repo_root / ".env"))

    path: Path | None
    if config_path is not None:
        path = Path(config_path)
    else:
        candidate = repo_root / "config.yaml"
        path = candidate if candidate.exists() else None

    raw: dict[str, Any] = {}
    if path is not None:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with path.open(encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config root must be a mapping, got {type(loaded)}")
        raw = loaded

    # Allow env override for shorts URL without editing YAML
    if os.getenv("VANTAGE_API_URL"):
        raw.setdefault("shorts", {})
        if isinstance(raw["shorts"], dict):
            raw["shorts"]["vantage_api_url"] = os.environ["VANTAGE_API_URL"]

    cfg = AppConfig.model_validate({**raw, "repo_root": repo_root})
    return cfg
