"""Chatterbox (Resemble AI) — MIT local voice cloning.

Narration quality comes from four things, all handled here:
1. A clean ~10s prompt (Chatterbox only conditions on the first 10s of its reference) —
   see modules/voice/reference.py and `python cli.py voice-prompt`.
2. Sentence-sized generation: long inputs drift and garble, so text is split into
   sentences, each generated with a fixed seed against conditionals prepared once.
3. ASR verification: each sentence is transcribed and regenerated (new seed) when it does
   not match the script; the best take is kept.
4. Mastering: edge-silence trim, natural inter-sentence pauses, then high-pass, de-ess,
   gentle compression and loudness normalisation to -16 LUFS.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import zlib
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from core.logging_setup import get_logger

from modules.voice.engine import VoiceEngine, VoiceEngineError, convert_to_mp3
from modules.voice.profile import get_profile, validate_profile_for_cloning

log = get_logger(__name__)

Audio = npt.NDArray[np.float32]

MASTER_FILTER = (
    "highpass=f=70,deesser=i=0.35,"
    "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80:makeup=2,"
    "loudnorm=I=-16:TP=-1.5:LRA=9"
)
MAX_CHUNK_CHARS = 220
GOOD_MATCH = 0.9


def good_enough(text: str, score: float) -> bool:
    """Pass at 0.9, or when the miss is about two words (ASR slips on jargon in short sentences)."""
    n = max(1, len(text.split()))
    return score >= min(GOOD_MATCH, 1 - 2 / n)


def split_sentences(text: str) -> list[str]:
    """Sentence chunks; over-long sentences split at a comma near the middle."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
    chunks: list[str] = []
    for p in parts:
        while len(p) > MAX_CHUNK_CHARS:
            commas = [m.end() for m in re.finditer(r"[,;:]\s", p)]
            if not commas:
                break
            cut = min(commas, key=lambda c: abs(c - len(p) / 2))
            chunks.append(p[:cut].strip())
            p = p[cut:].strip()
        chunks.append(p)
    merged: list[str] = []
    carry = ""
    for c in chunks:
        c = f"{carry} {c}".strip()
        carry = ""
        if len(c) < 12:
            if merged:
                merged[-1] = f"{merged[-1]} {c}"
            else:
                carry = c
            continue
        merged.append(c)
    if carry:
        merged.append(carry)
    return merged


def pause_after(chunk: str) -> float:
    end = chunk.rstrip()[-1:]
    if end in "?!":
        return 0.38
    if end == ".":
        return 0.32
    return 0.16


def trim_edges(wav: Audio, sr: int, floor_db: float = 40.0, pad_s: float = 0.04) -> Audio:
    hop = max(1, int(sr * 0.01))
    n = len(wav) // hop
    if n == 0:
        return wav
    rms = np.sqrt(np.mean(wav[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    loud = np.flatnonzero(db > db.max() - floor_db)
    if len(loud) == 0:
        return wav
    pad = int(pad_s * sr)
    lo, hi = max(0, loud[0] * hop - pad), min(len(wav), (loud[-1] + 1) * hop + pad)
    trimmed: Audio = wav[lo:hi]
    return trimmed


class ChatterboxEngine(VoiceEngine):
    """Production voice backend using Resemble AI Chatterbox (MIT)."""

    name = "chatterbox"

    def __init__(
        self, *, exaggeration: float | None = None, cfg_weight: float | None = None
    ) -> None:
        import importlib.util

        if (
            importlib.util.find_spec("chatterbox") is None
            and importlib.util.find_spec("chatterbox_tts") is None
        ):
            raise ImportError(
                "chatterbox package not installed.\n"
                "  uv pip install --python .venv/bin/python chatterbox-tts\n"
                "See docs/VOICE_CLONING.md"
            )
        self._model: Any = None
        self._device: str | None = None
        self._cond_ref: Path | None = None
        self.exaggeration = 0.5 if exaggeration is None else exaggeration
        self.cfg_weight = 0.5 if cfg_weight is None else cfg_weight
        self.seed = int(os.getenv("YT_STUDIO_VOICE_SEED", "7"))
        self.verify = os.getenv("YT_STUDIO_VOICE_VERIFY", "1") != "0"
        self.tries = max(1, int(os.getenv("YT_STUDIO_VOICE_TRIES", "3")))

    def _resolve_device(self) -> str:
        forced = os.getenv("YT_STUDIO_VOICE_DEVICE")
        if forced:
            return forced
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            # No MPS by default: on Apple Silicon Chatterbox's sampler starts ~20 it/s on MPS
            # but collapses to 1-3 s/it after ~100 steps (a 3-min script took 12h); CPU holds a
            # steady ~12 it/s (~4x real time). Opt in with YT_STUDIO_VOICE_DEVICE=mps.
        except Exception:  # noqa: BLE001
            pass
        return "cpu"

    def warmup(self) -> None:
        if self._model is not None:
            return
        self._device = self._resolve_device()
        log.info("Loading Chatterbox model on device=%s", self._device)
        try:
            from chatterbox.tts import ChatterboxTTS  # type: ignore[import-untyped]

            self._model = ChatterboxTTS.from_pretrained(device=self._device)
        except Exception as exc:  # noqa: BLE001
            raise VoiceEngineError(
                f"Failed to load Chatterbox on {self._device}: {exc}"
            ) from exc

    def _condition(self, ref: Path) -> None:
        if self._cond_ref == ref:
            return
        self._model.prepare_conditionals(str(ref), exaggeration=self.exaggeration)
        self._cond_ref = ref

    def _take(self, text: str, seed: int) -> Audio:
        import torch

        torch.manual_seed(seed)
        wav = self._model.generate(
            text, exaggeration=self.exaggeration, cfg_weight=self.cfg_weight
        )
        arr: Audio = wav.detach().cpu().numpy().squeeze().astype(np.float32)
        return trim_edges(arr, self._model.sr)

    def _best_take(self, text: str, seed: int, tmp: Path) -> Audio:
        import soundfile as sf  # type: ignore[import-untyped]

        from modules.voice.words import asr_words, similarity

        best: tuple[float, Audio] | None = None
        for attempt in range(self.tries):
            arr = self._take(text, seed + attempt)
            if not self.verify:
                return arr
            sf.write(str(tmp), arr, self._model.sr)
            score = similarity(text, asr_words(tmp))
            if best is None or score > best[0]:
                best = (score, arr)
            if good_enough(text, score):
                break
            log.info("retake (match %.2f): %s", score, text[:60])
        assert best is not None
        if best[0] < 0.8:
            log.warning("best take still mismatches script (%.2f): %s", best[0], text)
        return best[1]

    def synthesize(self, text: str, voice_id: str, output_path: Path) -> Path:
        import soundfile as sf

        self.warmup()
        profile = get_profile(voice_id)
        for w in validate_profile_for_cloning(profile):
            log.warning("voice profile: %s", w)
        ref = profile.resolve_reference()
        self._condition(ref)
        chunks = split_sentences(text or " ") or [" "]
        log.info(
            "Chatterbox clone voice_id=%s ref=%s sentences=%d", voice_id, ref.name, len(chunks)
        )

        sr = self._model.sr
        pieces: list[Audio] = [np.zeros(int(0.06 * sr), dtype=np.float32)]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "take.wav"
            base = self.seed + (zlib.crc32(text.encode()) % 997) * 10
            for n, chunk in enumerate(chunks):
                pieces.append(self._best_take(chunk, base + n * 100, tmp))
                gap = pause_after(chunk) if n < len(chunks) - 1 else 0.15
                pieces.append(np.zeros(int(gap * sr), dtype=np.float32))
            raw = Path(td) / "raw.wav"
            sf.write(str(raw), np.concatenate(pieces), sr)
            mastered = Path(td) / "mastered.wav"
            master(raw, mastered, sr)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.suffix.lower() == ".mp3":
                convert_to_mp3(mastered, output_path, sample_rate=sr)
            else:
                shutil.copy2(mastered, output_path)
        return output_path


def master(src: Path, dest: Path, sr: int) -> Path:
    ff = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [ff, "-v", "error", "-y", "-i", str(src), "-af", MASTER_FILTER, "-ar", str(sr), str(dest)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise VoiceEngineError(f"ffmpeg mastering failed: {proc.stderr[-800:]}")
    return dest
