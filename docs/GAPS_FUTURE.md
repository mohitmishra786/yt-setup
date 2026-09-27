KernelKafe: from yt-setup to CoreDumpped-grade visuals
Research + a copy-paste engineering brief for GLM 5.3 / Gemini 3.8 Flash / GPT-6 Luna to execute against github.com/mohitmishra786/yt-setup.
1. What yt-setup actually does today
I pulled the full repo (main, 60 files) and read the pipeline end to end, not just the README. Here's the honest picture.
What's genuinely good and should survive untouched:
core/pipeline.py, checkpoint.py, project.py — a resumable, stage-based orchestrator (state.json, --from-stage, --only, --force). This is solid infra and exactly the shape a video pipeline should have. Keep it.
modules/voice/ — Chatterbox (MIT, zero-shot local cloning) as the default engine, with prepare-voice --consent, edge-tts/mac_say/ElevenLabs/XTTS as fallbacks, and docs/VOICE_CLONING.md giving you an honest duration/quality table (30–90s clean reference = "natural," 2–5min = "strong," 30min+ = "closest local to PVC"). This directly serves your "authentic audio" goal and needs no rework, just actual recorded reference audio from you.
modules/transcriber/, chapters/, subtitles/, publisher/ — faster-whisper/WhisperX, YouTube chapter-rule compliance, private-by-default upload. Fine as-is.
modules/shorts/vantage_adapter.py — reuses your other project (Vantage) for long→short clipping. Fine.
The actual gap — and it's the whole reason your videos would look AI-sloppy:
modules/slidebuilder/build_pptx.py + theme.py + modules/video_assembler/frame_renderer.py are, right now, a title + bullet-point slide generator. I read the code directly:
theme.py is five fixed colors (slate-900 background, sky-400 accent bar, violet-400 side strip) and a title/body font size. That's it.
build_pptx.py draws: background rectangle → accent bar → side panel → title textbox → bulleted textbox → footer. Every slide, every video, same four shapes.
frame_renderer.py (the Pillow fallback that turns slides into PNG frames for FFmpeg) does the identical layout in raster form: accent bar, title, wrapped bullets, footer.
video_assembler/transitions.py is 28 lines — crossfade between static frames. No element-level animation, no diagrams, no arrows, no code highlighting, no camera movement.
So the current pipeline is architecturally "Table of Contents slide, forever," narrated over. That is the canonical shape of an AI-slop explainer video — it's not a defect you'd tune, it's the whole design of those three files. This is what you need to gut, not patch.
2. What CoreDumpped's visual language actually consists of
Worth being precise about this before generating anything, because "minimalist" is doing a lot of work in your brief. CoreDumpped-style videos (and the broader systems/OS-explainer genre they sit in) share a specific, learnable grammar:
Labeled boxes and arrows as the primary vocabulary — memory pages, CPU cores, cache lines, queues, syscalls rendered as flat rectangles/circles with a name, connected by directional arrows that draw themselves in.
One idea revealed at a time, then held. Elements enter sequentially (never all at once), and the camera/composition pauses 1–3 seconds after a reveal before moving on. Pacing is the clarity.
A tight, repeated palette — usually 1 background, 1–2 neutral shape colors, 1–2 accent colors used consistently for "the thing we're tracking right now." Never a rainbow of boxes.
Consistent typography and spacing across the whole video — same font, same corner radius, same stroke width, same arrow style from minute 1 to minute 12.
State transitions, not slide transitions — a box moving from the "ready queue" to "running" is animated as a literal move, not a cut to a new slide.
Text is a caption, not the content — on-screen text is short labels near diagrams; the explanation is spoken, not read.
This is not what yt-setup's PPTX pipeline can produce even in principle — python-pptx + static PNG frames + crossfade has no concept of "this box moves from state A to state B while narration describes it." You need a genuinely different rendering approach, not a re-skin of theme.py.
3. The three tool ecosystems you named, and what they're actually for
I fetched the real skill definitions rather than going off the names.
latent-spaces/brag (/brag, /brag-slim) — Its own SKILL.md is explicit: 15–25 seconds, "the hook is everything," built to turn a product's own real UI/code into a punchy launch reel (Hyperframes for the full version; pure HTML/CSS/JS motion, model-authored, for brag-slim). Its actual production discipline is genuinely useful — a written brag-plan.md storyboard before any code, a fixed scene shape (hook → reveal → highlights → punchline), explicit "creative laws" (readable hold-times, ~0.3s/word, no generic filler, cohesive motion) — but it is tuned for and length-capped at short-form product reveals. You were right that it won't stretch to an 8–15 minute technical explainer as-is; its whole creative-laws section is calibrated for a 20-second attention arc, not sustained teaching.
A Manim-based long-form pipeline (this is the actual precedent for what you want — there are already published "Manim Video Production Pipeline" skills built on exactly this shape) uses: PLAN → CODE → RENDER → STITCH → AUDIO → REVIEW, one Python class per scene, Manim Community Edition + FFmpeg, and states its creative standard almost verbatim as what you described CoreDumpped doing: "every frame teaches," "never rush from one animation to the next," "a 2-second pause after a key reveal is never wasted," "cohesive visual language — all scenes share a color palette, matching animation speeds." This is architecturally the right shape for long-form CS/systems content — code-driven diagrams with real animation primitives (Transform, FadeIn, Create, MoveTo), not slide images.
skills.sh/jimliu/baoyu-skills — mostly baoyu-infographic, baoyu-cover-image, baoyu-slide-deck, baoyu-article-illustrator, baoyu-post-to-wechat/x. These are static image generators and social publishing, not animation engines. Useful for thumbnails, channel art, and X/community-post graphics — not for the video body.
claude-office-skills / "youtube-automation"-style skills — these are transcript-to-content repurposing and metadata skills (description, chapters, cross-posting), the same job yt-setup's scriptwriter/chapters/publisher stages already do. Not a visuals solution; genuinely redundant with what you already have.
Conclusion: none of the three off-the-shelf things you listed is the CoreDumpped engine. brag gives you production discipline for short-form; a Manim-shaped pipeline gives you the actual long-form animation architecture; baoyu gives you thumbnails/social assets. The right move is what you already intuited — build your own scene-animation engine inside yt-setup, but borrow the disciplined parts of brag (storyboard-first, explicit creative laws, "make it alive" principle) and the Manim skill (PLAN→CODE→RENDER→STITCH, cohesive-visual-language rule, one-class-per-scene, hold-after-reveal pacing) rather than copying either verbatim — which also solves your "shouldn't look copied" concern, since the result is neither /brag's product-launch grammar nor 3Blue1Brown's math grammar, but your own systems/CS diagram grammar.
4. Recommended architecture change
Replace the "outline → PPTX → Pillow frames → crossfade" spine with:
topic/source
  → outline.json           (KEEP scriptwriter stage, extend schema)
  → storyboard.json         (NEW — scene-by-scene visual plan, not prose)
  → scenes/scene_XX.py       (NEW — one render unit per beat, Manim OR
                               Remotion/Playwright-HTML depending on your
                               tool choice, see §5)
  → renders/scene_XX.mp4     (NEW — rendered per-scene, independently
                               re-renderable, matching yt-setup's existing
                               "resumable per-stage" philosophy)
  → audio/slide_XX.mp3       (KEEP — Chatterbox voice stage, unchanged)
  → final.mp4                (video_assembler stage rewritten to concat
                               scene renders + mux narration, instead of
                               still-image + FFmpeg crossfade)
  → transcript/chapters/shorts/publish   (KEEP, unchanged)
Two implementation choices for the scene renderer — pick one, don't do both:
Manim CE (Python) — best fit if you want precise, code-controlled geometric animation (boxes, arrows, Transforms, camera pans) and you're comfortable writing/generating Python Scene classes per beat. Heavier render times, needs LaTeX+ffmpeg, but this is the closest match to CoreDumpped/3B1B-style diagram choreography and is a well-trodden path (see §3).
HTML/CSS/JS scenes rendered via headless browser (Playwright) frame-by-frame, muxed with FFmpeg — closer to what brag-slim already does internally. Lower barrier for an LLM to generate correct code on the first try (CSS transitions/keyframes are more forgiving than Manim's animation API), easier to hit a crisp "flat, minimalist" look with plain CSS, and reuses skills your agents already have (HTML/CSS is the same substrate as yt-setup's own Artifact/web tooling). Weaker for camera-style 2D/3D geometric transforms.
Given you specifically want long and crisp/minimalist (not mathematical diagrams), I'd lean HTML/CSS/JS + Playwright rendering as the primary engine, with Manim as an optional scene-type for anything that needs true geometric animation (e.g. a rotating cache-line diagram). Both can coexist behind the same scenes/ interface if you want to hedge.
4.1 Two interaction surfaces, one shared engine
You flagged something I under-specified: you don't want the repo's only interface to be python cli.py run --topic "...". You want two things to genuinely coexist, sharing the same underlying scene engine so a video made either way looks identical:
Surface A — CLI/API pipeline (what exists today, kept and extended). python cli.py run --topic "..." for anyone running this programmatically/in batch/CI, calling out to an LLM API for the taste-bearing stages (storyboard, scene-coder). This is the path someone without a coding agent, or someone automating a schedule, uses.
Surface B — agent-native, chat-driven, no API key required. Anyone clones the repo, opens it in Claude Code or opencode, and just says "create a video on X" or "create a short on Y." No ANTHROPIC_API_KEY needed — the coding agent is the model doing the work, the same way you'd use it to write code. This is distributed the way brag distributes itself: as discoverable skills under .claude/skills/ (and symlinked/mirrored to .opencode/skill/, .agents/skills/ for cross-agent discovery — brag's README documents this exact pattern, reuse it) with slash-commands like /create-video "topic" and /create-short "topic" that walk the agent through the same director → scene-coder → visual-reviewer → assemble steps the CLI pipeline runs, except the agent itself performs each step (writing storyboard.json, writing scene files, running ffmpeg/playwright via its own shell access) instead of the code calling out to an LLM API.
Why this needs to be one engine, not two implementations: both surfaces must read/write the exact same storyboard.json schema, the exact same modules/scenegen/tokens.py design tokens, and the exact same modules/scenegen/components/ library. The CLI path and the skill path are two different drivers of identical scene-generation logic — never let them diverge into two different visual styles.
On model choice for Surface A: don't hardcode Anthropic as the only backend. You specifically want NVIDIA's hosted models (build.nvidia.com — OpenAI-compatible NIM endpoints serving many open models) available as a swappable provider alongside the Claude API, since plenty of people running this repo will want a free/cheap/self-hosted-adjacent option rather than an Anthropic key. core/llm.py already exists as a single client wrapper — extend it to a provider-agnostic interface (LLM_PROVIDER=anthropic|nvidia|... in config/env) rather than adding a second parallel client. This matters most for Surface A; Surface B doesn't need it at all, since the coding agent supplies its own model.
5. What to strip vs. keep in the repo
Path	Action	Why
modules/slidebuilder/*	Delete/replace	PPTX bullet generator — this is the AI-slop source
modules/video_assembler/frame_renderer.py	Delete	Pillow bullet-frame renderer, same problem
modules/video_assembler/transitions.py	Replace	Whole-slide crossfade → scene-level concat/transition logic
modules/video_assembler/assemble.py, bgm.py, pptx_to_images.py	Rework	Keep the FFmpeg-orchestration knowledge, repoint inputs at scene renders instead of slide PNGs; pptx_to_images.py becomes dead code
core/schemas.py (SlideOutline)	Extend, don't delete	Add a Storyboard/Scene schema alongside the existing outline schema
modules/scriptwriter/*	Keep, extend prompt	Still the right stage for topic → narrative beats; the output just needs a "visual beat" field per section now, not just bullets
core/pipeline.py, checkpoint.py, project.py	Keep unchanged	Orchestration is already correct
modules/voice/*	Keep unchanged	Already does what you want
modules/transcriber, chapters, subtitles, publisher, shorts	Keep unchanged	Downstream of video, not visual-dependent
.claude/agents/*, agentroles.yaml, opencode.json	Extend	Add scene-director/scene-coder/visual-reviewer roles (see §6) — this config is currently generic dev-agent routing for building the repo itself, it has nothing to do with video production yet
core/llm.py	Extend	Single-provider (Anthropic) → pluggable provider interface (Anthropic + NVIDIA NIM/build.nvidia.com, OpenAI-compatible), config-selected. Only matters for Surface A below
.claude/skills/, .opencode/skill/, .agents/skills/	New	Chat-driven /create-video, /create-short skills — Surface B, see §4.1
6. Agent roles for the new visual stage
The existing agentroles.yaml routes coding-the-repo tasks (planner/implementer/reviewer/fixer/tester/summarizer). That's separate from producing-a-video tasks. Add a second, video-specific role set (own file, e.g. videoroles.yaml, or a section in the same one):
director (opus-class) — turns outline.json into storyboard.json: one entry per beat with what's on screen, what enters/exits/moves, timing, which accent color is "live" right now. This is the taste-bearing step; keep it opus/highest-capability regardless of what you use elsewhere.
scene-coder (sonnet-class) — turns each storyboard beat into a scene render file (HTML/CSS/JS or Manim Scene), against a fixed design-token file (palette, spacing, font, stroke width, corner radius, arrow style) so every scene is visually consistent without the model having to reinvent style choices each time.
visual-reviewer (needs vision) — renders a still frame or short preview per scene and checks it against the design tokens and the "creative laws" checklist (one idea revealed at a time, text legible for its hold duration, palette compliance, no unexplained clutter). This is the step that catches slop before render time, and it's genuinely worth a human-in-the-loop checkpoint here too, at least for your first 5–10 videos, since taste doesn't fully delegate.
narrator-sync (mechanical, haiku-class fine) — aligns audio/durations.json timing against scene beat timing so narration and animation don't drift.
7. Honesty check before you commit to this
CoreDumpped is (as far as public information goes) largely hand-animated — you already said this. An agentic pipeline can get you disciplined, consistent, code-generated minimalism; it will not spontaneously discover the specific compositional choices a skilled motion designer makes. The design-token file + storyboard-first discipline in §4–6 is how you close most of that gap, but budget for manually tuning the token file and a few hand-picked "hero" scene templates yourself early on, then let the agents reuse them.
Treat the first 2–3 videos as building your scene template library (reusable box/arrow/queue/cache/timeline components), not as disposable one-offs. Every video after that gets cheaper and more consistent because scene-coder is composing from a growing library instead of inventing from scratch — this is also your main defense against "looks copied," since your library will diverge from anyone else's within a few videos.
Long-form (8–15 min) means dozens of scene renders per video. Keep the render stage resumable per-scene (matching the repo's existing checkpoint philosophy) so a failed/ugly scene 14 doesn't force a full re-render.
8. The brief — hand this to GLM 5.3 / Gemini 3.8 Flash / GPT-6 Luna
Copy everything in the code block below as the task prompt. It assumes the model has repo write access (fork/clone of mohitmishra786/yt-setup) and can run Python/Node/FFmpeg/Playwright locally.
You are working in a clone of github.com/mohitmishra786/yt-setup, a
local-first, resumable YouTube production pipeline (Python, stage-based:
core/pipeline.py orchestrates modules/ stages, checkpointed in state.json
per project under projects/<id>/).

GOAL
Replace the current slide-deck visual stage (python-pptx bullet slides +
Pillow static-frame renderer + FFmpeg crossfade) with a scene-based
animation engine that produces minimalist, CoreDumpped/3Blue1Brown-style
diagram animations (labeled boxes, arrows, state transitions, one idea
revealed at a time, held for readability) instead of narrated bullet
points. Target: 8-15 minute long-form technical/CS explainer videos,
narrated with the existing Chatterbox voice-cloning stage. Output must
look hand-crafted and consistent across an entire video and across many
videos, not like default AI-generated slides.

This must ship as TWO COEXISTING INTERFACES over one shared engine, not
one or the other:
  (A) The existing `python cli.py run --topic "..."` programmatic
      pipeline, kept and extended, calling out to an LLM API for the
      storyboard/scene-coder stages.
  (B) New chat-driven skills so that anyone can clone this repo, open it
      in Claude Code or opencode with no API key configured, and just
      say "create a video on X" or "create a short on Y" — the coding
      agent itself performs the director/scene-coder/visual-reviewer/
      assemble steps directly (writing files, running ffmpeg/playwright
      via shell) instead of code calling an LLM API.
Both interfaces MUST read/write the identical storyboard.json schema and
the identical modules/scenegen/tokens.py + components/ library, so a
video produced via the CLI and one produced via chat are visually
indistinguishable. Do not build two parallel visual systems.

DO NOT TOUCH (already correct, do not modify behavior):
- core/pipeline.py, core/checkpoint.py, core/project.py
- modules/voice/* (Chatterbox/edge-tts/ElevenLabs/XTTS engines)
- modules/transcriber/*, modules/chapters/*, modules/subtitles/*,
  modules/publisher/*, modules/shorts/*
- Existing CLI surface in cli.py for these stages

DELETE / REPLACE:
- modules/slidebuilder/build_pptx.py and theme.py
  (python-pptx bullet-slide generator — remove entirely)
- modules/video_assembler/frame_renderer.py
  (Pillow bullet-frame renderer — remove entirely)
- modules/video_assembler/pptx_to_images.py (becomes dead code, remove)
- modules/video_assembler/transitions.py (rewrite for scene-level concat,
  not whole-slide crossfade)

BUILD, as a new modules/scenegen/ package:

1. Design-token file (modules/scenegen/tokens.py or tokens.json):
   a single source of truth for background color, 1-2 neutral shape
   colors, 1-2 accent colors, font family/sizes, stroke width, corner
   radius, arrow style, default hold-duration-per-reveal (~1.5-3s),
   default per-word reading pace (~0.3s/word) for any on-screen text.
   Every scene must import and obey this file. No scene may hardcode a
   color or font.

2. Storyboard schema (extend core/schemas.py):
   Add a Storyboard/Scene pydantic model: ordered list of beats, each
   with: id, narration_text (ties to existing speaker-notes concept),
   duration estimate, a list of visual "elements" (box/arrow/label/
   group) with enter/exit/move actions and timing offsets, and which
   accent color is "live" in this beat. This sits between the existing
   outline.json (keep as-is, it's still the narrative/SEO source) and
   the new scene renders — add a "storyboard" pipeline stage that
   consumes outline.json + generates storyboard.json (this is the stage
   an LLM call should own; treat it as the taste-bearing step, so wire
   it to accept a higher-capability model than the mechanical stages).

3. Scene renderer (pick ONE, implement cleanly):
   Option A (recommended primary): HTML/CSS/JS scenes rendered
   frame-by-frame via a headless browser (Playwright), then muxed to
   video with FFmpeg. Each scene is a self-contained HTML file using
   the design tokens as CSS custom properties; animation via CSS
   transitions/keyframes or a small JS animation loop; one scene per
   storyboard beat, independently re-renderable and cacheable exactly
   like the existing per-slide audio files are.
   Option B (alternative/optional secondary): Manim Community Edition
   scenes (one Python Scene class per beat) for any beat that needs
   true geometric/camera animation. If you implement this as a second
   scene "kind," both kinds must render to the same MP4-per-beat
   interface so video_assembler doesn't care which engine produced a
   given scene.

   Either way: one render unit per storyboard beat, written to
   projects/<id>/scenes/scene_XX.mp4, checkpointed per-scene the same
   way audio/slide_XX.mp3 already is, so a single bad scene can be
   re-rendered with --force on just that stage without redoing the rest.

4. Rewrite modules/video_assembler/assemble.py to concatenate scene
   renders + mux the existing per-slide/per-beat narration audio,
   instead of still-image-plus-audio-per-slide. Keep the existing BGM
   ducking logic (bgm.py) if it still applies structurally; adapt as
   needed.

5. Build a small reusable "component library" inside modules/scenegen/
   (e.g. components/box.py|.ts, components/arrow.py|.ts,
   components/queue.py, components/timeline.py) so common CS-diagram
   primitives (labeled box, directional arrow, state-transition move,
   queue/stack visualization, memory-grid, timeline/sequence diagram)
   are written ONCE and composed by every future video, not
   regenerated from scratch per video. This library is the actual
   long-term differentiator — prioritize getting 4-6 solid, reusable
   primitives right over covering every possible diagram type.

6. Add a lightweight visual-QA step: render a still frame (or short
   clip) per scene and run an automated check against the design-token
   file (palette compliance, text-hold-duration vs. word count, "only
   one new element enters at a time" heuristic) before the stage is
   marked complete in state.json. Flag/fail loudly rather than silently
   producing an off-brand scene.

7. Extend modules/scriptwriter/ prompts (modules/scriptwriter/prompts/)
   minimally: the existing outline generation is fine for narrative
   structure, but each slide/beat entry needs a short "visual_beat"
   hint field (what should be ON SCREEN, not what should be SAID) so
   the new storyboard stage has something to work from beyond bullet
   text.

8. Agent routing: add a second role set (new file, e.g.
   videoroles.yaml, following the exact pattern already established by
   agentroles.yaml/opencode.json/.claude/agents/) for the VIDEO
   PRODUCTION task (separate from the existing REPO DEVELOPMENT roles,
   which govern coding this repo and should not be touched):
   - director: plans storyboard.json from outline.json (highest-
     capability model available; this is the taste-bearing step)
   - scene-coder: writes individual scene render files against the
     token file (mid-capability model, high volume of small tasks)
   - visual-reviewer: runs the visual-QA check from step 6 and can
     request a re-render of a specific scene
   - narrator-sync: aligns audio durations to storyboard beat timing
     (mechanical, cheapest model tier is fine)

9. Pluggable LLM provider for Surface A: extend core/llm.py from its
   current single-provider (Anthropic) shape to a small provider
   interface selected via config/env (e.g. LLM_PROVIDER=anthropic or
   LLM_PROVIDER=nvidia), where the nvidia provider talks to NVIDIA's
   hosted NIM endpoints at build.nvidia.com (OpenAI-compatible chat
   completions API — treat it like any OpenAI-compatible client, model
   name configurable) so people without an Anthropic key can still run
   the CLI pipeline end to end. Keep the existing offline-stub behavior
   (YT_STUDIO_STUB_LLM) working regardless of provider. This step ONLY
   affects Surface A; the chat-driven skills in step 10 do not need it.

10. Build Surface B as real, installable skills:
    a. Create .claude/skills/create-video/SKILL.md and
       .claude/skills/create-short/SKILL.md. Each should instruct the
       agent, in the agent's own words/steps (not by shelling out to
       an LLM API), to: take a topic or source in natural language,
       run/emulate the outline -> storyboard -> scene-render ->
       voice -> assemble pipeline directly using the agent's own file-
       write and shell/bash tool access, reusing the exact same
       modules/scenegen/tokens.py + components/ library and the same
       storyboard.json schema Surface A uses. create-short should be a
       shorter/faster path (fewer beats, tighter duration) reusing the
       same component library, not a separate visual system.
    b. Mirror discovery for other agents the way latent-spaces/brag
       already does: symlink or mirror these skills at
       .opencode/skill/ and .agents/skills/ pointing at the same
       skill body, so Claude Code, opencode, and other agent-skill-
       aware tools all discover them without duplicate content. Look
       at exactly how brag's repo wires this (see step 11) and copy
       the mechanism, not the content.
    c. These skills should be able to call the SAME Python functions/
       modules the CLI pipeline calls (e.g. import from
       modules/scenegen, modules/voice) rather than reimplementing
       logic in prose only — treat the skill as a thin orchestration
       layer over the existing Python modules wherever the agent's
       tool access allows it (running the checkpointed pipeline stages
       via subprocess is a legitimate implementation, not just
       "describe how to do it in English").

11. Before building steps 3, 5, and 10, actually clone and read the
    real source of the tools referenced in this brief, don't work from
    memory or from names alone:
    - github.com/latent-spaces/brag — read skills/brag-slim/SKILL.md
      and skills/brag/ in full. Extract: (i) the cross-agent skill-
      discovery symlink pattern (.claude/skills, .opencode/skill,
      .agents/skills) for step 10b, (ii) the storyboard-before-code
      discipline and the shape of its "creative laws" section as a
      structural template for YOUR OWN video-specific creative-laws
      doc (write your own laws for long-form CS-diagram pacing, e.g.
      "one idea revealed at a time," "hold 1.5-3s after a reveal" —
      do not reuse brag's actual short-form product-launch wording,
      it doesn't apply to this content type and reusing it verbatim is
      exactly the "looks copied" outcome to avoid).
    - Any published Manim-based long-form video-production skill you
      can find (search for "Manim Video Production Pipeline" style
      skills) — extract the PLAN -> CODE -> RENDER -> STITCH -> AUDIO
      -> REVIEW stage shape and the "cohesive visual language across
      scenes" discipline as a structural reference for this repo's own
      storyboard -> scenegen -> assemble stages. Do not adopt Manim
      itself unless you're implementing Option B in step 3.
    - skills.sh/jimliu/baoyu-skills — specifically baoyu-infographic
      and baoyu-cover-image, only for optional thumbnail/channel-art
      generation (NOT the main video body). Skip this entirely if
      you're not building a thumbnail stage in this pass.
    In every case: extract the reusable STRUCTURE/DISCIPLINE (how the
    work is planned, how consistency is enforced, how skills are made
    discoverable across agents), not the specific creative content or
    wording, which is tuned for a different format (short-form product
    launches, or math animation) than this repo's long-form CS/systems
    explainer format.

CONSTRAINTS
- Preserve the existing resumable/checkpointed philosophy: every new
  stage must be independently re-runnable via --only/--force on the
  existing CLI, matching how audio/transcriber/etc already behave.
- Preserve offline-stub behavior: heavy stages (rendering, LLM calls)
  need a YT_STUDIO_STUB_* style environment-variable stub path for CI/
  tests, matching the existing pattern (YT_STUDIO_STUB_VOICE,
  YT_STUDIO_STUB_LLM, etc.) — add YT_STUDIO_STUB_SCENES or similar.
- Do not introduce a dependency on any single external animation SaaS
  (e.g. Hyperframes) — this must run fully locally with open tooling
  (Playwright/FFmpeg, or Manim CE/FFmpeg), consistent with the repo's
  existing "local-first" principle stated in its README and
  docs/ARCHITECTURE.md.
- Write tests (pytest, matching the existing tests/ pattern) for the
  new schema validation and for the assemble.py concat logic at
  minimum; full visual-render tests can be smoke tests that just check
  a scene file/mp4 was produced, not pixel-perfect assertions.
- Update docs/ARCHITECTURE.md's data-flow diagram and README's
  "Project layout" / "Pipeline stages" tables to reflect the new
  storyboard + scenegen stages, removing references to slidebuilder's
  old PPTX behavior.

DELIVERABLE
Two working end-to-end paths producing visually identical output:
  (A) `python cli.py run --topic "..."` (Anthropic or NVIDIA NIM as the
      LLM provider, config-selected) producing final.mp4 built from
      animated, design-token-consistent scenes instead of static bullet
      slides, with all existing downstream stages (transcribe, chapters,
      shorts, publish) unaffected.
  (B) Inside Claude Code or opencode, with no API key configured,
      saying "create a video on <topic>" or "create a short on <topic>"
      and getting the same kind of output via the .claude/skills/
      create-video and create-short skills.
Include a short docs/SCENEGEN.md explaining the token file, the
component library, how to add a new reusable diagram primitive, and how
Surface A and Surface B both stay in sync against the same engine. Also
include a brief docs/CREDITS.md noting which structural patterns were
adapted from brag/other referenced skills (per step 11) and what was
built from scratch, so provenance is honest and visible.
9. Practical next steps for you, before running that prompt
Record your 30–90s (ideally 2–5min) clean voice reference now if you haven't — docs/VOICE_RECORDING_SCRIPT.md already exists in the repo for this, and it's the one input nothing downstream can substitute for.
Pick Option A vs B in §4 (I'd default to HTML/CSS/Playwright) before handing off the brief above — it changes what "scene-coder" is actually generating.
Decide your default LLM provider for Surface A (Anthropic API vs. a specific model on build.nvidia.com) — doesn't block Surface B (chat-driven, no key needed) at all, but the executing model needs to know which one to wire as default.
Sketch (even roughly, on paper) 4–6 diagram primitives you know you'll reuse across your first several videos (a labeled box, a directional arrow/pointer, a queue, a memory grid, a timeline/sequence swimlane, a state-transition move) — hand these sketches to the "director" role as reference before it invents its own, so your component library starts from your taste rather than the model's default.
Treat video 1-3 as template-building, not publishing-ready — budget extra review time there specifically on the visual-reviewer step's output.