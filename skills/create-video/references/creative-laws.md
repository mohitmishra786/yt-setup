# Creative laws — technical explainers (shorts and long-form)

The look is **minimal, flat, near-monochrome diagrams that transform in step with the
narration** — in the spirit of the CoreDumpped channel (slide-deck-style morph animation),
built with HyperFrames. Production discipline adapted from
[latent-spaces/brag](https://github.com/latent-spaces/brag) (MIT).

## The laws

**The voice drives the picture.** Every visual change lands on the word that names it
(±0.15s). When the narration says "free", the block frees — not a second before, not a
second after. This is enforced mechanically: anchors → `cli.py cues` → exact times (see
`compose.md`). Never time reveals by guessing seconds.

**Persistent actors, not slides.** The things being explained (a pointer, a heap block, a
thread, a page) are objects that stay on stage and *change state*: move, resize, split,
recolor, get crossed out. Scene changes are morphs — the same object moving to its new
place — or a camera push into a detail. Hard cuts only between chapters.

**One mechanism, watched happening.** A viewer should see the mechanism work. A pointer
arrow that keeps pointing after its block goes dashed beats a box labelled "dangling".

**Show the real thing.** Real code that compiles (or fails exactly as shown), real
compiler/terminal output, real layouts and syscall names, real numbers with a source.
Illustrative values (an address like `0x7ffd…`) are fine; invented facts are not.

**Text explains, it doesn't decorate.** One explanatory line at the top that changes at
each beat ("Ask for 24 bytes → glibc hands out a 32-byte chunk"). It should be accurate,
concrete and at most two lines. **No section labels** like `C · USE AFTER FREE` or
`01 · …` by default: they are clutter, and YouTube chapters carry that information.
Diagrams keep short labels, addresses and code. No badges or bullet lists, and don't repeat
the same phrase as a big diagram label when the note and caption already say it.

**Focus stack.** The thing being talked about sits in the centre of the frame. When the next
element arrives, earlier ones slide up (and dim unless they're still being referenced) and
the newcomer takes the centre. The group stays vertically centred between the note and the
captions, so there is no dead space at the top or bottom. Use `Scene.focus()` in
`scenekit.py`; move multi-part diagrams as one `Scene.group()`.

**Never a blank frame.** Every scene opens with its label, note and some of its diagram
already visible (faint outlines of what's coming are fine). No empty canvas waiting for the
first cue.

**Breathe.** Nothing should feel rushed: ~0.75s between sentences (`cli.py pace`) and ~1s
between scenes. Going over the requested length by 10–20% for clarity is fine.

**Readable.** Any text a viewer must read stays settled ~0.3s/word (min ~1.2s; short
labels ~0.8s). Code: highlight the line being spoken; ~0.5s per line read.

**Fill the frame.** Diagrams are big: the active group spans 70–90% of the frame width.
Nothing floats in the top third over an empty canvas, and there is no big empty band above the
captions. The focus stack handles vertical balance.

**One focus.** At most one element is in the accent color at any moment — the one being
talked about. Everything else is neutral grey. `--bad` (red) only for crash / UB /
rejected, and only on the element that is bad.

**Calm motion.** Ease-in-out, 0.4–0.8s moves, no bounce/elastic, no shake, no flashes,
no slams. Motion is how the viewer's eye is led, not decoration.

**Every frame postable.** Freeze any frame: clean, deliberate, no overlaps, no arrows
through labels, no half-rendered text.

## Visual identity — the house style

Use `skills/create-video/assets/house.css` (copy into `composition/assets/`). It defines:

- Background `#121417`, surfaces `#1c1f24` / `#252930`, lines `#3a3f48`.
- Text `#e9eaec`, secondary `#9aa0a8`, tertiary `#5d636c`.
- **One accent per video** (`--accent`, default soft blue `#5aa9f0`; choose once, keep it).
- `--bad` `#e5645c` for failure states only.
- Inter for text, JetBrains Mono for code/addresses.
- Flat fills, 3px strokes, 10px radius. No glows, drop shadows, noise, or coloured light.
- **Background:** neutral charcoal with a soft centre lift and a faint white dot grid
  (`BG_CSS` / `DOTS_CSS` in `scenekit.py`). No colour in the background, ever.

Color budget per frame: greys + at most one accent element + (only if something is
failing) one `--bad` element.

## Type and layout minimums (on the rendered canvas)

| Element | Vertical 1080×1920 | Landscape 1920×1080 |
|---|---|---|
| Key phrase (rare) | 96–130px, 800 weight | 80–110px |
| Labels on shapes | ≥ 42px | ≥ 34px |
| Code | ≥ 38px mono, ≤ 12 lines | ≥ 32px mono, ≤ 16 lines |
| Addresses / small | ≥ 34px | ≥ 28px |
| Captions | 60–68px bold white | 44–52px bold white |

**Vertical safe zones** (Shorts/Reels/TikTok UI): keep content out of the top ~220px,
bottom ~380px, right ~140px.

## Captions

- Shorts: on by default. White, bold, 2–4 words per chunk; the spoken word at full
  opacity, the rest at ~55%. **No colored words.** Placed above the bottom safe zone,
  never over the active diagram.
- Long-form: on by default too (bottom, 44px bold, up to ~7 words); off with `--no-captions`.
- Caption words must match the script exactly (use `audio/words.json`, not raw ASR).

## Channel branding (from `config.yaml` → `channel:`)

The wordmark, handle, tagline, accent colour, timezone and posting slot all come from the
`channel:` section of `config.yaml`. `scenekit.py` and `build_shorts.py` read it, so never
hardcode a channel. The wordmark is drawn with every part in ink except the last, which is in
the accent colour, followed by a blinking `_` cursor (e.g. `Kernel` + `Kafe_`).

Order: **intro → agenda → content → outro**.

- **Intro** (2–3s, silent): the wordmark with the video's topic title under it
  (`title_card()`).
- **Agenda** (4–5s, narrated, long-form only): one short line in the cloned voice naming the
  4–5 topics ("Here's the plan: …"). Each topic lights up as it's said, then the full list
  holds. Write it as the *last* outline slide, so editing it never re-synthesises the others,
  and place it second in the composition. Use dashes, not numbers.
- **Outro** (3s): wordmark, handle and tagline (`outro()`). YouTube end-screen elements need
  at least 5s, so lengthen the outro if the creator plans to add them.
- **Shorts:** a ~1.5–1.8s title card, then straight into the hook; a 2.5–3s outro; no agenda.
- **Poster/thumbnail:** the intro frame with the cursor visible. It's baked into frame 0, so
  it matches the first thing the video shows (otherwise viewers see the card "twice").
- **Chapters:** the first chapter starts at 0:00 and absorbs the intro and agenda (YouTube
  needs each chapter to be at least 10s).

## Tones

Tones change pacing and energy — never the palette or the no-glow rule.

| Tone | Feel | Pacing |
|---|---|---|
| `coredump` (default) | Calm, precise, curious; diagrams do the talking | Medium holds, morphs, slow push-ins |
| `punchy` (shorts default) | Tighter, faster, still minimal | Shorter holds, quicker morphs, a cut on the hook |
| `lecture` | Patient, step by step | Long holds, builds one element at a time |
| `deadpan` | Dry; the absurdity of the bug is the joke | Long still holds, big empty space around one object |

## Audio

- **Narration is the product.** Cloned voice only (never a generic TTS voice without the
  user's explicit OK), mastered to −16 LUFS by the voice stage.
- Music: off by default. If the user wants it: a soft, sparse bed ducked to ≤ −26 dB under
  speech, no drums/drops.
- SFX: none by default. If used: very quiet, only on state changes (a soft tick on a code
  line, a low thud on a crash).
- Never waveform bars, equalizers, or note graphics.
