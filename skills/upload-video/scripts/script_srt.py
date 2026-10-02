"""Exact-script captions for YouTube: projects/<id>/publish/captions.srt.

`transcript.srt` is Whisper's guess at the finished audio, so it repeats every mishearing
the voice check caught ("C++ fix", "an INC pointer"). This builds the caption track from the
script itself instead: `audio/words.json` (word timings aligned to the script, already shifted
by `cli.py pace`) placed at each voice clip's real start in `composition/index.html`.

    .venv/bin/python skills/upload-video/scripts/script_srt.py projects/<id>

Phonetic spellings in the script (G-lib-C, C-plus-plus) are mapped back by the same
`caption_word()` the on-screen captions use.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills" / "create-video" / "assets"))
from scenekit import caption_word  # noqa: E402

MAX_WORDS, MAX_CHARS, GAP = 9, 42, 0.6


def ts(t: float) -> str:
    ms = round(max(0.0, t) * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def clip_starts(index_html: str) -> dict[int, float]:
    starts: dict[int, float] = {}
    for tag in re.findall(r"<audio\b[^>]*>", index_html):
        n = re.search(r'id="voice-(\d+)"', tag)
        st = re.search(r'data-start="([\d.]+)"', tag)
        if n and st:
            starts[int(n.group(1))] = float(st.group(1))
    return starts


def cues(words: list[dict], offset: float) -> list[tuple[float, float, str]]:
    out: list[tuple[float, float, str]] = []
    cur: list[dict] = []

    def flush() -> None:
        if cur:
            text = " ".join(caption_word(w["text"]) for w in cur)
            out.append((offset + cur[0]["start"], offset + cur[-1]["end"], text))
            cur.clear()

    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        line = " ".join(caption_word(x["text"]) for x in cur)
        if (nxt is None or len(cur) >= MAX_WORDS or nxt["start"] - w["end"] > GAP
                or re.search(r"[.?!]$", w["text"])
                or len(line) + 1 + len(caption_word(nxt["text"])) > MAX_CHARS):
            flush()
    return out


def main(project: Path) -> Path:
    words = json.loads((project / "audio" / "words.json").read_text(encoding="utf-8"))
    html = (project / "composition" / "index.html").read_text(encoding="utf-8")
    starts = clip_starts(html)
    all_cues: list[tuple[float, float, str]] = []
    for slide in words["slides"]:
        n = int(slide["index"])
        if n not in starts:
            raise SystemExit(f"slide {n}: no <audio id=\"voice-{n:02d}\"> in index.html")
        all_cues += cues(slide["words"], starts[n])
    all_cues.sort()
    lines = []
    for i, (a, b, text) in enumerate(all_cues, start=1):
        nxt = all_cues[i][0] if i < len(all_cues) else b + 2
        end = min(b + 0.4, nxt - 0.05)  # hold briefly, never overlap the next cue
        lines.append(f"{i}\n{ts(a)} --> {ts(max(end, a + 0.5))}\n{text}\n")
    out = project / "publish" / "captions.srt"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(all_cues)} cues -> {out}")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: script_srt.py projects/<id>")
    main(Path(sys.argv[1]).resolve())
