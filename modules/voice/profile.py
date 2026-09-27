"""Voice profile layout for professional-grade cloning (Chatterbox / ElevenLabs PVC)."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.logging_setup import get_logger

log = get_logger(__name__)

VOICES_ROOT = Path(__file__).resolve().parent / "voices"


@dataclass
class VoiceProfile:
    """
    On-disk voice clone profile.

    Layout:
      modules/voice/voices/<voice_id>/
        profile.json
        reference.wav          # primary clip used for zero-shot cloning
        samples/               # optional extra clean takes (wav/flac/mp3)
        consent.txt            # optional: you confirm you own this voice
    """

    voice_id: str
    root: Path

    @property
    def profile_json(self) -> Path:
        return self.root / "profile.json"

    @property
    def reference_wav(self) -> Path:
        return self.root / "reference.wav"

    @property
    def samples_dir(self) -> Path:
        return self.root / "samples"

    def exists(self) -> bool:
        return self.root.is_dir() and (
            self.reference_wav.exists()
            or any(self.samples_dir.glob("*"))
            or list(self.root.glob("*.wav"))
            or list(self.root.glob("*.mp3"))
        )

    def load_meta(self) -> dict[str, Any]:
        if self.profile_json.exists():
            return json.loads(self.profile_json.read_text(encoding="utf-8"))
        return {}

    def save_meta(self, meta: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.profile_json.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def resolve_reference(self) -> Path:
        """Best single reference file for zero-shot engines (Chatterbox)."""
        if self.reference_wav.exists() and self.reference_wav.stat().st_size > 1000:
            return self.reference_wav
        candidates: list[Path] = []
        for pattern in ("*.wav", "*.flac", "*.mp3", "*.m4a"):
            candidates.extend(self.root.glob(pattern))
            if self.samples_dir.is_dir():
                candidates.extend(self.samples_dir.glob(pattern))
        # Prefer longest file (usually best coverage)
        candidates = [c for c in candidates if c.is_file() and c.stat().st_size > 1000]
        if not candidates:
            raise FileNotFoundError(
                f"No reference audio for voice_id={self.voice_id!r} under {self.root}. "
                f"Run: python cli.py prepare-voice --voice {self.voice_id} --audio your.wav"
            )
        candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
        return candidates[0]

    def all_sample_paths(self) -> list[Path]:
        paths: list[Path] = []
        if self.reference_wav.exists():
            paths.append(self.reference_wav)
        if self.samples_dir.is_dir():
            for pattern in ("*.wav", "*.flac", "*.mp3", "*.m4a"):
                paths.extend(sorted(self.samples_dir.glob(pattern)))
        for pattern in ("*.wav", "*.flac", "*.mp3"):
            for p in sorted(self.root.glob(pattern)):
                if p not in paths and p.name != "reference.wav":
                    paths.append(p)
        return paths


def get_profile(voice_id: str, *, voices_root: Path | None = None) -> VoiceProfile:
    root = (voices_root or VOICES_ROOT) / voice_id
    return VoiceProfile(voice_id=voice_id, root=root)


def probe_duration_seconds(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        # rough estimate
        return max(1.0, path.stat().st_size / 32000.0)
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
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def normalize_to_reference_wav(
    sources: list[Path],
    dest_wav: Path,
    *,
    sample_rate: int = 24000,
    target_lufs: float | None = -16.0,
) -> Path:
    """
    Convert and optionally concat source clips into a clean mono reference.wav.

    For Chatterbox zero-shot, a single clean 15–60s clip is ideal.
    Extra samples are concatenated (with short silence) so more of your voice
    is represented — closer to PVC-style coverage than a 3-second clip.
    """
    if not sources:
        raise ValueError("No source audio files provided")
    for s in sources:
        if not s.exists():
            raise FileNotFoundError(s)

    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("ffmpeg required to prepare voice profiles")

    # Normalize each to temp mono wav then concat
    tmp_dir = dest_wav.parent / ".prep_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    normalized: list[Path] = []
    try:
        for i, src in enumerate(sources):
            out = tmp_dir / f"n_{i:02d}.wav"
            # high-pass mild + loudnorm for consistency (optional)
            af = f"highpass=f=80,lowpass=f=12000,loudnorm=I={target_lufs}:TP=-1.5:LRA=11"
            cmd = [
                ff,
                "-y",
                "-i",
                str(src),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-af",
                af,
                str(out),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                # retry without loudnorm
                cmd = [
                    ff,
                    "-y",
                    "-i",
                    str(src),
                    "-ac",
                    "1",
                    "-ar",
                    str(sample_rate),
                    str(out),
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if proc.returncode != 0:
                    raise RuntimeError(f"ffmpeg normalize failed for {src}: {proc.stderr[-800:]}")
            normalized.append(out)

        if len(normalized) == 1:
            shutil.copy2(normalized[0], dest_wav)
        else:
            list_file = tmp_dir / "concat.txt"
            # Insert 200ms silence between clips
            silence = tmp_dir / "silence.wav"
            subprocess.run(
                [
                    ff,
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"anullsrc=r={sample_rate}:cl=mono",
                    "-t",
                    "0.2",
                    str(silence),
                ],
                capture_output=True,
                check=False,
            )
            lines: list[str] = []
            for i, n in enumerate(normalized):
                lines.append(f"file '{n.resolve()}'")
                if i < len(normalized) - 1 and silence.exists():
                    lines.append(f"file '{silence.resolve()}'")
            list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            proc = subprocess.run(
                [
                    ff,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_file),
                    "-c",
                    "copy",
                    str(dest_wav),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg concat failed: {proc.stderr[-800:]}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return dest_wav


def prepare_voice_profile(
    voice_id: str,
    audio_files: list[Path],
    *,
    display_name: str | None = None,
    language: str = "en",
    consent: bool = False,
    voices_root: Path | None = None,
    also_copy_samples: bool = True,
) -> VoiceProfile:
    """Create/update a voice profile from one or more clean recordings."""
    profile = get_profile(voice_id, voices_root=voices_root)
    profile.root.mkdir(parents=True, exist_ok=True)
    if also_copy_samples:
        profile.samples_dir.mkdir(exist_ok=True)
        for i, src in enumerate(audio_files):
            dest = profile.samples_dir / f"sample_{i + 1:02d}{src.suffix.lower()}"
            shutil.copy2(src, dest)

    normalize_to_reference_wav(audio_files, profile.reference_wav)
    duration = probe_duration_seconds(profile.reference_wav)

    quality = "short"
    notes: list[str] = []
    if duration < 8:
        quality = "too_short"
        notes.append(
            "Reference is under 8s. Cloning will work but often sounds unstable. "
            "Record at least 15–30s of clean speech; 2–5 minutes is better; "
            "30+ minutes (multi-file) approaches ElevenLabs PVC-style coverage."
        )
    elif duration < 20:
        quality = "minimal"
        notes.append("OK for zero-shot. 30–90s of varied sentences will sound more natural.")
    elif duration < 120:
        quality = "good"
        notes.append("Good zero-shot reference length for Chatterbox.")
    else:
        quality = "excellent"
        notes.append(
            "Strong coverage. For best results keep audio dry (no music), single speaker, "
            "consistent mic distance."
        )

    meta = {
        "voice_id": voice_id,
        "display_name": display_name or voice_id,
        "language": language,
        "reference_file": "reference.wav",
        "reference_duration_seconds": round(duration, 2),
        "quality_tier": quality,
        "sample_count": len(audio_files),
        "consent_own_voice": consent,
        "engine_recommendation": "chatterbox",
        "notes": notes,
        "created_from": [str(p) for p in audio_files],
    }
    profile.save_meta(meta)
    if consent:
        (profile.root / "consent.txt").write_text(
            "I confirm I own or have rights to use this voice for synthesis.\n",
            encoding="utf-8",
        )
    log.info(
        "Voice profile ready id=%s duration=%.1fs tier=%s path=%s",
        voice_id,
        duration,
        quality,
        profile.root,
    )
    return profile


def validate_profile_for_cloning(profile: VoiceProfile) -> list[str]:
    """Return human-readable warnings (empty list = OK)."""
    warnings: list[str] = []
    if not profile.exists():
        return [
            f"Voice profile '{profile.voice_id}' not found at {profile.root}. "
            f"Create it with: python cli.py prepare-voice --voice {profile.voice_id} --audio me.wav"
        ]
    try:
        ref = profile.resolve_reference()
    except FileNotFoundError as exc:
        return [str(exc)]
    dur = probe_duration_seconds(ref)
    if dur < 5:
        warnings.append(f"Reference only {dur:.1f}s — expect robotic/unstable clone.")
    elif dur < 15:
        warnings.append(
            f"Reference {dur:.1f}s is usable; 30–90s clean speech is recommended for pro narration."
        )
    meta = profile.load_meta()
    if not meta.get("consent_own_voice"):
        warnings.append(
            "No consent flag on profile. Only clone voices you own or have rights to use."
        )
    return warnings
