"""Give narration room to breathe without regenerating it.

Inserts extra silence at every sentence break (found from audio/words.json), then rewrites
the slide audio, words.json and durations.json with the shifted timings — so captions and
word-anchored cues stay in sync. The unpaced originals live in audio/unpaced/ and are always
the input, so pacing is idempotent; a slide whose narration was regenerated (its .key changed)
is picked up fresh.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from core.project import Project

from modules.voice.engine import convert_to_mp3, probe_audio_duration
from modules.voice.reference import Audio, decode_mono

SR = 24000
SENTENCE_END = re.compile(r"[.!?][\"')\]]*$")


def sentence_breaks(words: list[dict[str, Any]]) -> list[tuple[int, float]]:
    """(index of first word after the break, cut time in the silence between sentences)."""
    out = []
    for i in range(len(words) - 1):
        if SENTENCE_END.search(words[i]["text"]):
            cut = (float(words[i]["end"]) + float(words[i + 1]["start"])) / 2
            out.append((i + 1, cut))
    return out


def pace_words(
    words: list[dict[str, Any]], gap: float
) -> tuple[list[dict[str, Any]], list[float]]:
    """Shift word timings for `gap` seconds of silence at each break; returns (words, cuts)."""
    breaks = sentence_breaks(words)
    shifted = []
    for w in words:
        extra = gap * sum(1 for first, _ in breaks if w["i"] >= first)
        start, end = round(w["start"] + extra, 3), round(w["end"] + extra, 3)
        shifted.append({**w, "start": start, "end": end})
    return shifted, [cut for _, cut in breaks]


def insert_silence(audio: Audio, cuts: list[float], gap: float, sr: int = SR) -> Audio:
    pieces: list[Audio] = []
    prev = 0
    silence = np.zeros(int(round(gap * sr)), dtype=np.float32)
    for cut in cuts:
        at = int(round(cut * sr))
        pieces += [audio[prev:at], silence]
        prev = at
    pieces.append(audio[prev:])
    out: Audio = np.concatenate(pieces).astype(np.float32)
    return out


def pace_project(project: Project, gap: float) -> dict[str, Any]:
    import soundfile as sf  # type: ignore[import-untyped]

    audio_dir = project.paths.audio_dir
    words_path = audio_dir / "words.json"
    if not words_path.exists():
        raise FileNotFoundError(f"{words_path} missing — run the voice stage first")
    doc = json.loads(words_path.read_text(encoding="utf-8"))
    raw_dir = audio_dir / "unpaced"
    raw_dir.mkdir(exist_ok=True)

    offset = 0.0
    durations: list[float] = []
    slides_out = []
    for slide in doc["slides"]:
        idx = int(slide["index"])
        cur = project.paths.audio_for_slide(idx)
        key = cur.with_suffix(".key")
        raw, raw_key, raw_words = (raw_dir / cur.name, raw_dir / key.name,
                                   raw_dir / f"{cur.stem}.words.json")
        current_key = key.read_text() if key.exists() else ""
        if not raw.exists() or not raw_key.exists() or raw_key.read_text() != current_key:
            shutil.copy2(cur, raw)
            raw_key.write_text(current_key)
            raw_words.write_text(json.dumps(slide["words"]), encoding="utf-8")
        base_words = json.loads(raw_words.read_text(encoding="utf-8"))
        words, cuts = pace_words(base_words, gap)
        paced = insert_silence(decode_mono(raw, SR), cuts, gap)
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "paced.wav"
            sf.write(str(wav), paced, SR)
            convert_to_mp3(wav, cur, sample_rate=SR)
        dur = probe_audio_duration(cur)
        slides_out.append({**slide, "offset": round(offset, 3), "duration": round(dur, 3),
                           "words": words})
        durations.append(dur)
        offset += dur

    words_path.write_text(
        json.dumps({"slides": slides_out, "paced_gap": gap}, indent=2) + "\n", encoding="utf-8"
    )
    dpath = audio_dir / "durations.json"
    meta = json.loads(dpath.read_text(encoding="utf-8")) if dpath.exists() else {}
    meta.update({"durations": durations, "paced_gap": gap})
    dpath.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {"slides": len(slides_out), "total": round(offset, 2), "gap": gap}
