---
name: create-short
description: Produce a vertical technical Short/Reel (typically 30–45s, max 60s; up to 3 min if asked) end to end — verified script, the creator's cloned voice, minimal diagram animation in HyperFrames timed to the spoken word, big captions, channel title card/outro, and a post-ready publish kit. Use when someone says "/create-short", "create a short on X", "make a reel about X", or wants a short-form technical video. Asks for the target length if it is not given.
---

# /create-short

You make the whole Short yourself, the same way `/create-video` does. The rules, scene kit
and house style are shared, so read `skills/create-video/references/creative-laws.md` first.
Channel branding comes from the `channel:` section of `config.yaml`.

A Short teaches **exactly one mechanism** ("why C runs a use-after-free that Rust refuses to
build", "where the kernel's stack comes from on every syscall"), and the viewer watches it
happen.

## 0. Parse the request, and ask for the length if it's missing

Usage: `/create-short <topic> [duration] [options]`:

| Option | Default |
|---|---|
| duration (`30s`, `45 sec`, `1 min`, `--duration 50s`) | **none: ask** (the user may have a standing preference such as "30–45s"; use it) |
| `--format vertical\|square\|landscape` | vertical 1080×1920, 30fps |
| `--tone <preset or free-form>` | `punchy` |
| `--no-captions`, `--music`, `--accent <hex>` | captions on, no music, accent from `channel.accent` |
| `--voice <id>` | `voice.default_voice` |

If there's no duration and no standing preference, ask one question:

> How long should this Short be? 30s · 45s · 60s · other

Over 3 minutes → suggest `/create-video`.

## 1. Preflight

Same as `/create-video` step 1.

## 2. Script, verified

Follow `skills/create-video/references/plan.md` §1–2. Use this shape as a starting point,
not a template:

```
Hook (0–3s)        the surprising thing, shown immediately (not a headline)
Setup / mechanism  one mechanism, watched happening; real code and real output
Why it matters     the consequence, made concrete
Payoff (5–8s)      the one-line takeaway on a poster-worthy frame
```

- 3–5 slides. Budget about 2.7 words per second of narration; with the title card, outro and
  pauses, 45s ≈ 95–105 words.
- **Verify everything:**
  - compile and run the code you'll show, in the right environment (Docker for glibc/gcc)
  - read the real source for kernel or library claims, and show excerpts verbatim with the
    file and version
- Spell names phonetically (`G-C-C`, `G-S`) and avoid flippable words (see `/create-video`
  step 2).

```bash
.venv/bin/python cli.py import-outline /tmp/<slug>-outline.json --topic "<topic>" \
  --seo /tmp/<slug>-seo.json --voice <voice>
.venv/bin/python cli.py run --project <id> --only voice        # background
.venv/bin/python cli.py voice-check --project <id>             # read every line
.venv/bin/python cli.py pace --project <id> --gap 0.3
```

**Recording it yourself instead of cloning?** If the user says they'll read the narration
(or has no voice profile and doesn't want one), stop after the script and give them each
slide's `speaker_notes` to record, one file per slide. Then run
`cli.py voice-import --project <id> --dir <folder>` in place of `--only voice`, followed by
`voice-check` and `pace` as usual.

## 3. Storyboard and cues

Write `video-plan.md` and `anchors.json` (`plan.md` §3), then run `cli.py cues --project <id>`.

Short-specific rules:
- **Title card first** (~1.5–1.8s: wordmark + topic), then straight into the hook; the first
  motion lands within 0.3s of the scene starting. No agenda in Shorts.
- **Focus stack:** the element being talked about sits centred between the note and the
  captions, and earlier ones slide up. No dead space top or bottom.
- **Text:**
  - one explanatory note per beat at the top (inside the 220px safe zone)
  - big white captions low, above the bottom ~380px Shorts UI
  - no section labels
- **Code:** at least 34px. Break long lines at natural points rather than shrinking the font.
- **Outro:** 2.5–3s with the wordmark, handle and tagline.

## 4. Compose, check, render, deliver

- Compose with `skills/create-video/assets/scenekit.py`: `set_layout("portrait")`,
  `title_card()`, `focus()`, `group()`, `panel()`, `add_notes(None, …)`, `add_captions()`,
  `outro()` and `write_index()`. Follow `skills/create-video/references/compose.md`.
- Gate: `npx hyperframes check` with 0 errors (fix warnings too), and snapshots of every
  scene reviewed.
- Render: `poster.json` (title card, cursor visible), then `cli.py run --only hyperframes`.
  Verify the length (30–45s preferred, never over 60s), loudness and frames.
- Packaging: `YT_STUDIO_SKIP_VANTAGE=1 .venv/bin/python cli.py run --project <id> --only transcriber,publisher --dry-run-publish`.
- **Publish kit:** write `publish/short.md` (Shorts format in
  `skills/create-video/references/publish.md`):
  - title ≤ 60 characters + `#shorts`, plus 1–2 alternates
  - description with real facts and 3 hashtags
  - tags (≤ 500 characters)
  - a pinned comment
  - a posting slot (`channel.timezone` / `channel.post_time`; slot it into any existing
    `schedule.md`)
  - the related long video, if one exists

Never upload without the user's explicit go-ahead.
