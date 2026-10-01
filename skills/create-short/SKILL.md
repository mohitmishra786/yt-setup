---
name: create-short
description: Produce a vertical technical Short/Reel (30–45s ideal, max 60s) end to end — one verified mechanism, the creator's cloned or self-recorded voice, minimal diagram animation in HyperFrames timed to the spoken word (centred focus-stack layout, big captions, channel title card/outro), a verification gate, and a post-ready publish kit. Use when someone says "/create-short", "create a short on X", "make a reel about X", or wants a short-form technical video. Asks for the target length if it is not given.
---

# /create-short

You make the whole Short yourself: script, voice, storyboard, composition, render and publish
kit. A Short teaches **exactly one mechanism**, and the viewer **watches it happen**, on the
word that names it.

## What this skill contains

| Path | Use it for |
|---|---|
| `references/script.md` | Picking the mechanism, the 3–5 slide shape, hooks, word budget, **verifying claims** |
| `references/shorts-laws.md` | The vertical rules: safe zones, focus stack, sizes, timings, captions, colour |
| `references/compose.md` | Building the composition on the scene kit, sizing recipes, the review loop |
| `references/publish.md` | The `publish/short.md` kit and how to schedule it |
| `templates/build.py` | Starting composition (a rough cut that builds immediately) |
| `scripts/scaffold.py` | One command: HyperFrames init + house style + narration + `build.py` |
| `scripts/verify_short.py` | Final gate (length, size, loudness, contact sheet) and snapshot times |
| `examples/kernel-stack/` | A complete shipped Short: script, anchors, `build.py`, publish kit, lessons |
| `examples/rust-vs-c/` | How a claim was verified (real gcc/glibc and rustc output) before scripting |

**Shared engine.** This skill runs inside the yt-setup repo, and shares its engine with
`/create-video` so the two never drift: the CLI (`cli.py`), the voice pipeline, and the scene
kit at `<repo>/skills/create-video/assets/scenekit.py`. The template and scripts find it by
walking up to the repo root. If it's missing, you're outside the repo: clone
https://github.com/mohitmishra786/yt-setup and work in its `projects/` folder. The shared house
rules are in `<repo>/skills/create-video/references/creative-laws.md`; `shorts-laws.md` adds
the vertical-specific ones.

**Channel branding** (wordmark, handle, tagline, accent, timezone, post time) comes from the
`channel:` section of `config.yaml`. Never hardcode a channel.

## 0. Parse the request

Usage: `/create-short <topic> [duration] [options]`.

| Option | Default |
|---|---|
| duration (`30s`, `45 sec`, `1 min`) | **ask**, unless the user has a standing preference (e.g. "30–45s") |
| `--format vertical\|square\|landscape` | vertical 1080×1920, 30fps |
| `--no-captions`, `--music`, `--accent <hex>` | captions on, no music, `channel.accent` |
| `--voice <id>` | `voice.default_voice`; or "I'll record it myself" → Path B |

If there's no duration, ask one question first: *How long should this Short be? 30s · 45s ·
60s · other.* Anything over 60s should usually be a `/create-video`.

## 1. Preflight

```bash
node --version && ffmpeg -version | head -1 && npx hyperframes doctor
.venv/bin/python -c "import chatterbox, faster_whisper"            # Path A (clone)
ls modules/voice/voices/<voice>/prompt.wav                          # missing -> cli.py voice-prompt
```

If anything is missing, see `docs/GUIDE.md` §1–3. Never fall back to a generic TTS voice
without the user's explicit OK.

## 2. Script, verified → project

Follow `references/script.md`:
- one mechanism, 3–5 slides, ~95–105 words for 45s
- names spelled for the voice, no flippable words
- **every claim verified** (run the code in the right environment, read the real source),
  with the artifacts kept in the project

```bash
.venv/bin/python cli.py import-outline /tmp/<slug>-outline.json --topic "<topic>" \
  --seo /tmp/<slug>-seo.json --voice <voice>
```

## 3. Voice, checked by ear

**Path A (clone):**

```bash
.venv/bin/python cli.py run --project <id> --only voice     # ~4–5× real time on CPU; background it
```

**Path B (the user records it):** give them each slide's `speaker_notes`, one file per slide,
then:

```bash
.venv/bin/python cli.py voice-import --project <id> --dir <folder>
```

Then, either way:

```bash
.venv/bin/python cli.py voice-check --project <id>          # READ every line, not just the score
.venv/bin/python cli.py pace --project <id> --gap 0.3
```

A flipped word ("can't" → "can") can still score 0.9. Fix it by rewording; identical text
reproduces the identical take. Only changed slides regenerate. If the narration total misses
the target by more than ~10%, rewrite.

## 4. Storyboard → cues

Write `projects/<id>/video-plan.md` (one line per beat: spoken phrase → what changes on screen)
and `anchors.json` (`{"cues": [{"id": "s1_free", "slide": 1, "at": "frees memory"}, …]}`).
Phrases must be exact words from that slide. Then:

```bash
.venv/bin/python cli.py cues --project <id>
```

## 5. Compose, following `references/compose.md` and `references/shorts-laws.md`

```bash
.venv/bin/python skills/create-short/scripts/scaffold.py projects/<id>
cd projects/<id>/composition && ../../../.venv/bin/python build.py      # rough cut builds
```

Replace each rough-cut scene with a real one. Use `examples/kernel-stack/build.py` as the
pattern:
- **Focus stack:** the current element is centred, earlier ones slide up.
- **Real code at 34px**, with the source on the first line.
- **One note per beat**, with no section label.
- **Red only on what's wrong.**

Then the review loop: `lint` → snapshots at `verify_short.py --times` → **look at every
frame** → `npx hyperframes check` with 0 errors and warnings addressed.

## 6. Render and verify

```bash
echo '{ "time": 0.9 }' > projects/<id>/poster.json      # title card, cursor visible
.venv/bin/python cli.py run --project <id> --only hyperframes
.venv/bin/python skills/create-short/scripts/verify_short.py projects/<id>   # gate + qa/contact.png
YT_STUDIO_SKIP_VANTAGE=1 .venv/bin/python cli.py run --project <id> \
  --only transcriber,publisher --dry-run-publish
```

Look at `qa/contact.png` before calling it done.

## 7. Publish kit

Write `projects/<id>/publish/short.md` following `references/publish.md`:
- title ≤ 60 characters + `#shorts`, plus 2 alternates
- a factual description with 3 hashtags
- tags
- a pinned comment with caveats and a question
- a posting slot in `channel.timezone`, added to any existing `schedule.md`
- the related long video

Also write `share-copy.txt`. **Never upload without the user's explicit go-ahead.**

## Gates (do not skip)

- [ ] Length stated or asked; final is 30–45s (never over 60s).
- [ ] Every claim verified; code and output on screen are real and cited.
- [ ] `voice-check` read line by line; no flipped meanings.
- [ ] Every beat comes from `cues.json`; no hand-typed times.
- [ ] Snapshots reviewed: focus stack centred, nothing blank, text minimums met, red only on
      what's wrong, diagram matches reality.
- [ ] `hyperframes check`: 0 errors. `verify_short.py`: no ✗; contact sheet looked at.
- [ ] `publish/short.md` written and length-checked.
