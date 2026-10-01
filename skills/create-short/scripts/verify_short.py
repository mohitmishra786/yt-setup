"""Final gate for a rendered Short, plus snapshot times for reviewing the composition.

    .venv/bin/python skills/create-short/scripts/verify_short.py projects/<id>
        -> checks final.mp4
    .venv/bin/python skills/create-short/scripts/verify_short.py projects/<id> --times
        -> snapshot times

Checks final.mp4: 1080x1920 (or the composition's size), 30fps, length (30-45s ideal, hard
max 60s), narration loudness, poster present. Writes projects/<id>/qa/contact.png (8 frames)
to look at. `--times` prints the times to pass to `npx hyperframes snapshot --at`: 0.6s into
every scene (nothing should be blank) and 0.9s after every cue (each beat should be visible).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def snapshot_times(project: Path) -> list[float]:
    index = (project / "composition" / "index.html").read_text()
    starts = {int(m.group(1)): float(m.group(2)) for m in
              re.finditer(r'id="scene-(\d+)"[^>]*data-start="([\d.]+)"', index)}
    cues_file = project / "cues.json"
    cues = json.loads(cues_file.read_text()) if cues_file.exists() else {}
    times = [t + 0.6 for t in starts.values()]
    times += [starts[c["slide"]] + c["t"] + 0.9 for c in cues.values() if c["slide"] in starts]
    return sorted(round(t, 2) for t in times)


def verify(project: Path) -> int:
    final = project / "final.mp4"
    if not final.exists():
        print(f"✗ {final} missing — render with `cli.py run --project <id> --only hyperframes`")
        return 1
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
         str(final)], capture_output=True, text=True, check=True).stdout)
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in probe["streams"])
    dur = float(probe["format"]["duration"])
    w, h = int(video["width"]), int(video["height"])
    num, den = (int(x) for x in video["r_frame_rate"].split("/"))
    fps = num / den
    lufs_out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(final), "-af", "ebur128",
                               "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", lufs_out)
    lufs = float(m[-1]) if m else float("nan")

    problems, warnings = [], []
    if dur > 60.0:
        problems.append(f"{dur:.1f}s is over the 60s Shorts limit")
    elif not 30.0 <= dur <= 45.0:
        warnings.append(f"{dur:.1f}s is outside the 30–45s sweet spot")
    if (w, h) != (1080, 1920):
        warnings.append(f"{w}x{h} (not vertical 1080x1920)")
    if abs(fps - 30) > 0.01:
        warnings.append(f"{fps:.2f} fps (expected 30)")
    if not has_audio:
        problems.append("no audio stream")
    if not -18.0 <= lufs <= -12.0:
        warnings.append(f"loudness {lufs:.1f} LUFS (expected about -16 to -13)")
    if not (project / "poster.jpg").exists():
        warnings.append("no poster.jpg — set poster.json (title card, ~0.9s) and re-render")

    qa = project / "qa"
    qa.mkdir(exist_ok=True)
    step = max(dur / 8, 0.5)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-vf",
                    f"fps=1/{step:.3f},scale=270:-1,tile=8x1", "-frames:v", "1", "-update", "1",
                    str(qa / "contact.png")], check=False)

    print(f"final.mp4: {dur:.1f}s · {w}x{h} · {fps:.0f}fps · {lufs:.1f} LUFS · "
          f"audio={'yes' if has_audio else 'NO'}")
    for p in problems:
        print(f"  ✗ {p}")
    for wmsg in warnings:
        print(f"  ! {wmsg}")
    print(f"  contact sheet: {qa / 'contact.png'} — look at it before publishing")
    return 1 if problems else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("project", type=Path)
    ap.add_argument("--times", action="store_true", help="print snapshot times and exit")
    a = ap.parse_args()
    if a.times:
        print(",".join(f"{t:.2f}" for t in snapshot_times(a.project)))
        return
    sys.exit(verify(a.project))


if __name__ == "__main__":
    main()
