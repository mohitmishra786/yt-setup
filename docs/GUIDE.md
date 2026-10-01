# Make technical YouTube videos with your own voice — the complete guide

This repo turns a topic into a finished YouTube package:

- a long-form explainer (3–25 min) or a Short (30–60 s)
- narrated in **your** voice, either cloned from a few minutes of your recordings or read by you
- with minimal diagram animation that moves **on the word being spoken**
- captions, a channel intro and outro, a thumbnail frame and chapters
- 3–5 Shorts cut from each long video
- a post-ready publish kit: titles, descriptions, tags, a pinned comment and a 7–10 day schedule

You drive it from a coding agent (Claude Code, OpenCode, Codex, …) with one command:

```
/create-video how TCP congestion control works 8 min
/create-short why a use-after-free compiles in C but not in Rust 45s
```

The agent is the writer, director and motion designer. This repo provides the tools it runs:
voice cloning, word timing, the scene kit, rendering, Shorts and packaging. **No paid API is
needed.** Everything renders on your machine.

---

## 0. What you'll need

| | Needed for | Check |
|---|---|---|
| macOS or Linux (Windows via WSL2) | everything | — |
| Python **3.11+** and [uv](https://docs.astral.sh/uv/) | pipeline, voice, timing | `python3 --version`, `uv --version` |
| Node.js **22+** | HyperFrames (rendering) | `node --version` |
| FFmpeg | audio and video | `ffmpeg -version` |
| A coding agent | `/create-video`, `/create-short` | Claude Code, OpenCode, Codex, … |
| Docker (optional) | running demo code in a clean Linux, e.g. real glibc output | `docker --version` |
| ~12 GB free disk, 16 GB RAM | PyTorch, voice model, Whisper, headless Chrome | — |

## 1. Install

```bash
git clone https://github.com/mohitmishra786/yt-setup.git && cd yt-setup
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e ".[dev,voice]"   # voice = Chatterbox cloning
npx hyperframes doctor        # downloads headless Chrome on first run; Chrome + FFmpeg must be ✓
.venv/bin/python -m pytest -q # should be all green
```

- On **Claude Code**, the skills are picked up automatically from `.claude/skills/`.
- On **OpenCode**, they come from `.opencode/skills/` (plus the slash commands in `opencode.json`).
- On **Codex and others**, they come from `.agents/skills/`.
- The HyperFrames skills that the video skills rely on are installed once with
  `npx hyperframes skills`.

## 2. Set up your channel

```bash
cp config.yaml.example config.yaml     # config.yaml is gitignored, so it stays yours
```

Edit the `channel:` section. It drives the intro card, outro, Shorts branding, accent colour
and posting schedule:

```yaml
channel:
  name: ByteBistro
  wordmark: [Byte, Bistro]       # last part is drawn in the accent colour: "Byte" + "Bistro_"
  handle: "@bytebistro"
  url: https://www.youtube.com/@bytebistro
  tagline: "Subscribe for more systems deep dives"
  accent: "#5aa9f0"              # the ONE accent colour; everything else stays grey
  timezone: Europe/Berlin
  post_time: "17:00"
```

Also set `voice.default_voice` to the voice id you'll create in the next step.

## 3. Your voice: pick one path

### Path A: clone your voice (recommended; write any script and it sounds like you)

1. **Record 2–5 minutes** of yourself reading naturally:
   - a quiet room, the same mic and distance throughout
   - no music, no other speakers
   - [`docs/VOICE_RECORDING_SCRIPT.md`](VOICE_RECORDING_SCRIPT.md) is a good text to read
   - several takes are fine; `.m4a`, `.wav` and `.mp3` all work
   - only clone a voice you own or have explicit permission to use
2. **Build the profile:**
   ```bash
   .venv/bin/python cli.py prepare-voice --voice alex \
     --audio recordings/alex/take1.m4a --audio recordings/alex/take2.m4a --consent
   ```
3. **Pick the 10 seconds that define you.** Chatterbox only listens to about the first 10 s of
   its reference, so choosing them matters more than anything else:
   ```bash
   .venv/bin/python cli.py voice-prompt --voice alex
   ```
   This writes `prompt.wav` (the best window it found) plus three audition clips in
   `modules/voice/voices/alex/prompt_candidates/`. Listen to them. If another one sounds more
   like you:
   ```bash
   .venv/bin/python cli.py voice-prompt --voice alex --source recordings/alex/take2.m4a --start 73.0
   ```

Generation runs on CPU at about 4–5× real time (a 3-minute script takes ~15 min). Each sentence
is generated with a fixed seed, checked with Whisper and retaken if it doesn't match, then
mastered to −16 LUFS. Finished slides are reused, so editing one sentence regenerates only
that slide.

### Path B: record the narration yourself (no cloning)

Let the agent write the script (or write it yourself), then read each slide's
`speaker_notes` into its own file: `slide_01.wav`, `slide_02.wav`, … Any audio format works,
and files sorted by name are fine too.

```bash
.venv/bin/python cli.py voice-import --project <id> --dir ~/narration/my-video
```

Your takes are trimmed, mastered to −16 LUFS and timed word by word, so captions, animation
cues, pacing and Shorts work exactly as they do with a cloned voice. Tell the agent you're on
Path B. It will stop after writing the script, wait for your recordings, then continue from
the storyboard.

## 4. Make a video

Open the repo in your agent and type:

```
/create-video <topic> <length>        e.g.  /create-video how DNS resolution works 8 min
/create-short <topic> <length>        e.g.  /create-short what a page fault really costs 45s
```

If you leave out the length, the agent asks for it. What happens next:

1. **Script.** The agent researches and verifies every claim. It compiles and runs any code it
   shows (in Docker when the exact environment matters) and reads real source for kernel or
   library claims. It then writes `outline.json` and `seo.json`.
2. **Narration**, in your cloned voice or imported:
   - `voice-check` prints the script next to what was actually heard; the agent rewords
     anything ambiguous ("can't" vs "can")
   - `pace` adds breathing room
3. **Storyboard.** Every visual change is tied to a spoken phrase (`anchors.json` →
   `cli.py cues` → exact times).
4. **Composition**, built with the scene kit (`skills/create-video/assets/scenekit.py`):
   - centred "focus stack" layout and flat grey diagrams with one accent colour
   - captions, one explanatory note per step, your intro card and outro
   - the agent snapshots and reviews frames, and HyperFrames `check` must pass
5. **Render** to `final.mp4` (1080p, 30fps, −16 LUFS narration). The intro frame is baked in as
   the thumbnail frame.
6. **Shorts and publish kit** (long-form): 3–5 Shorts plus `publish/video.md`,
   `publish/shorts.md` and `publish/schedule.md`.

Nothing is uploaded unless you say so.

**What you get**, in `projects/<id>/`:

```
final.mp4          the video                    poster.jpg      thumbnail frame
shorts/short_NN.mp4  Shorts (long-form)         chapters.txt    YouTube chapters
transcript.srt     captions file to upload      share-copy.txt  1–3 sentence post
publish/           titles, descriptions, tags, pinned comment, schedule
outline.json / video-plan.md / anchors.json / composition/   the editable sources
```

**Changing things.** Ask the agent ("make scene 3 slower", "reword the hook"):
- **Script edits** regenerate only the changed slides.
- **Visual edits** rebuild in seconds (`composition/build.py`).
- **Manual edits:** `npx hyperframes preview` in `projects/<id>/composition/` opens Studio, a
  timeline editor.

## 5. Without an agent: the manual path

The same pipeline, one command at a time. You write the JSON and the composition yourself.

```bash
.venv/bin/python cli.py import-outline outline.json --topic "My topic" --seo seo.json --voice alex
.venv/bin/python cli.py run --project <id> --only voice          # or: voice-import --dir …
.venv/bin/python cli.py voice-check --project <id>
.venv/bin/python cli.py pace --project <id> --gap 0.45
.venv/bin/python cli.py cues --project <id>                      # anchors.json -> cues.json
# write projects/<id>/composition/build.py on top of scenekit.py (see the skills' compose.md)
.venv/bin/python cli.py run --project <id> --only hyperframes    # check + render + poster
.venv/bin/python cli.py run --project <id> --only transcriber,chapters,publisher --dry-run-publish
.venv/bin/python skills/create-video/assets/build_shorts.py projects/<id>   # needs shorts.json
```

Formats and rules live in `skills/create-video/references/`: `plan.md` (outline and anchors),
`compose.md` (scene kit), `deliver.md`, `publish.md`, `creative-laws.md` (the look),
`long-form.md` (chapter structure).

## 6. Publishing

- Upload manually using `publish/` (copy-paste fields, with lengths already checked), or use
  the built-in `publisher` stage: put a YouTube OAuth desktop client JSON at
  `.credentials/client_secret.json` and drop `--dry-run-publish`. It is **private by
  default**, and public uploads need `--privacy public --confirm-public`.
- For every Short, set **Related video** to the long video in YouTube Studio.
- `schedule.md` is a 7–10 day plan: the long video on day 1, a Short every 1–2 days, a
  community poll, and a review day with concrete thresholds.

## 7. Make it yours

| Want | Change |
|---|---|
| Different accent colour or branding | `config.yaml` → `channel:` |
| Different look (spacing, type sizes, background) | `LAYOUTS`, `BG_CSS`, `DOTS_CSS` in `skills/create-video/assets/scenekit.py` |
| Different creative rules (pacing, captions, notes) | `skills/create-video/references/creative-laws.md` |
| Correct how a spoken name appears in captions | `caption_word()` in `scenekit.py` (e.g. `G-lib-C` → `glibc`) |
| Faster or more careful voice checks | `YT_STUDIO_VOICE_ASR_MODEL` (default `medium`), `YT_STUDIO_VOICE_TRIES` |
| Render quality | `YT_STUDIO_HF_QUALITY=draft\|standard\|high` |

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Voice generation crawls (seconds per step) | Leave it on CPU (the default). MPS slows down badly on long runs; `YT_STUDIO_VOICE_DEVICE=mps` only for short tests |
| `perth` / `pkg_resources` error when loading Chatterbox | `uv pip install --python .venv/bin/python "setuptools<81"` (already in the `voice` extra) |
| `.venv/bin/pip: not found` | uv venvs have no pip; use `uv pip install --python .venv/bin/python …` |
| Narration says the wrong word | Read `cli.py voice-check`, **reword** the sentence (same text means the same take), re-run `--only voice` |
| Retakes on every sentence with names or jargon | Spell names phonetically in `speaker_notes` (`J-E-malloc`) and map them back in `caption_word()` |
| `cli.py cues` fails: phrase not found | The anchor must use the exact words of that slide's `speaker_notes` |
| `hyperframes snapshot` navigation timeout | Add `--timeout 60000`, and don't snapshot while voice generation is using the CPU |
| `hyperframes check` contrast errors | Use `ink2` (not `ink3`) for any readable text |
| You see the intro card "twice" | Bake the poster from the intro frame (`poster.json` time inside the intro) |
| Video is short of the requested length | Add real content to the script; `pace` adds breathing room; never pad with dead air |

## 9. Privacy

These are gitignored and never committed: `config.yaml`, `.env`, `.credentials/`, `projects/`
(all renders), `recordings/`, `modules/voice/voices/*/` (your voice profile), and every
`.mp4`, `.mp3` and `.wav`. Clone only a voice you own or have explicit permission to use.
