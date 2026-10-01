# Shorts laws: vertical 1080×1920

These extend the shared house rules in `skills/create-video/references/creative-laws.md`
(palette, voice-drives-the-picture, real material, one focus). This file covers what's
different about a vertical Short. Every number below came from a Short that shipped, or from
a correction the creator made.

## The frame

```
y=0     ┌──────────────────────────┐
        │  (platform UI: status,   │  top ~220px: nothing important
y=220   ├──────────────────────────┤
        │  NOTE: one explanatory   │  y≈250, 50px, max 2 lines, width 900
        │  line (changes per beat) │
y≈420   ├──────────────────────────┤
        │                          │
        │      CONTENT AREA        │  y 420–1350: the focus stack lives here,
        │   (focus stack, centred) │  vertically centred as a group
        │                          │
y=1350  ├──────────────────────────┤
        │  CAPTIONS (60px, white)  │  y≈1410, 2–4 words per chunk
y=1540  ├──────────────────────────┤
        │  (Shorts UI: title,      │  bottom ~380px: nothing important
        │   channel, buttons)      │  right ~140px also covered by buttons
y=1920  └──────────────────────────┘
        x: content from 90 to 990 (width 900)
```

These positions are the `portrait` entry of `LAYOUTS` in `scenekit.py`. Don't hand-place
content outside them.

## The laws

1. **Focus stack, always.** The thing being talked about sits **centred** in the content
   area. When the next thing arrives, earlier items slide up (and dim, unless they're still
   being referenced, e.g. code whose lines keep lighting up) and the newcomer takes the centre.
   Never put one block at the top and leave the middle empty while waiting for the next
   reveal. Use `Scene.focus([heights])` and `Focus.run(...)`.
2. **One mechanism.** A Short explains exactly one thing. If the script needs "and also…",
   it's two Shorts.
3. **Hook within 0.5s of the first scene.** Something visible changes immediately: the code
   appears, a value flips, an arrow draws. Not a headline. The title card (1.5–1.8s) comes
   first and then cuts straight into it.
4. **No section labels.** No `C · USE AFTER FREE`, no `01 · …`. One explanatory note line
   carries the context. Notes that would show for under 1.2s are merged away automatically,
   so don't fight it; anchor notes to beats at least ~1.5s apart.
5. **Readable on a phone:**

   | Element | Minimum |
   |---|---|
   | Code | **34px** mono, line height ~52px. Break long lines at natural points (`movq %rsp,` / `  PER_CPU_VAR(…)`) instead of shrinking |
   | Diagram labels | 36–40px; register/variable names 56–64px |
   | Note line | 50px |
   | Captions | 60px, weight 800 |
   | Secondary labels ("user memory", "pointer") | 32–36px in `ink2` |

   Readable text never uses `ink3`, which fails contrast. Code comments use `ink2`.
6. **Real material, cited on screen.** Every code panel's first line names its source
   (`// entry_SYSCALL_64 · Linux 7.3`, `$ gcc uaf.c && ./uaf`). Output is copied from an
   actual run, never typed from memory.
7. **Calm motion.** 0.3–0.6s moves, ease-in-out, nothing bouncy. Pace comes from the cut
   between beats, not from frantic motion.
8. **Colour budget.** Greys, plus one accent element (the focus), plus red only on the thing
   that is wrong (the bad line, the bad value, the guard page that got hit). The background
   is the neutral kit background; never a coloured one.
9. **Get the direction right.** Diagrams must match reality: x86 stacks grow *down*, so the
   guard page goes below. A wrong diagram is worse than none.
10. **Length.** 30–45s is the sweet spot, never over 60s. That's a 1.5–1.8s title card,
    ~33–38s of paced narration, ~0.6s between scenes, a 0.8s hold on the last scene and a
    2.5s outro.

## Captions

- On by default: white, bold, 60px, 2–4 words per chunk. The spoken word is at full opacity,
  the rest at 45%. **No coloured words.**
- Built from `audio/words.json` (the exact script), never from raw ASR text.
- Names spelled phonetically for the voice (`G-C-C`, `G-S`) are mapped back in
  `caption_word()` (scenekit). Add any new ones there.

## Audio

- Narration only. No music or SFX unless the creator asks.
- `cli.py pace --gap 0.3` for Shorts (long-form uses 0.45): tighter, but never breathless.

## Branding (from `config.yaml` → `channel:`)

- **Title card**, 1.5–1.8s: wordmark with blinking cursor, plus the topic title.
  `title_card(cues, TITLE, 1.8)`.
- **Outro**, 2.5–3s: wordmark, handle, tagline. `outro(cues, 2.5)`.
- **Poster** = the title card at a moment the cursor is visible (`poster.json` time ≈ 0.9s).
  It's baked into frame 0, so the thumbnail matches the first thing viewers see.
