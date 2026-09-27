---
name: create-video
description: Produce an authentic, 8-15 minute long-form technical/CS explainer video with minimalist CoreDumpped/3Blue1Brown-style diagram animation, local voice cloning, and YouTube-ready packaging. Use when someone says "/create-video", "create a video on X", "make an explainer video about X", or wants to produce an end-to-end technical YouTube video.
---

# /create-video

You produce an end-to-end, high-quality technical/CS explainer video (8–15 minutes) with minimalist diagram animations, cloned narration, and YouTube-ready packaging.

Unlike default AI video tools that generate bullet-point slides, this pipeline produces **clean, hand-crafted CoreDumpped / 3Blue1Brown-style diagram animations**: labeled boxes, directional arrows, memory layouts, execution queues, and state transitions.

You run this directly using the repository's modules, tools, and shell commands. No external LLM API key is required when running as an agent — **you act as the director, scene coder, and reviewer yourself**.

---

## Creative Laws for Technical Explainers

- **One Idea Revealed at a Time**: Never show a complete complex diagram all at once. Elements enter sequentially (staggered by 1.5–2.5s).
- **Hold for Readability**: After an element enters or transitions, pause for 1.5–3.0 seconds before introducing the next element. Pacing is the clarity.
- **State Transitions over Slide Cuts**: Animate state changes (e.g. moving a task from Ready to Running, drawing a connector packet, invalidating a cache line) instead of abruptly cutting to a new screen.
- **Text is a Caption, Not the Content**: Spoken narration carries the explanation. On-screen text is limited to crisp labels, addresses, or short badges.
- **Palette Discipline**: Canvas background is deep matte slate (`#0f141c`). Shape fills are neutral (`#1b2230`, `#273248`). Only ONE accent color is live at a time (`#38bdf8` cyan, `#f43f5e` rose, or `#34d399` emerald) to track active focus.
- **Every Frame Postable**: Any frozen frame should look like a clean, publication-grade technical diagram.

---

## Step-by-Step Production Workflow

### Step 1: Project Initialization

1. Create a project id from the topic and date:
   ```bash
   python cli.py new-id "<topic>"
   ```
2. Initialize the project directory under `projects/<project_id>/` with state checkpoint:
   ```bash
   python cli.py run --topic "<topic>" --only scriptwriter
   ```
   Or create the project folder structure directly:
   `projects/<project_id>/scenes`, `projects/<project_id>/audio`, `projects/<project_id>/logs`.

### Step 2: Narrative Scriptwriting (Outline + SEO)

Write `projects/<project_id>/outline.json` matching `core/schemas.py:SlideOutline`:
- 8–16 logical beats for an 8–12 minute explainer.
- Each slide contains:
  - `title`: Mental model milestone.
  - `speaker_notes`: Spoken conversational narration (45–75 seconds when spoken aloud).
  - `visual_beat`: Specific diagram description (what is ON SCREEN: boxes, arrows, queues, memory cells).
  - `bullets`: Short scannable reference points (optional 2-4 items).

Write `projects/<project_id>/seo.json` matching `core/schemas.py:SEOMetadata` (title, description, tags, chapters).

### Step 3: Visual Storyboarding (Choreography)

Write `projects/<project_id>/storyboard.json` matching `core/schemas.py:Storyboard`:
- Map each outline slide to an animated `StoryboardBeat`.
- Assign semantic `VisualElement` entries (`box`, `arrow`, `queue`, `timeline`, `grid`).
- Assign timed `VisualAction` sequences (`enter`, `draw`, `highlight`, `move`) adhering to the 1.5–2.5s stagger rule and 2.0s hold rule.

### Step 4: Scene Rendering

Render each beat to `projects/<project_id>/scenes/scene_XX.html` and `scene_XX.mp4`:
- Compose using `modules/scenegen/tokens.py` and `modules/scenegen/components/`.
- Run the scene generator:
  ```bash
  python cli.py run --project <project_id> --only scenegen
  ```
- Each scene is checkpointed independently. If scene 4 needs adjustment, edit `scene_04.html` and re-render only that scene with `--force`.

### Step 5: Narration Audio Synthesis

Synthesize voice audio using the Chatterbox engine or configured voice profile:
```bash
python cli.py run --project <project_id> --only voice
```
This produces `audio/slide_01.mp3`, `audio/slide_02.mp3`, ... and `audio/durations.json`.

### Step 6: Visual QA Verification

Run the automated Visual QA suite:
```bash
.venv/bin/python -c "
from core.project import Project
from core.config import load_config
from modules.scenegen.qa import validate_storyboard_qa
from core.schemas import Storyboard
import json
from pathlib import Path

cfg = load_config()
proj = Project.load(cfg, '<project_id>')
with open(proj.paths.root / 'storyboard.json') as f:
    sb = Storyboard.model_validate(json.load(f))
results = validate_storyboard_qa(sb, scenes_dir=proj.paths.root / 'scenes', raise_on_failure=True)
print('QA Passed: All', len(results), 'scenes compliant with design tokens and pacing laws.')
"
```

### Step 7: Assembly & Muxing

Concatenate all scenes and mux with narration:
```bash
python cli.py run --project <project_id> --only video_assembler
```
If a scene animation completes before narration finishes, the video assembler automatically freezes the final frame so the completed diagram stays on screen while the speaker finishes explaining.

### Step 8: Downstream Deliverables

Run downstream transcription, chapters, and Shorts:
```bash
python cli.py run --project <project_id> --from-stage transcriber
```
Deliverables produced in `projects/<project_id>/`:
- `final.mp4` (Full assembled video)
- `chapters.txt` (YouTube timestamps)
- `transcript.srt` & `transcript.json`
- `shorts/short_01.mp4` (Auto-extracted Shorts)
- `publish_manifest.json`
