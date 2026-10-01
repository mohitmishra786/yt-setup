# Long-form: stretching the short-form discipline to minutes

The creative laws are tuned for a ~20-second attention arc. A long video is **a chain of
short arcs**, not one short arc stretched thin. Every chapter must earn attention the way a
short does.

## Structure

```
Cold open (0:00–0:15)   the hook — the crash / wrong intuition / impossible number, shown
Promise   (0:15–0:40)   what the viewer will understand by the end, and why it matters
Chapters  (1–3 min each) each a mini-arc: question → mechanism shown working → payoff
Recap     (last 30–60s) the payoff diagram, rebuilt fast from the recurring elements
Outro     (5–10s)       the one-line takeaway; hold on the poster-worthy frame
```

Chapter count by length (adjust to the material, don't pad):

| Duration | Chapters | Slides (scenes) |
|---|---|---|
| 3–5 min | 3–4 | 6–10 |
| 6–10 min | 4–6 | 10–18 |
| 11–15 min | 6–8 | 16–26 |
| 16–25 min | 8–12 | 24–40 |

Slides cap at 40 (`SlideOutline`). Beyond ~25 min, split into a series.

Set `chapter_skeleton` in `outline.json` to the real chapter starts (minutes) — the
chapters stage and YouTube description use it.

## Attention rules (in addition to creative-laws.md)

- **Something visibly changes every 4–8 seconds.** A reveal, state change, camera move, or
  cut. Holds exist, dead air does not.
- **Pattern interrupt every 30–60 seconds**: switch visual mode — diagram → real code →
  terminal run → zoomed memory view → back. Monotone visuals lose viewers even when the
  narration is good.
- **Open loops.** End each chapter by naming the next question ("but the compiler doesn't
  know when `data` dies — so how does it decide?").
- **Recurring cast.** Reuse the same visual elements (the pointer, the heap block, the
  borrow badge) across chapters so the viewer's mental model accumulates. Change their
  state, not their design.
- **Chapter cards are brief** (≤ 1.5s, the chapter question, not "Part 2").
- **Callback at the recap**: rebuild the payoff from the recurring elements in seconds.

## Building it without losing quality

- One HyperFrames sub-composition per scene; group chapters in the root timeline.
- Build and gate **chapter by chapter**: lint, snapshot its midpoints, look, fix — then
  move on. Don't write 20 scenes and check at the end.
- Keep shared styles (palette, type scale, recurring element components) in one shared
  stylesheet/snippet so chapters stay consistent.
- If using sub-agents, give each one scene (or one chapter) plus the brief, `video-plan.md`,
  the shared styles, and the exact start/end times. Review every returned scene's
  snapshots yourself before accepting it.
- Do a `draft` render of the full video and scrub the contact sheet before the final render.
