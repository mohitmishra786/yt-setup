"""Use narration you recorded yourself instead of a synthesized voice.

`cli.py voice-import --project <id> --dir <folder>` takes one recording per outline slide
(`slide_01.*`, `slide_02.*`, … — or files sorted by name when there is exactly one per
slide), masters each to the same loudness as the clone pipeline (-16 LUFS), writes
audio/slide_XX.mp3 + durations.json + words.json, and marks the voice stage done. Captions,
`cli.py cues`, `cli.py pace`, the scene kit and the Shorts builder then work unchanged.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from core.logging_setup import get_logger
from core.project import Project

from modules.voice.engine import convert_to_mp3, probe_audio_duration, write_word_timings

log = get_logger(__name__)

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg", ".aiff", ".aif"}
MASTER = (
    "highpass=f=70,deesser=i=0.35,"
    "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80:makeup=2,"
    "loudnorm=I=-16:TP=-1.5:LRA=9"
)


def match_recordings(folder: Path, slide_count: int) -> list[Path]:
    """Recordings for slides 1..N: `slide_NN.*` names win; else exactly N files sorted by name."""
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXT)
    named: dict[int, Path] = {}
    for f in files:
        m = re.search(r"(?:slide|scene)[_\- ]?0*(\d+)", f.stem, re.IGNORECASE)
        if m:
            named[int(m.group(1))] = f
    if all(i in named for i in range(1, slide_count + 1)):
        return [named[i] for i in range(1, slide_count + 1)]
    if len(files) == slide_count:
        return files
    missing = [i for i in range(1, slide_count + 1) if i not in named]
    raise FileNotFoundError(
        f"Need one recording per outline slide ({slide_count}) in {folder}: name them "
        f"slide_01.wav, slide_02.wav, … (missing {missing}) or provide exactly {slide_count} files."
    )


def master_file(src: Path, dest_mp3: Path, *, trim_silence: bool = True) -> None:
    ff = shutil.which("ffmpeg") or "ffmpeg"
    chain = MASTER
    if trim_silence:  # trim leading/trailing room tone so scenes start on the first word
        edge = "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08"
        chain = f"{edge},areverse,{edge},areverse,{MASTER}"
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "mastered.wav"
        cmd = [ff, "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "24000", "-af", chain,
               str(wav)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed on {src.name}: {proc.stderr[-800:]}")
        convert_to_mp3(wav, dest_mp3, sample_rate=24000)


def import_narration(
    project: Project, folder: Path, *, trim_silence: bool = True
) -> dict[str, Any]:
    outline = json.loads(project.paths.outline.read_text(encoding="utf-8"))
    slides = outline.get("slides") or []
    if not slides:
        raise ValueError("outline.json has no slides")
    recordings = match_recordings(folder, len(slides))
    project.paths.audio_dir.mkdir(parents=True, exist_ok=True)
    durations: list[float] = []
    files: list[str] = []
    for slide, rec in zip(slides, recordings, strict=True):
        idx = int(slide.get("index") or len(files) + 1)
        out = project.paths.audio_for_slide(idx)
        master_file(rec, out, trim_silence=trim_silence)
        out.with_suffix(".key").unlink(missing_ok=True)  # never mistaken for a synthesized take
        durations.append(probe_audio_duration(out))
        files.append(project.rel(out))
        log.info("slide_%02d <- %s (%.2fs)", idx, rec.name, durations[-1])
    write_word_timings(project, slides, durations)
    meta = {"engine": "recorded", "voice_id": "recorded", "durations": durations, "files": files}
    (project.paths.audio_dir / "durations.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    project.checkpoint.mark_completed(
        "voice",
        artifacts=[*files, "audio/durations.json", "audio/words.json"],
        meta={"engine": "recorded", "clip_count": len(files), "total_duration": sum(durations)},
    )
    project.save()
    return {"slides": len(files), "total": round(sum(durations), 2)}
