# yt-studio

Local-first YouTube creation pipeline. Turn a topic (or source document) into:

**script -> branded slides -> narrated video -> transcript -> chapters -> SEO metadata -> Shorts -> optional YouTube upload**

Companion to [Vantage](https://www.tryvantage.site) (long video to keyword-targeted clips). This repo owns everything upstream of Vantage and reuses it via the `shorts/` adapter.

| Stage | Default stack | Notes |
|---|---|---|
| Script / SEO / chapters | Anthropic Claude API | Uses `ANTHROPIC_API_KEY`; offline stub without key |
| slides | `python-pptx` + branded theme | Editable `.pptx` |
| PPTX / frames | Pillow renderer; LibreOffice if installed | 1920x1080 PNG frames |
| Voice | Chatterbox (MIT) when installed; **edge-tts** default fallback | Also: mac_say, ElevenLabs, XTTS, silence |
| Video assembly | FFmpeg (image + audio per slide, optional crossfade) | Real H.264/AAC MP4 |
| Transcription | faster-whisper; WhisperX when installed | Word timestamps + SRT/VTT |
| Shorts | Vantage HTTP adapter; local keyword FFmpeg fallback | Vertical 9:16 clips |
| Publish | YouTube Data API v3 | **private by default**; dry-run without OAuth |

License: **MIT** (this repo).

**Voice license note:** Chatterbox (Resemble AI) is MIT and safe for commercial use. **XTTS v2 (Coqui) is not MIT** — verify Coqui terms before monetizing with XTTS.

---

## Status

Phases 0-6 implemented:

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Scaffold, resumable pipeline, CLI, tests | Done |
| 1 | Scriptwriter (Claude + schemas) + Slidebuilder | Done |
| 2 | Voice engines + FFmpeg video assembler | Done |
| 3 | Transcriber, chapters, subtitle burn-in | Done |
| 4 | Vantage shorts + local fallback | Done |
| 5 | Publisher, thumbnails, FastAPI web UI | Done |
| 6 | BGM, batch mode, templates, polish | Done |

---

## Project layout

```
yt-setup/
├── cli.py
├── config.yaml.example
├── .env.example
├── pyproject.toml
├── core/                 # config, checkpoint, pipeline, schemas, llm client
├── modules/
│   ├── scriptwriter/     # Claude / NVIDIA NIM outline + SEO
│   ├── storyboard/       # Visual choreography (storyboard.json)
│   ├── scenegen/         # Design tokens, component library, Playwright renderer & Visual QA
│   ├── voice/            # Chatterbox / edge-tts / ElevenLabs / XTTS
│   ├── video_assembler/  # Scene concatenation + audio muxing + BGM
│   ├── transcriber/      # faster-whisper / WhisperX
│   ├── chapters/         # YouTube chapter markers
│   ├── shorts/           # Vantage adapter / local extraction
│   ├── subtitles/        # FFmpeg burn-in
│   ├── thumbnail/        # Pillow thumbnails
│   └── publisher/        # YouTube Data API v3
├── projects/             # per-video artifacts (gitignored)
├── web_ui/               # FastAPI + static dashboard
├── tests/
└── docs/
```

Each run creates `projects/<YYYY-MM-DD_slug>/` with intermediate and final files so any stage can be re-run alone.

---

## No Anthropic API? (Claude Pro UI is enough)

Claude **Pro** (claude.ai) does not give you an API key. You do not need one.

**Best path:** build the deck in Claude.ai / PowerPoint, fill **speaker notes**, export `.pptx`, then:

```bash
python cli.py import-pptx ./my-deck.pptx --topic "My video" --voice mohit
python cli.py run --project <id> --from-stage voice --voice mohit
```

Or one shot:

```bash
python cli.py run --pptx ./my-deck.pptx --topic "My video" --voice mohit
```

Details: [docs/NO_API_WORKFLOW.md](docs/NO_API_WORKFLOW.md)

## Professional voice cloning (not robotic TTS)

Generic engines (`edge_tts`, macOS `say`) sound like bots. For narration that
sounds like **you**, use **Chatterbox** local cloning (MIT) with a prepared profile.

```bash
# 1) Record 30-90s+ clean speech (see docs/VOICE_RECORDING_SCRIPT.md)
# 2) Build profile
python cli.py prepare-voice --voice mohit --audio ~/clean.wav --consent
# 3) Install clone engine
pip install chatterbox-tts
# 4) Run with --voice mohit
```

What we need from you and how this compares to ElevenLabs PVC:
[docs/VOICE_CLONING.md](docs/VOICE_CLONING.md)

### 1. System dependencies

| Tool | Needed for | Install (macOS) |
|---|---|---|
| Python 3.11+ | everything | `brew install python@3.12` |
| FFmpeg | video + audio + subtitles | `brew install ffmpeg` |
| LibreOffice (optional) | PPTX to PNG via soffice | `brew install --cask libreoffice` |
| CUDA GPU (optional) | Chatterbox + WhisperX speed | NVIDIA driver + CUDA |

### 2. Python environment

```bash
cd yt-setup
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
# optional web dashboard:
# pip install -e ".[web]"
```

### 3. Config and secrets

```bash
cp config.yaml.example config.yaml
cp .env.example .env
# Edit .env:
#   ANTHROPIC_API_KEY=...
#   HF_TOKEN=...                 # WhisperX diarization only
#   ELEVENLABS_API_KEY=...      # optional
#   VANTAGE_API_URL=...
```

Place YouTube OAuth desktop client JSON at `.credentials/client_secret.json` when you are ready to upload.

### 4. Run

```bash
# Full pipeline (Claude if API key set; edge-tts narration; real MP4)
python cli.py run --topic "Rust async explained"

# Offline-friendly heavy stages for CI / dry architecture checks
YT_STUDIO_STUB_VOICE=1 YT_STUDIO_STUB_TRANSCRIBE=1 \
  python cli.py run --topic "Demo" --dry-run-publish

# Single stage against existing project
python cli.py run --project 2026-07-09_rust-async-explained --only slidebuilder --force

# Source document + keywords + skip publish
python cli.py run --topic "Docker networking" \
  --source-file ./notes.md \
  --keywords "docker,networking" \
  --skip publisher

# Batch queue (one topic per line)
python cli.py batch topics.txt --skip publisher

# Web UI API
python cli.py serve --port 8765
# open web_ui/frontend/index.html in a browser
```

### 5. Tests

```bash
pytest
```

---

## CLI reference

| Command | Purpose |
|---|---|
| `python cli.py run --topic "..."` | Create project and run all stages |
| `python cli.py run --project <id> --only a,b` | Run selected stages |
| `python cli.py run ... --from-stage voice` | Resume from a stage |
| `python cli.py run ... --force` | Ignore completed checkpoints |
| `python cli.py run ... --voice <id>` | Select voice id |
| `python cli.py run ... --source-file path` | Extra context for scriptwriter |
| `python cli.py run ... --burn-subtitles` | Write `final_subtitled.mp4` |
| `python cli.py run ... --dry-run-publish` | Never call YouTube API |
| `python cli.py batch topics.txt` | Sequential multi-topic queue |
| `python cli.py list` / `status` / `stages` | Inspection |
| `python cli.py serve` | FastAPI dashboard backend |

---

## Pipeline stages

1. **scriptwriter** — Claude / NVIDIA NIM (or stub) -> `outline.json` + `seo.json`
2. **storyboard** — Director -> choreographed visual beats (`storyboard.json`)
3. **scenegen** — Animated HTML/CSS scenes rendered to per-beat `scene_XX.mp4` + Visual QA
4. **voice** — one MP3 per slide/beat under `audio/` via Chatterbox or configured engine
5. **video_assembler** — animated scenes + narration audio -> `final.mp4` (optional BGM)
6. **transcriber** — `transcript.json` / `.srt` / `.vtt`
7. **chapters** — `chapters.txt` (first marker must be `0:00`); merges into SEO description
8. **shorts** — Vantage or local keyword clips under `shorts/`
9. **publisher** — thumbnail + private upload or dry-run `publish_manifest.json`

Orchestration: `core/pipeline.py`. Completed stages in `state.json` are skipped unless `--force` / `--only`.

---

## Agent-Native Skills (Surface B)

Anyone running inside Claude Code, OpenCode, or any agent-skill-compatible tool can build videos without an Anthropic API key by invoking the skills:
- `/create-video "topic"` — runs long-form CoreDumpped/3B1B-style animated video creation.
- `/create-short "topic"` — runs punchy 30-60s Short/Reel creation.

Both interfaces share the identical design tokens, storyboard schema, and component library.

---

## Configuration highlights

See `config.yaml.example`.

- `llm.provider`: `anthropic` | `nvidia` (NVIDIA NIM hosted endpoints) | `openai`
- `voice.engine`: `chatterbox` | `edge_tts` | `mac_say` | `elevenlabs` | `xtts` | `silence`
- `transcription.engine`: `faster-whisper` (default) or `whisperx`
- `music.enabled` + `music.track_path` for a ducked bed under narration
- `publisher.default_privacy`: `private` (recommended)

### Environment overrides

| Variable | Effect |
|---|---|
| `LLM_PROVIDER=nvidia` | Route LLM completions to NVIDIA NIM endpoints |
| `NVIDIA_API_KEY` | API key for build.nvidia.com NIM hosted models |
| `YT_STUDIO_STUB_SCENES=1` | Fast synthetic MP4 scenes for CI / testing |
| `YT_STUDIO_STUB_VOICE=1` | Silence clips (no TTS network/GPU) |
| `YT_STUDIO_STUB_TRANSCRIBE=1` | Stub transcript |
| `YT_STUDIO_STUB_LLM=1` | Force outline/storyboard stub even with API key |
| `YT_STUDIO_STRICT_QA=1` | Fail pipeline run if visual QA detects violations |
| `YT_STUDIO_SKIP_VANTAGE=1` | Local shorts only |
| `YT_STUDIO_PUBLISH_DRY_RUN=1` | Never upload |
| `YT_STUDIO_WHISPER_MODEL=tiny` | Faster local transcription |
| `YT_STUDIO_ALLOW_PUBLIC=1` | Allow public YouTube privacy |

---

## Hardware

- **GPU:** RTX 3060 12GB+ is comfortable for Chatterbox + WhisperX.
- **No GPU:** `edge_tts` + `faster-whisper` (`base`/`tiny`) work on CPU.
- Spot GPU (~$0.20-0.60/hr) only needed for heavy local model sessions.

---

## Security

- Never commit `.env`, OAuth client secrets, or `projects/` media.
- Publisher defaults to **private** uploads.
- Public uploads require `--confirm-public` or `YT_STUDIO_ALLOW_PUBLIC=1`.

---

## Related

- Vantage: https://www.tryvantage.site
- Chatterbox: https://github.com/resemble-ai/chatterbox
- WhisperX: https://github.com/m-bain/whisperX
- faster-whisper: https://github.com/SYSTRAN/faster-whisper

---

## License

MIT — see [LICENSE](LICENSE).
