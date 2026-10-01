"""Cut vertical Shorts (1080x1920) out of a finished long-form video.

Usage (from the repo root):
    .venv/bin/python skills/create-video/assets/build_shorts.py projects/<id> [--only 1,3] [--draft]

Reads projects/<id>/shorts.json:
    {"accent": "#5aa9f0", "shorts": [
      {"id": "short_01", "slides": [1, 2], "hook": ["Where do your", "bytes actually go?"]}
    ]}

For each short: finds the scenes' slots in composition/index.html (host ids `scene-NN` where NN is
the outline slide index), cuts that range from final.mp4 with ffmpeg (cropped to the diagram area,
leaving out the long-form captions), builds a portrait HyperFrames project in
projects/<id>/shorts/<short id>/ — hook title on top, diagram in the middle, big word-by-word
captions from audio/words.json, the channel wordmark (config.yaml `channel:`) at the
bottom, all inside the Shorts safe zones — and renders it to
projects/<id>/shorts/<short id>.mp4. Target 30-45s per short (hard max 60s).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scenekit import CHANNEL  # noqa: E402  (channel branding from config.yaml)
from scenekit import K as KIT  # noqa: E402

W, H = 1080, 1920
# region of the 1920x1080 long-form frame kept in the short: diagram + notes, not the captions
CROP = (90, 30, 1740, 910)  # x, y, w, h
CLIP_W = W
CLIP_H = round(CROP[3] * W / CROP[2] / 2) * 2
CLIP_Y = 500
INK, INK2, BG = "#e9eaec", "#9aa0a8", "#121417"
MAX_S = 60.0


def caption_word(word: str) -> str:
    word = word.replace("G-lib-C", "glibc").replace("J-E-malloc", "jemalloc")
    return re.sub(r"[Mm]ee-malloc", "mimalloc", word)


def scene_slots(index_html: str) -> dict[int, tuple[float, float]]:
    slots = {}
    for m in re.finditer(r'data-composition-id="scene-(\d+)"[^>]*?data-start="([\d.]+)"[^>]*?'
                         r'data-duration="([\d.]+)"', index_html):
        slots[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
    return slots


def chunks(words: list[dict]) -> list[list[dict]]:
    out, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        gap = nxt["start"] - w["end"] if nxt else 9.0
        if (nxt is None or len(cur) >= 4 or gap > 0.3 or re.search(r"[.?!]$", w["text"])
                or (re.search(r"[,:;]$", w["text"]) and len(cur) >= 2)):
            out.append(cur)
            cur = []
    return out


def run(cmd: list[str], cwd: Path | None = None) -> None:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd[:4])}…\n{(proc.stdout + proc.stderr)[-1500:]}")


def build(project: Path, spec: dict, accent: str, draft: bool) -> Path:
    sid = spec["id"]
    slots = scene_slots((project / "composition" / "index.html").read_text())
    words_doc = {int(s["index"]): s for s in
                 json.loads((project / "audio" / "words.json").read_text())["slides"]}
    start = slots[spec["slides"][0]][0]
    parts, t = [], 0.0
    for n in spec["slides"]:
        s0, d = slots[n]
        parts.append((n, t))
        t += d
    dur = t
    if dur > MAX_S:
        sys.exit(f"{sid}: {dur:.1f}s is over the {MAX_S:.0f}s Shorts limit — pick fewer scenes")

    out_dir = project / "shorts" / sid
    if not (out_dir / "hyperframes.json").exists():
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "HYPERFRAMES_SKIP_SKILLS": "1"}
        subprocess.run(["npx", "hyperframes", "init", sid, "--non-interactive",
                        "--resolution", "portrait"], cwd=out_dir.parent, env=env,
                       capture_output=True, check=True)
    assets = out_dir / "assets"
    assets.mkdir(exist_ok=True)
    x, y, cw, ch = CROP
    final = project / "final.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(final),
         "-vf", f"crop={cw}:{ch}:{x}:{y},scale={CLIP_W}:{CLIP_H}", "-an", "-c:v", "libx264",
         "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", str(assets / "clip.mp4")])
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(final),
         "-vn", "-c:a", "pcm_s16le", str(assets / "clip.wav")])

    caps, js = [], []
    timed = [(offset, ch) for n, offset in parts for ch in chunks(words_doc[n]["words"])]
    for c, (offset, chunk) in enumerate(timed):
        k = c
        spans = " ".join(f'<span id="w{c}_{j}" style="opacity:0.5">'
                         f'{html.escape(caption_word(w["text"]))}</span>'
                         for j, w in enumerate(chunk))
        caps.append(f'<div id="cap{c}" class="cap" style="opacity:0">{spans}</div>')
        a = offset + max(0.0, chunk[0]["start"] - 0.06)
        b = offset + chunk[-1]["end"] + 0.25
        if k + 1 < len(timed):  # never two caption chunks on screen at once
            nxt_off, nxt = timed[k + 1]
            b = min(b, nxt_off + max(0.0, nxt[0]["start"] - 0.06) - 0.01)
        js.append(f'tl.set("#cap{c}",{{opacity:1}},{a:.3f});tl.set("#cap{c}",{{opacity:0}},{b:.3f});')
        for j, w in enumerate(chunk):
            js.append(f'tl.set("#w{c}_{j}",{{opacity:1}},{offset + w["start"] - 0.02:.3f});')
    hook = "".join(f'<div>{html.escape(line)}</div>' for line in spec["hook"])
    brand = (f'{html.escape("".join(CHANNEL[:-1]))}<span>{html.escape(CHANNEL[-1])}</span>'
             "<span>_</span>")
    (out_dir / "index.html").write_text(f"""<!doctype html>
<html lang="en" data-resolution="portrait">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width={W}, height={H}">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:{BG}; }}
#root {{ position:relative; width:100%; height:100%; overflow:hidden; background:{BG};
  font-family:"Inter", sans-serif; color:{INK}; }}
#hook {{ position:absolute; left:90px; width:{W - 230}px; top:250px; text-align:center;
  font-size:76px; font-weight:800; line-height:1.08; letter-spacing:-0.01em; }}
#hook div:last-child {{ color:{accent}; }}
#clipbox {{ position:absolute; left:0; top:{CLIP_Y}px; width:{CLIP_W}px; height:{CLIP_H}px;
  overflow:hidden; border-top:2px solid #252930; border-bottom:2px solid #252930; }}
#clip {{ position:absolute; left:0; top:0; width:{CLIP_W}px; height:{CLIP_H}px; }}
.cap {{ position:absolute; left:90px; width:{W - 230}px; top:{CLIP_Y + CLIP_H + 70}px;
  text-align:center; font-size:66px; font-weight:800; line-height:1.15; }}
#brand {{ position:absolute; left:90px; width:{W - 230}px; top:1420px; text-align:center;
  font-size:42px; font-weight:800; }}
#brand span {{ color:{accent}; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="{W}" data-height="{H}"
  data-fps="30" data-duration="{dur:.3f}">
  <div id="hook">{hook}</div>
  <div id="clipbox">
    <video id="clip" src="assets/clip.mp4" data-start="0" data-duration="{dur:.3f}"
      data-track-index="0" muted playsinline></video>
  </div>
  {chr(10).join(caps)}
  <div id="brand">{brand}</div>
  <audio id="voice" src="assets/clip.wav" data-start="0" data-duration="{dur:.3f}"
    data-track-index="10" data-volume="1"></audio>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines["main"] = tl;
</script>
</body>
</html>
""")
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1"}
    check = subprocess.run(["npx", "hyperframes", "check"], cwd=out_dir, env=env,
                           capture_output=True, text=True)
    if check.returncode != 0:
        sys.exit(f"{sid}: hyperframes check failed\n{(check.stdout + check.stderr)[-2500:]}")
    target = project / "shorts" / f"{sid}.mp4"
    run(["npx", "hyperframes", "render", "--quality", "draft" if draft else "high",
         "--output", str(target.resolve())], cwd=out_dir)
    print(f"{sid}: {dur:.1f}s -> {target}")
    return target


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--only", default="")
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    spec = json.loads((a.project / "shorts.json").read_text())
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    for i, sh in enumerate(spec["shorts"], start=1):
        if only and str(i) not in only and sh["id"] not in only:
            continue
        build(a.project, sh, spec.get("accent", KIT["accent"]), a.draft)
    if shutil.which("ffprobe"):
        for sh in spec["shorts"]:
            f = a.project / "shorts" / f"{sh['id']}.mp4"
            if f.exists():
                d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "csv=p=0", str(f)], capture_output=True, text=True)
                print(f"  {f.name}: {float(d.stdout or 0):.1f}s")


if __name__ == "__main__":
    main()
