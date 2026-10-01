"""Pick the cleanest short prompt clip for zero-shot cloning.

Chatterbox conditions only on the first ~10s of its reference (6s for the text-to-token
model), so a long reference.wav is mostly ignored and whatever sits at its start — a
breath, a pause, mic handling — becomes "the voice". This module scans the original
recordings for the window with continuous, steady, unclipped speech and writes it as
`prompt.wav`, which VoiceProfile.resolve_reference() prefers.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
from core.logging_setup import get_logger

log = get_logger(__name__)

Audio = npt.NDArray[np.float32]

SR = 24000
FRAME_S = 0.05
PROMPT_S = 10.0
CLEAN_FILTER = "highpass=f=70,afftdn=nf=-50,loudnorm=I=-20:TP=-2:LRA=7"


@dataclass
class Candidate:
    source: Path
    start: float
    score: float
    speech_ratio: float
    longest_pause: float


def _ffmpeg() -> str:
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("ffmpeg required to build a voice prompt")
    return ff


def decode_mono(path: Path, sr: int = SR) -> Audio:
    cmd = [_ffmpeg(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
           "-f", "f32le", "-"]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed for {path}: {proc.stderr[-500:]!r}")
    return np.frombuffer(proc.stdout, dtype=np.float32)


def frame_db(audio: Audio, sr: int = SR) -> npt.NDArray[np.float64]:
    hop = int(sr * FRAME_S)
    n = len(audio) // hop
    frames = audio[: n * hop].reshape(n, hop)
    rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
    db: npt.NDArray[np.float64] = 20 * np.log10(rms)
    return db


def score_windows(audio: Audio, source: Path, length: float = PROMPT_S) -> list[Candidate]:
    """Score every window that begins at a speech onset."""
    db = frame_db(audio)
    if len(db) == 0:
        return []
    noise = float(np.percentile(db, 10))
    speech = db > noise + 15
    peaks = np.abs(audio)
    win = int(length / FRAME_S)
    out: list[Candidate] = []
    # start only at speech onsets so the clip begins on a word, not mid-syllable
    onsets = np.flatnonzero(speech[1:] & ~speech[:-1]) + 1
    for i in (int(o) for o in onsets if o + win <= len(db)):
        seg = speech[i : i + win]
        ratio = float(seg.mean())
        runs = np.diff(np.flatnonzero(np.diff(np.r_[1, seg.astype(int), 1]) != 0))[::2]
        longest_pause = float(runs.max() * FRAME_S) if len(runs) else 0.0
        a0, a1 = int(i * FRAME_S * SR), int((i + win) * FRAME_S * SR)
        clipped = float((peaks[a0:a1] > 0.98).mean())
        steadiness = float(np.std(db[i : i + win][seg])) if seg.any() else 99.0
        score = ratio - 0.08 * max(0.0, longest_pause - 0.4) - 0.02 * steadiness - 50 * clipped
        out.append(Candidate(source, i * FRAME_S, score, ratio, longest_pause))
    return out


def best_candidates(sources: list[Path], top: int = 3, length: float = PROMPT_S) -> list[Candidate]:
    """Top non-overlapping windows across all sources, best first."""
    scored: list[Candidate] = []
    for src in sources:
        scored.extend(score_windows(decode_mono(src), src, length))
    scored.sort(key=lambda c: c.score, reverse=True)
    picked: list[Candidate] = []
    for c in scored:
        if all(c.source != p.source or abs(c.start - p.start) >= length for p in picked):
            picked.append(c)
        if len(picked) == top:
            break
    return picked


def cut_clean(source: Path, start: float, dest: Path, length: float = PROMPT_S) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [_ffmpeg(), "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
           "-i", str(source), "-ac", "1", "-ar", str(SR), "-af", CLEAN_FILTER, str(dest)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg prompt cut failed: {proc.stderr[-500:]}")
    return dest
