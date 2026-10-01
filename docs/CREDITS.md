# Provenance & Credits

This document records the structural design patterns adapted from external open-source projects, and what was authored from scratch for this pipeline.

---

## 1. Patterns Adapted from `latent-spaces/brag`

Source: [github.com/latent-spaces/brag](https://github.com/latent-spaces/brag)

### Structural Patterns Adopted
1. **Cross-Agent Skill Discovery Directory Pattern**:
   - Skills are authored in `skills/<skill_name>/SKILL.md` as the canonical source.
   - Symlinked across `.claude/skills/`, `.opencode/skill/`, `.opencode/skills/`, and `.agents/skills/` to allow seamless multi-agent discovery (Claude Code, OpenCode, Codex, and other agent platforms) without duplicating content.
2. **Storyboard-Before-Code Discipline**:
   - Requiring a complete, structured plan (`storyboard.json` in our engine, corresponding to `brag-plan.md`) before writing any rendering or code files.
3. **Shape of "Creative Laws" Section**:
   - Structuring creative constraints into an explicit checklist of non-negotiable visual laws that agents and QA tooling verify before rendering.
4. **Perception-Aware Hold Times**:
   - The rule that on-screen text must remain visible long enough to be read by a human (~0.3s per word), and that pace comes from choreography rather than pulling text away prematurely.

5. **Brag production discipline, retuned for technical explainers (2026-09)** — adapted from
   `skills/brag/SKILL.md` and `references/step-2..4` (MIT):
   - Plan → composition brief → HyperFrames build → single `hyperframes check` gate → render.
   - The hook-first rule, "show the real thing", "make it alive", "every frame postable", the
     reading-time floor, tone presets, the plan template shape, and the poster-as-frame-0 bake.
   - Written up in `skills/create-video/references/` with our own wording, palette, and
     technical-explainer rules (real code/compiler output, one live accent, type minimums,
     vertical safe zones, long-form chapter arcs).

### What Was NOT Used from `brag`
- **Creative Wording & Content**: Brag's product-launch copy, tone text, and share-copy
  templates are not reused.
- **Bundled assets**: Brag's music and SFX files are not copied; audio is resolved through
  HyperFrames `media-use`.
- **The skill itself**: brag is not installed or invoked; `/create-video` and
  `/create-short` are standalone workflows.

HyperFrames (open source, renders locally with headless Chrome + FFmpeg) is now the visual
engine for the agent surface. An earlier version of this file said it was an "external
SaaS dependency"; that was wrong — cloud rendering is optional and never used here.

---

## 2. Patterns Adapted from Manim Video Production Pipelines

Sources: `manim-video-lab`, `topic2manim`, and published Manim production workflows.

### Structural Patterns Adopted
1. **Production Lifecycle Shape**:
   `PLAN (Storyboard) -> CODE (HTML/Components) -> RENDER (Playwright/FFmpeg) -> AUDIO (Chatterbox Voice) -> STITCH (Assembler) -> REVIEW (Visual QA)`
2. **Cohesive Visual Grammar Across All Scenes**:
   - The requirement that all scenes in a video share an unvarying design-token palette, consistent stroke widths, identical typography, and synchronized animation speeds.
3. **One Render Unit Per Beat**:
   - Decoupling scenes into standalone, independently cacheable files (`scenes/scene_XX.html` and `scenes/scene_XX.mp4`) matching `audio/slide_XX.mp3` so individual scenes can be re-rendered with `--force` without re-rendering the entire video.
4. **"A 2-second pause after a key reveal is never wasted"**:
   - The rule that visual clarity in technical teaching requires pausing on completed diagram states rather than immediately rushing into the next animation.

---

## 3. What Was Built From Scratch

1. **Minimalist CS/Systems Diagram Component Library (`modules/scenegen/components/`)**:
   - Custom implementations of labeled boxes, directional SVG connectors with animated draw-in, FIFO buffer queues with head/tail markers, execution timelines, memory/cache grids with hex offsets, and discrete state machines.
2. **Deterministic Time-Driver for Web Animations**:
   - `window.seekTo(t)` JavaScript architecture allowing headless browsers to advance animations to discrete time offsets for deterministic frame capture and testing.
3. **Automated Visual QA Engine (`modules/scenegen/qa.py`)**:
   - Automated validator checking palette compliance (forbidding unapproved colors), measuring sequential reveal staggering (flagging simultaneous element pop-in), and validating reading durations.
4. **Dual-Surface Coexistence Architecture**:
   - The unified bridge enabling both Surface A (`python cli.py run` with Anthropic or NVIDIA NIM) and Surface B (chat-driven `/create-video` and `/create-short` skills) to read and write the exact same Pydantic schema and component library.
5. **Frame Freeze & Audio Muxing Adapter (`modules/video_assembler/assemble.py`)**:
   - Automatic `tpad` frame-hold extension that freezes the final frame of an animated diagram if speech continues past the animation duration, ensuring the diagram stays visible on screen while the narration finishes.
