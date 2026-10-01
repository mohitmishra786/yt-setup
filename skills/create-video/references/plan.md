# Plan: script, then storyboard

Two artifacts, written in this order, both before any composition code:

1. `outline.json` + `seo.json` — the **script** (what is said). The voice stage reads this.
2. `projects/<id>/video-plan.md` — the **storyboard** (what is seen, when). Written after
   narration audio exists so scene durations come from real audio, not estimates.

## 1. Answer the rubric first

Before writing a word of script, answer these in your head (or at the top of the plan):

1. What is the one mechanism (short) / the chapter spine (long) this video teaches?
2. Who is it for? What do they already know? What do they get wrong?
3. What is the surprising hook — the crash, the wrong intuition, the impossible number?
4. What real material can be shown? (code that compiles or fails, compiler output,
   memory layout, syscall trace, benchmark with source)
5. What can be *watched happening* — what moves, fills, breaks, flips, travels?
6. What is the payoff line — the one sentence the viewer repeats to a friend?
7. What tone fits (see `creative-laws.md` → Tones)?
8. Are there any facts you are not sure of? Verify them (docs, spec, man page, or by
   actually compiling/running the code) before they go into narration.

## 2. Script → `outline.json` / `seo.json`

Word budget from the requested duration: spoken pace ≈ 150 wpm ≈ **2.5 words / second**.
A 45s short ≈ 110 words; a 10-minute video ≈ 1,500 words. Leave ~5–8% of the runtime for
silent holds (hook beat, payoff hold, chapter breathers).

`outline.json` (schema: `core/schemas.py:SlideOutline`) — one **slide = one narration
unit = one scene** in the composition:

```json
{
  "title": "Rust vs C: Memory Safety at Compile Time",
  "target_duration_minutes": 1.0,
  "audience": "Systems programmers learning Rust",
  "slides": [
    {
      "index": 1,
      "title": "One dangling pointer",
      "speaker_notes": "Exact words to be spoken. Conversational. No stage directions.",
      "visual_beat": "What the viewer watches happen, in order.",
      "bullets": []
    }
  ]
}
```

Constraints: 3–40 slides, each with `index` (1, 2, …); `target_duration_minutes` ≥ 1.0 (use 1.0 for shorts);
`speaker_notes` must be plain speakable text (no markdown, no code blocks — say
"ampersand data", not `&data`).

Shorts: 3–6 slides of 5–15s. Long-form: see `long-form.md` for the chapter layout
(typically 30–90s per slide).

`seo.json` (schema: `core/schemas.py:SEOMetadata`): `title` (≤ 100 chars, add `#Shorts`
for shorts), `description`, `tags`, `hashtags`, `thumbnail_text`, `hook_line`.

## 3. Storyboard → `projects/<id>/video-plan.md` + `anchors.json`

Read `audio/durations.json` and `audio/words.json` first (both written by the voice
stage, then shifted by `cli.py pace`). Write the explanatory note for every beat in the plan too
(no section labels) — they are part of the storyboard. Scene N lasts at least `durations[N-1]` (plus any planned silent hold). The total
must match the requested length within ±10%.

```markdown
# Video Plan: [title]

## Format
- Kind: short | long — Canvas: 1080x1920 | 1920x1080 @ 30fps
- Requested duration: [as asked] — Narration total: [sum]s
- Tone: [preset] — Accent: [one hex, e.g. #5aa9f0]

## Angle / Hook / Payoff
[premise] / [first frame + first motion] / [final line + the frame it lands on = poster]

## Cast (persistent actors)
- [actor]: [what it is, how it looks, where it lives on stage, which states it goes through]

## Storyboard
### Scene 1 — [name] — [duration]s (audio/slide_01.mp3)
- Narration: "…verbatim…"
- Stage at start: [which actors are where, sizes as % of frame]
- Beats (each anchored to a spoken word or phrase):
  - "dangling pointer" → pointer arrow draws to the block (accent)
  - "free" → block turns dashed/ghost; arrow stays (turns --bad)
- Stage at end → morph into scene 2: [what moves where]
```

Then write `projects/<id>/anchors.json` — one entry per beat, using the **exact words
from the narration** (the phrase must appear in that slide's `speaker_notes`):

```json
{"cues": [
  {"id": "s1_arrow",  "slide": 1, "at": "dangling pointer"},
  {"id": "s1_free",   "slide": 1, "at": "free", "offset": -0.05},
  {"id": "s2_ub",     "slide": 2, "at": "undefined behavior", "edge": "end"},
  {"id": "s2_free_2", "slide": 2, "at": "free", "occurrence": 2}
]}
```

`edge` = `start` (default, beat lands as the word begins) or `end`; `offset` nudges
seconds; `occurrence` picks the Nth match. Resolve them:

```bash
.venv/bin/python cli.py cues --project <id>    # -> projects/<id>/cues.json
```

It fails loudly on any phrase it can't find — fix the anchor, don't guess a time.

Rules while storyboarding:

- **Every beat is an anchor.** If a visual change isn't tied to a word, ask why it exists.
- **Something changes every 2–4s** (shorts) / **4–8s** (long-form) — a state change, a
  morph, or a camera move. Holds are fine; dead screens are not.
- **Plan the stage, not slides.** Where each actor sits and how big (% of frame); the
  active group fills 70–90% of the width.
- **Show code, not descriptions of code.** If the narration says "this won't compile",
  the next thing on stage is the compiler error.
