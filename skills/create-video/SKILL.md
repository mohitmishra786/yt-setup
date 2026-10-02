---
name: create-video
description: Produce a long-form (typically 3–25 minute) technical/CS explainer video end to end — verified script, the creator's cloned voice, minimal diagram animation in HyperFrames timed to the spoken word, captions, channel intro/outro, 3–5 Shorts cut from it, and a post-ready publish kit with a schedule. Use when someone says "/create-video", "create a video on X", "make an explainer video about X", or wants an end-to-end long-form technical YouTube video. Asks for the target length if it is not given.
---

# /create-video

You make the whole video yourself: script, narration, storyboard, HyperFrames composition,
render, Shorts and publish kit. Use this repo's CLI for voice, timing and packaging, and
HyperFrames for visuals. No LLM API key is needed: you are the writer, director, motion
designer and reviewer.

**The quality bar.** The viewer *watches the mechanism happen*: the block frees as the voice
says "free". Every frame is clean and deliberate, there's never a blank screen, and every
technical claim has been verified. Read `references/creative-laws.md` before planning and
check against it before rendering.

**The channel** (name, wordmark, handle, tagline, accent colour, timezone, posting slot) comes
from the `channel:` section of `config.yaml`, and the scene kit reads it automatically. Never
hardcode a channel name. If `config.yaml` has no `channel:` section, ask the user for their
channel name and handle once, and suggest they add it (see `docs/GUIDE.md`).

## 0. Parse the request, and ask for the length if it's missing

Usage: `/create-video <topic> [duration] [options]`. Options can be flags or plain language:

| Option | Default |
|---|---|
| duration (`12m`, `10 min`, `8-10 minutes`, `--duration 15m`) | **none: ask** |
| `--format landscape\|vertical` | landscape 1920×1080, 30fps |
| `--tone <preset or free-form>` | `coredump` (creative-laws → Tones) |
| `--no-captions`, `--music`, `--accent <hex>` | captions on, no music, accent from `channel.accent` |
| `--voice <id>` | `voice.default_voice` in config.yaml |

**If the user didn't state a duration, stop and ask before doing anything else.** Ask one
short question, using your agent's question tool if it has one:

> How long should this video be? 5 min · 8 min · 10 min · 12–15 min · other

Ask for the topic in the same question if it's missing too. Ranges are fine; aim for the
middle. Under ~2 minutes → suggest `/create-short`. Record the answer in `video-plan.md`.

## 1. Preflight (once per machine; fix or report, don't guess)

```bash
node --version                 # >= 22
ffmpeg -version | head -1
npx hyperframes doctor         # Chrome + FFmpeg + whisper are what matter
.venv/bin/python -c "import chatterbox, faster_whisper; print('ok')"
ls modules/voice/voices/<voice>/prompt.wav   # missing -> cli.py voice-prompt --voice <voice>
```

If something is missing, follow `docs/GUIDE.md` §1–3 (install, voice profile, prompt clip).
Never fall back to a generic TTS voice without the user's explicit OK.

Set `HYPERFRAMES_NO_TELEMETRY=1` (and `HYPERFRAMES_SKIP_SKILLS=1` for `init`) for a local run.
Load the HyperFrames skills listed in `references/compose.md`. On agents other than Claude
Code, run `npx hyperframes skills` once to install them.

## 2. Script → project

Follow `references/plan.md` §1–2 and `references/long-form.md`:
- **Verify every technical claim.** Compile and run any code you show, ideally in the target
  environment (e.g. a Debian container for glibc behaviour). Read real source for kernel or
  library claims. Show real output only.
- Word budget: about 2.5–3 words per second of runtime.
- Write `speaker_notes` as plain speakable text, and spell names the way they should sound:
  `G-lib-C`, `J-E-malloc`, `mee-malloc`, `G-C-C`, `G-S`. Captions map them back automatically
  (`caption_word()` in `assets/scenekit.py`; add new mappings there).
- Avoid words a listener (or Whisper) can flip: prefer "refuses to use it" over "can't
  trust it".
- Put the **agenda line** ("Here's the plan: A, B, C, D, and E.") as the **last** outline
  slide. It plays second in the video, but appending it means later edits never renumber the
  other slides.

```bash
.venv/bin/python cli.py import-outline /tmp/<slug>-outline.json --topic "<topic>" \
  --seo /tmp/<slug>-seo.json --voice <voice>
```

Every slide needs `"index": 1, 2, …`. The command prints the project id; everything below
lives in `projects/<id>/`.

## 3. Narration, then check it by ear (via ASR)

```bash
.venv/bin/python cli.py run --project <id> --only voice      # slow: run in the background
.venv/bin/python cli.py voice-check --project <id>           # script vs what was heard
.venv/bin/python cli.py pace --project <id> --gap 0.45       # breathing room between sentences
```

- The voice stage generates each sentence with a fixed seed, checks it with Whisper, retakes if
  needed, then masters the result to −16 LUFS. It also writes `audio/durations.json` and
  `audio/words.json`.
- It runs on CPU at about 4–5× real time. MPS is off on purpose, because it collapses on long
  runs.
- **Read every `voice-check` line.** A single flipped word ("can't" → "can", "program" →
  "problem", "recursion" → "percussion") can pass a 0.9 score. Fix it by **rewording** the
  sentence, since identical text reproduces the identical take, then re-run `--only voice`.
  Only changed slides regenerate (`audio/slide_XX.key`).
- `pace` adds silence at sentence breaks without re-synthesis and shifts the word timings. It
  is safe to re-run.
- If the total is more than ~10% short, add real content rather than dead air. Running 10–20%
  long for clarity is fine.

**Recording it yourself instead of cloning?** If the user says they'll read the narration
(or has no voice profile and doesn't want one), stop after the script and give them each
slide's `speaker_notes` to record, one file per slide. Then run
`cli.py voice-import --project <id> --dir <folder>` in place of `--only voice`, followed by
`voice-check` and `pace` as usual.

## 4. Storyboard and cues

Write `video-plan.md` and `anchors.json` following `references/plan.md` §3. Every visual
change is anchored to a spoken phrase, and every scene gets one explanatory note per beat.
Then:

```bash
.venv/bin/python cli.py cues --project <id>    # -> projects/<id>/cues.json; fails loudly on misses
```

## 5. Compose with the scene kit

Follow `references/compose.md`:
- Scaffold `composition/`, copy `assets/house.css` and the voice files in.
- Write `composition/build.py` on top of **`assets/scenekit.py`**: `Scene`, `focus()`,
  `group()`, `panel()`, `add_notes()`, `add_captions()`, `title_card()`, `outro()` and
  `write_index()`.
- Video structure, in order:
  1. **intro**: wordmark + topic title, 2–3s, silent
  2. **agenda**: the narrated last slide, 4–5s
  3. **content scenes**
  4. **outro**: 3s
- Use the **focus stack** for anything that builds up. The current element sits centred;
  earlier ones slide up and dim. There are no section labels and no blank frames.

Build → `npx hyperframes lint` → snapshot 0.5s into every scene and ~0.8s after key cues →
**look at every frame** → fix → `npx hyperframes check` must show 0 errors, and fix
warnings too.

## 6. Render and deliver

Follow `references/deliver.md`:
- `poster.json`: the intro frame with the wordmark cursor visible. It's baked into frame 0.
- A draft render plus a contact-sheet review, then the final render:
  ```bash
  .venv/bin/python cli.py run --project <id> --only hyperframes
  ```
- `YT_STUDIO_SKIP_VANTAGE=1 .venv/bin/python cli.py run --project <id> --only transcriber,chapters,publisher --dry-run-publish`
- Rewrite `chapters.txt` from the real scene starts. The first chapter starts at 0:00 and
  covers the intro and agenda; every chapter must be at least 10s.

## 7. Shorts + publish kit

Follow `references/publish.md`:
- Cut 3–5 Shorts with `assets/build_shorts.py`: **30–45s each, never over 60s**, on scene
  boundaries, each standing alone. Review frames from each.
- Write `publish/video.md`, `publish/shorts.md` and `publish/schedule.md`. Schedule times use
  `channel.timezone` and `channel.post_time`.

Also write `publish/upload.json` (the machine plan: `skills/upload-video/references/plan-format.md`)
so `/upload-video` can schedule everything. Never upload or publish without the user's explicit
go-ahead; uploading and scheduling is the `/upload-video` skill.

## Gates (do not skip)

- [ ] Duration was stated by the user or asked for.
- [ ] Every technical claim verified; shown code and output are real.
- [ ] Narration is the cloned voice; `voice-check` read line by line, no flipped meanings.
- [ ] Every visual beat comes from `cues.json` (anchors), with no hand-typed times.
- [ ] Snapshots reviewed:
  - focus stack centred, nothing blank
  - house palette only (greys + one accent + red only for failures)
  - text minimums met, no arrows through labels
- [ ] `npx hyperframes check`: 0 errors, warnings addressed.
- [ ] Final contact sheet reviewed; poster frame is settled.
- [ ] Shorts 30–45s (≤ 60s), frames reviewed; `publish/` written and length-checked
      (titles ≤ 100, tags ≤ 500, descriptions ≤ 5000 characters).
