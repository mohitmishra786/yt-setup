"""Export word/segment transcripts to SRT and VTT."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _fmt_ts(seconds: float, *, vtt: bool = False) -> str:
    if seconds < 0:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    sep = "." if vtt else ","
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def segments_to_srt(segments: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        start = float(seg["start"])
        end = float(seg["end"])
        text = str(seg.get("text", "")).strip()
        lines.append(str(i))
        lines.append(f"{_fmt_ts(start)} --> {_fmt_ts(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def segments_to_vtt(segments: list[dict[str, Any]]) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = float(seg["start"])
        end = float(seg["end"])
        text = str(seg.get("text", "")).strip()
        lines.append(f"{_fmt_ts(start, vtt=True)} --> {_fmt_ts(end, vtt=True)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def write_srt(path: Path, segments: list[dict[str, Any]]) -> None:
    path.write_text(segments_to_srt(segments), encoding="utf-8")


def write_vtt(path: Path, segments: list[dict[str, Any]]) -> None:
    path.write_text(segments_to_vtt(segments), encoding="utf-8")
