# Scenegen — Animated Diagram Engine for Technical Videos

`modules/scenegen` replaces static bullet-point slide decks with minimalist, **CoreDumpped / 3Blue1Brown-style diagram animations**: labeled boxes, directional connection arrows, execution queues, memory grids, and state transitions.

Target format: **8–15 minute long-form technical/computer science explainer videos** and **30–60 second technical Shorts/Reels**, narrated with local voice cloning (Chatterbox).

---

## 1. Design Token System (`modules/scenegen/tokens.py`)

Visual consistency across hours of video is enforced through a single source of truth: `DesignTokens`.

Every scene must import and obey these tokens. **No scene is permitted to hardcode a raw hex color or custom font.**

### Key Design Tokens

| Token | Value | Purpose |
|---|---|---|
| `bg_color` | `#0f141c` | Deep matte slate canvas background |
| `shape_neutral_1` | `#1b2230` | Default card/box container fill |
| `shape_neutral_2` | `#273248` | Elevated element / divider fill |
| `border_color` | `#334155` | Crisp structural node border |
| `text_primary` | `#f8fafc` | Crisp high-contrast titles & labels |
| `text_muted` | `#94a3b8` | Addresses, captions, secondary text |
| `accent_primary` | `#38bdf8` | Electric cyan ("the thing we are tracking right now") |
| `accent_secondary` | `#f43f5e` | Crimson / rose (eviction, error, contrast state) |
| `accent_success` | `#34d399` | Emerald green (committed, match, success) |
| `accent_warning` | `#fbbf24` | Amber (pending, lock, waiting) |
| `accent_purple` | `#a855f7` | Violet (memory segment, transform) |
| `font_family` | `'Inter', system-ui, sans-serif` | Clean, readable diagram typography |
| `code_font_family` | `'JetBrains Mono', monospace` | Hex addresses, registers, code tokens |
| `stroke_width` | `3px` | Standard line and border thickness |
| `corner_radius` | `12px` | Card/box corner roundness |
| `default_hold_per_reveal` | `2.0s` | Minimum pause after an element enters before next action |
| `per_word_reading_pace` | `0.30s/word` | Minimum hold required for on-screen text |

Tokens are exported to CSS variables via `tokens.to_css_variables()` for injection into self-contained HTML scene files.

---

## 2. Storyboard Schema (`storyboard.json`)

Between the narrative `outline.json` and the rendered video sits `storyboard.json` (defined in `core/schemas.py:Storyboard`).

Each storyboard beat contains:
- `id`: Unique identifier (e.g. `scene_01`).
- `title`: Mental model milestone.
- `narration_text`: Spoken narration sentences from speaker notes.
- `duration_estimate`: Estimated duration in seconds (computed from narration word count + hold times).
- `live_accent`: Which accent token is currently active (`accent_primary`, `accent_secondary`, etc.).
- `visual_beat`: High-level description of what is visible on screen.
- `elements`: List of `VisualElement` primitives (`box`, `arrow`, `queue`, `timeline`, `grid`, `label`).
- `actions`: List of `VisualAction` steps (`enter`, `draw`, `highlight`, `move`, `exit`) with `start_time` and `duration`.

---

## 3. Reusable Component Library (`modules/scenegen/components/`)

Common systems and computer science primitives are authored once in `modules/scenegen/components/` and composed across all scenes:

1. **`box.py` (`render_box`)**: Rounded rectangle with semantic states (`idle`, `active`, `success`, `warning`, `error`), label, subtitle, and uppercase tag badge.
2. **`arrow.py` (`render_arrow`)**: SVG directional connector with arrowhead marker, optional label, and animated `stroke-dashoffset` draw-in effect.
3. **`queue.py` (`render_queue`)**: FIFO buffer / pipeline with discrete slot cells, count indicator, and `▲ HEAD` / `▲ TAIL` pointers.
4. **`timeline.py` (`render_timeline`)**: Execution sequence rail connecting milestone nodes with step numbers, checkmarks, and active stage pulsing.
5. **`memory_grid.py` (`render_memory_grid`)**: Contiguous memory / cache layout displaying byte offsets (`0x00`, `0x08`...) and values (`0xDEADBEEF`, `PTR`) with active cell selection.
6. **`state_transition.py` (`render_state_machine`)**: Discrete system state machine (`READY -> RUNNING -> BLOCKED`) showing current state tokens.

### How to Add a New Reusable Diagram Primitive

To add a new primitive (e.g., a B-Tree node or Network Ring):
1. Create `modules/scenegen/components/my_primitive.py`.
2. Define a rendering function returning semantic HTML/SVG markup styled with CSS variables (e.g. `var(--shape-neutral-1)`, `var(--stroke-width)`).
3. Define a `my_primitive_css()` function returning the component styles.
4. Export the component in `modules/scenegen/components/__init__.py` and include its CSS in `all_components_css()`.
5. Support the element type in `modules/scenegen/builder.py:_resolve_element_coords` and `build_scene_html`.

---

## 4. How Surface A and Surface B Stay in Sync

A central requirement of this architecture is that **CLI runs and Agent chat runs produce visually identical output**:

```
+-------------------------------------------------------+
|  Surface A: CLI Pipeline                              |
|  python cli.py run --topic "..."                      |
|  (calls Anthropic / NVIDIA NIM for Director step)     |
+---------------------------+---------------------------+
                            |
                            |  Both read/write identical
                            v  storyboard.json & HTML
+-------------------------------------------------------+
|  Shared Engine (modules/scenegen/)                    |
|  - tokens.py (single source of truth for visuals)     |
|  - components/ (reusable diagram primitives)          |
|  - qa.py (automated palette & pacing verification)   |
|  - renderer.py (Playwright + FFmpeg)                  |
|  - assemble.py (concatenation + voice muxing)         |
+---------------------------^---------------------------+
                            |
                            |  Both read/write identical
                            |  storyboard.json & HTML
+---------------------------+---------------------------+
|  Surface B: Agent-Native Skills                       |
|  /create-video, /create-short                         |
|  (Coding agent acts as Director & Scene Coder)        |
+-------------------------------------------------------+
```

1. **Shared Storyboard Schema**: Whether generated by Claude 3.5 Sonnet / Llama 3.3 via the CLI, or written directly by Claude Code / OpenCode in chat, `storyboard.json` validates against the exact same Pydantic schema in `core/schemas.py`.
2. **Shared Design Tokens**: Every scene HTML references `modules/scenegen/tokens.py`.
3. **Shared QA Suite**: Both paths run `modules/scenegen/qa.py` to assert palette compliance, word reading pace, and single-idea-reveal discipline.
4. **Shared Assembler**: `modules/video_assembler/assemble.py` concatenates the resulting scenes and freezes final frames to match narration durations equally for both surfaces.

---

## 5. Automated Visual QA (`modules/scenegen/qa.py`)

Before a video is assembled, `ScenegenStage` validates each scene against three automated gates:

1. **Sequential Reveals**: Ensures no two enter/draw actions occur simultaneously. Minimum stagger delta: `1.0s` (recommended `1.5–2.5s`).
2. **Hold Duration & Reading Pace**: Compares scene duration against word count (`words * 0.3s/word + 2.0s hold`). Flagged if the scene cuts away too quickly.
3. **Palette Compliance**: Inspects scene markup for unapproved hex colors outside the token palette.
