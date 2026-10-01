"""Word-level timing for narration: ASR words aligned back onto the exact script words.

The script is known, so ASR is only used for *timing*. Every script word gets a start/end;
words ASR missed are interpolated between their matched neighbours. Output feeds captions
and word-anchored animation cues (see modules/voice/cues.py).
"""

from __future__ import annotations

import difflib
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.logging_setup import get_logger

log = get_logger(__name__)


def narration_asr_model() -> str:
    """Whisper size for narration checks/timing. `base` mishears accented speech and jargon
    ("Rust" -> "rest") and triggers false retakes; `medium` is accurate and still fast
    relative to TTS."""
    return os.getenv("YT_STUDIO_VOICE_ASR_MODEL", "medium")


def norm(word: str) -> str:
    return re.sub(r"[^a-z0-9]", "", word.lower())


def script_words(text: str) -> list[str]:
    return re.findall(r"\S+", text.replace("—", " ").replace("–", " "))


_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
    "nineteen",
]
_TENS = ["_", "_", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def number_words(n: int) -> list[str]:
    """0-9999 as spoken words ("24" -> ["twenty", "four"]); ASR writes numbers as digits."""
    if n < 20:
        return [_ONES[n]]
    if n < 100:
        return [_TENS[n // 10]] + ([_ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [_ONES[n // 100], "hundred"] + (number_words(n % 100) if n % 100 else [])
    return number_words(n // 1000) + ["thousand"] + (number_words(n % 1000) if n % 1000 else [])


def expand_numbers(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for w in words:
        digits = re.fullmatch(r"\W*(\d{1,4})\W*", w["text"])
        if not digits:
            out.append(w)
            continue
        spoken = number_words(int(digits.group(1)))
        step = (w["end"] - w["start"]) / len(spoken)
        out.extend(
            {"text": t, "start": w["start"] + k * step, "end": w["start"] + (k + 1) * step}
            for k, t in enumerate(spoken)
        )
    return out


@lru_cache(maxsize=2)
def _model(size: str) -> Any:
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]

    return WhisperModel(size, device="cpu", compute_type="int8")


def asr_words(
    audio: Path, model_size: str | None = None, language: str = "en"
) -> list[dict[str, Any]]:
    segments, _ = _model(model_size or narration_asr_model()).transcribe(
        str(audio), language=language, word_timestamps=True, vad_filter=False, beam_size=5
    )
    return expand_numbers([
        {"text": w.word.strip(), "start": float(w.start), "end": float(w.end)}
        for seg in segments
        for w in (seg.words or [])
    ])


def similarity(expected: str, heard: list[dict[str, Any]]) -> float:
    """Token-level similarity between the script and what ASR heard (1.0 = identical)."""
    a = [norm(w) for w in script_words(expected) if norm(w)]
    b = [norm(w["text"]) for w in heard if norm(w["text"])]
    if not a:
        return 1.0
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def align(text: str, heard: list[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    """Map each script word to a time span using ASR word timings."""
    words = script_words(text)
    keys = [norm(w) for w in words]
    heard_keys = [norm(h["text"]) for h in heard]
    times: list[tuple[float, float] | None] = [None] * len(words)
    sm = difflib.SequenceMatcher(a=keys, b=heard_keys, autojunk=False)
    for block in sm.get_matching_blocks():
        for k in range(block.size):
            h = heard[block.b + k]
            times[block.a + k] = (h["start"], h["end"])
    # interpolate gaps between matched anchors
    known = [i for i, t in enumerate(times) if t is not None]
    for i, t in enumerate(times):
        if t is not None:
            continue
        prev = max((k for k in known if k < i), default=None)
        nxt = min((k for k in known if k > i), default=None)
        lo = times[prev][1] if prev is not None else 0.0  # type: ignore[index]
        hi = times[nxt][0] if nxt is not None else duration  # type: ignore[index]
        span_start = prev if prev is not None else -1
        span_end = nxt if nxt is not None else len(words)
        n = span_end - span_start - 1
        step = max(0.0, hi - lo) / max(1, n)
        pos = i - span_start - 1
        times[i] = (lo + pos * step, lo + (pos + 1) * step)
    return [
        {"i": i, "text": w, "start": round(t[0], 3), "end": round(t[1], 3)}  # type: ignore[index]
        for i, (w, t) in enumerate(zip(words, times, strict=True))
    ]


def estimate(text: str, duration: float) -> list[dict[str, Any]]:
    """Even spread — for stub/silent narration where there is nothing to hear."""
    return align(text, [], duration)
