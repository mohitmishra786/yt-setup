---
name: create-short
description: Produce a punchy, 30-60 second technical Short/Reel with minimalist diagram motion and cloned narration. Use when someone says "/create-short", "create a short on X", "make a reel about X", or wants to produce a short-form technical video.
---

# /create-short

Produce a high-impact, short-form technical Short/Reel (30–60 seconds) with animated diagrams and voice narration.

This uses the **exact same** design tokens (`modules/scenegen/tokens.py`), storyboard schema (`core/schemas.py:Storyboard`), and component library (`modules/scenegen/components/`) as long-form videos — ensuring brand consistency across formats without maintaining two separate visual engines.

---

## Short-Form Visual Laws

- **Fast Hook (0–3s)**: The first 3 seconds must reveal the problem or surprising question immediately. Animate the core node into view within 0.5s.
- **Tightly Choreographed Motion**: Stagger reveals every 1.0–1.8 seconds. Hold for 1.2–2.0 seconds after key state transitions.
- **Vertical or Landscape Resolution**:
  - Vertical (1080×1920): Set `shorts_width` & `shorts_height` in `ProjectSettings`.
  - Landscape (1920×1080): Standard format.
- **Single Core Mental Model**: Do not attempt to cover an entire topic. Focus on exactly ONE mechanism: e.g. "How epoll notifies the kernel", "How a mutex sleep works", "What happens on a cache miss".
- **Spoken Economy**: Keep spoken narration under ~130 words total (approx. 45 seconds).

---

## Short-Form Production Workflow

### Step 1: Initialize Short Project

```bash
python cli.py run --topic "<short_topic>" --only scriptwriter
```

### Step 2: Concise 3–4 Beat Storyboard

Write `projects/<project_id>/storyboard.json` with 3 to 4 focused beats:
1. **The Hook (0–10s)**: The question or unexpected bottleneck (e.g. `Client -> Server` slow poll).
2. **The Mechanism (10–35s)**: The diagram reveal (e.g. Event queue / Ring buffer replacing linear search).
3. **The State Transition (35–50s)**: Animated token transfer showing efficiency gain.
4. **The Takeaway / CTA (50–60s)**: Summary box + "Follow for systems deep dives".

### Step 3: Scene Generation & Voice Synthesis

Run scene rendering and audio synthesis:
```bash
python cli.py run --project <project_id> --only scenegen,voice
```

### Step 4: Verification & Assembly

Assemble the short video:
```bash
python cli.py run --project <project_id> --only video_assembler
```

The resulting `projects/<project_id>/final.mp4` is your publication-ready Short/Reel.
