"""Scaffold a Short's HyperFrames composition in one step.

    .venv/bin/python skills/create-short/scripts/scaffold.py projects/<id> [--format landscape]

Needs outline.json and the voice stage's audio (slide_XX.mp3, durations.json, words.json).
Creates projects/<id>/composition/ (HyperFrames init, portrait by default), copies the house
style and narration in, and writes build.py from the template (never overwrites an existing
build.py). Re-run it after regenerating the voice to refresh the audio copies.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


def repo_root(start: Path) -> Path:
    for base in (start, *start.parents):
        if (base / "skills" / "create-video" / "assets" / "scenekit.py").exists():
            return base
    sys.exit("Run this inside the yt-setup repo "
             "(skills/create-video/assets/scenekit.py not found).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("project", type=Path)
    ap.add_argument("--format", choices=["portrait", "landscape"], default="portrait")
    a = ap.parse_args()
    project = a.project.resolve()
    repo = repo_root(project)
    need = [project / "outline.json", project / "audio" / "durations.json",
            project / "audio" / "words.json"]
    missing = [str(p.relative_to(project)) for p in need if not p.exists()]
    if missing:
        sys.exit(f"missing {missing}: run `cli.py run --project <id> --only voice` "
                 "(or `cli.py voice-import`) first")

    comp = project / "composition"
    if not (comp / "hyperframes.json").exists():
        env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "HYPERFRAMES_SKIP_SKILLS": "1"}
        proc = subprocess.run(["npx", "hyperframes", "init", "composition", "--non-interactive",
                               "--resolution", a.format], cwd=project, env=env,
                              capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit(f"hyperframes init failed (Node 22+? `npx hyperframes doctor`):\n"
                     f"{(proc.stdout + proc.stderr)[-1500:]}")
    (comp / "assets" / "voice").mkdir(parents=True, exist_ok=True)
    (comp / "compositions").mkdir(exist_ok=True)
    shutil.copy2(repo / "skills" / "create-video" / "assets" / "house.css",
                 comp / "assets" / "house.css")
    voices = sorted((project / "audio").glob("slide_*.mp3"))
    for mp3 in voices:
        shutil.copy2(mp3, comp / "assets" / "voice" / mp3.name)

    build = comp / "build.py"
    if build.exists():
        note = "kept existing build.py"
    else:
        title = json.loads((project / "outline.json").read_text())["title"]
        text = (SKILL / "templates" / "build.py").read_text().replace(
            "__TITLE__", title.replace('"', "'"))
        if a.format == "landscape":
            text = text.replace('set_layout("portrait")', 'set_layout("landscape")')
        build.write_text(text)
        note = "wrote build.py from the template (rough cut until you add real scenes)"
    print(f"composition ready: {comp}\n  {len(voices)} narration file(s) copied; {note}\n"
          f"next: cli.py cues --project {project.name}  ·  "
          f"cd {comp} && ../../../.venv/bin/python build.py && npx hyperframes check")


if __name__ == "__main__":
    main()
