# Compose: hand off to HyperFrames

This repo owns the **story** (script, storyboard, tone, what real material to show, audio
intent, delivery). HyperFrames owns the **implementation** (composition structure, exact
animation timing, runtime choice, lint/check, render). Do not hand-roll a renderer, and do
not use the legacy `storyboard` / `scenegen` / `video_assembler` stages for these videos.

## Load the HyperFrames domain skills

Read: `hyperframes-core` (composition contract, `data-*` timing, sub-compositions),
`hyperframes-animation` (motion rules, blueprints, GSAP), `hyperframes-creative`
(design spec, beats), `hyperframes-keyframes` (camera moves, SVG draw/morph, masks),
`hyperframes-registry` (search blocks before building anything named), `hyperframes-cli`
(lint / check / snapshot / render), and `media-use` for captions, music and SFX.

This workflow is its own route: **do not** enter the `hyperframes` entry-point intent
interview or its generic `/faceless-explainer` / promo workflow — the plan already exists.

Not on Claude Code? Install the HyperFrames skills for your agent once with
`npx hyperframes skills` (writes to `~/.agents/skills`), or read them from
<https://github.com/heygen-com/hyperframes>.

## Scaffold

```bash
cd projects/<id>
HYPERFRAMES_NO_TELEMETRY=1 npx hyperframes init composition --non-interactive \
  --resolution portrait      # shorts; use `landscape` for long-form
mkdir -p composition/assets/voice
cp audio/slide_*.mp3 composition/assets/voice/
```

Assets must live inside `composition/` and be referenced by relative path
(`assets/voice/slide_01.mp3`). Absolute `/Users/...` paths silently fail at render time.

## House style

```bash
cp ../../../skills/create-video/assets/house.css assets/house.css   # from projects/<id>/composition
```

Link `assets/house.css` from every scene and build with its classes (`.stage`, `.box`,
`.cells/.cell`, `.arrow`, `.code .ln`, `.addr`, `.caption`). Set `--accent` once in
`index.html` if the plan picked a different accent. Do not add colors, gradients, glows,
shadows, or new fonts in scenes — if something seems to need them, the layout is wrong.

## Timing: words and cues (the sync contract)

The voice stage wrote `audio/words.json` — every script word with its start/end per slide
(aligned to the exact script, so it is also the caption source). The plan step wrote
`anchors.json`, and `cli.py cues` resolved it to `projects/<id>/cues.json`:

```json
{"s1_free": {"slide": 1, "t": 2.41, "abs": 2.41, "at": "free"}}
```

- `t` is seconds from the start of that slide's narration. Each scene is a
  sub-composition whose voice clip starts at the scene's start, so **`t` is the scene's
  local time** — use it directly on the scene timeline.
- **Embed the values at build time** (write them into each scene's script as a
  `const CUE = {...}` literal, or generate scenes from a small build script that reads
  `cues.json`). Never `fetch()` at render time, and never type times by hand.
- A beat's motion *starts* at its cue (entrances ~0.4–0.6s). For something that must be
  fully visible as the word is said, use `offset: -0.3` in the anchor.
- Changed the script or re-ran voice? Re-run `cli.py cues` and rebuild — times move.

Captions (shorts default, long-form with `--captions`): build from `audio/words.json` (not
raw ASR), 2–4 words per chunk, styled with `.caption` — white, spoken word full opacity.

## Scene kit (use it — don't hand-roll a builder)

`skills/create-video/assets/scenekit.py` is the tested engine behind every video made with this repo.
Write `composition/build.py` that imports it and describes each scene:

```python
sys.path.insert(0, "<repo>/skills/create-video/assets")
from scenekit import K, Scene, set_layout, title_card, outro, write_index
set_layout("landscape")           # or "portrait" for Shorts
s = Scene(1, cues)                # scene-01 <-> outline slide 1; beats via s.T("cue_id")
s.box(...); s.panel(...); s.arrow(...); s.show("x", "s1_free"); s.state("x", "free", "s1_free")
s.add_notes(None, [(0.0, "…"), ("s1_free", "…")]); s.add_captions(words[1])   # no section label
write_index(HERE, [(title_card(cues, TITLE, 2.6), 2.6, None, 0), (s, dur + PAD, 1, dur), …], TITLE)
```

It handles:
- cue-timed motion, with position moves converted to transforms
- arrows that stay invisible until drawn
- code/terminal panels with per-line highlight
- notes, captions, the title card, the outro and the index/audio wiring

Examples:
- `projects/2026-09-28_memory-allocators-how-malloc-and-free-work/composition/build.py`
  (landscape; an earlier inline copy of the kit)
- `projects/2026-09-28_rust-vs-c-memory-safety/composition/build.py` (portrait, on the kit)

## Composition layout

```
composition/
  index.html                 # root: canvas size, scene sequence, voice + captions + music tracks
  compositions/scene-01.html # one sub-composition per outline slide (templated)
  compositions/scene-02.html
  assets/voice/slide_XX.mp3  # copied from ../audio
  assets/house.css           # house style (copied from skills/create-video/assets)
```

- **One sub-composition per scene** (= per outline slide = per `audio/slide_XX.mp3`).
  Scene N starts where scene N−1 ends; its duration is at least `durations[N-1]` from
  `audio/durations.json` plus any planned silent hold. Let the voice set the pace — never
  cut narration short to fit an animation.
- Voice clips go on their own track **exactly at the scene's start time** (cue times
  assume this). No music unless the user asked for it (see creative-laws → Audio).
- Transitions are morphs: the last state of scene N equals the first state of scene N+1
  (same actors, same positions), so the cut is invisible. Build a shared `cast` snippet so
  actors look identical across scenes.
- Long-form: group scenes into chapters as described in `long-form.md`.
- To inspect what is on the timeline, use `npx hyperframes timeline --json`, not by
  re-reading every file.

## Write the composition brief first

Write `projects/<id>/composition-brief.md` (≤ 1 page) and give it to yourself (or a
sub-agent) as the contract before writing HTML:

```markdown
# Composition Brief: [title]
- Output: projects/<id>/composition/ → projects/<id>/final.mp4
- Canvas: [1080x1920 | 1920x1080] @ 30fps — Duration: [s]
- Tone: [preset + direction + interpretation]
- Visual identity: assets/house.css; accent [hex]; no other colors, no glows
- Cast (persistent actors) and their states: [from video-plan.md]
- Cue times: projects/<id>/cues.json (embed at build time)
- Real material that must appear verbatim: [code snippets, error text, numbers + source]
- Scene summary: 1. [name] [start→end] [what must be seen / read] …
- Audio: voice track (assets/voice), captions, music [mood/none], SFX posture
- Must: pass `npx hyperframes check`; all text meets the size minimums and reading holds;
  vertical safe zones respected; every beat lands on its cue.
```

## Build

- **Search the registry before hand-building any named visual** — code window, terminal,
  syntax-highlighted typing, chart, flow diagram, highlight sweep, callout:
  `npx hyperframes catalog --query "<the move in plain English>"`. Install with
  `npx hyperframes add <name>`. Hand-build only when nothing fits.
- Build scene by scene. After each scene: `npx hyperframes lint`, then
  `npx hyperframes snapshot --at <3–4 times inside that scene>` and **look at the PNGs**.
  Fix overflow, collisions, arrows crossing labels, small text, empty frame areas, and
  low contrast before moving on.
- Also snapshot mid-transition between scenes — a crossfade between busy layouts is mud.
- Diagrams are HTML/SVG using `house.css` (boxes, `stroke-dashoffset` arrow draws, memory
  cells, stack frames, queues), animated on the HyperFrames timeline at cue times.
  Registry blocks are fine only if restyled to the house style — strip their colors,
  glows, and window chrome.
- Check sync in snapshots: `npx hyperframes snapshot --at <cue abs times + 0.6>` — each
  frame must show the beat that the word names.

## Gate

```bash
cd projects/<id>/composition && npx hyperframes check --snapshots
```

`check` is the single pre-render gate: fix every error it reports (including WCAG
contrast). Then open the snapshots and review them against `creative-laws.md`. For a
human review pass, `npx hyperframes preview --background` and hand the user the Studio
URL (`http://localhost:<port>/#project/composition`).
