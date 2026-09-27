# yt-studio — implementation roadmap

Production-grade delivery checklist. Quality gates: types, tests, resumability, clear errors, no secrets in git.

---

## Phase 0 — Scaffold (done)

- [x] Directory tree matching the architecture plan
- [x] `pyproject.toml` + `requirements.txt`
- [x] `config.yaml.example` + `.env.example` + pydantic `AppConfig`
- [x] `core/project.py`, `checkpoint.py`, `pipeline.py`, `stages.py`
- [x] Eight stages with real artifact paths
- [x] VoiceEngine interface
- [x] Vantage HTTP client shell
- [x] CLI: `run`, `list`, `status`, `stages`
- [x] Pytest suite

---

## Phase 1 — Scriptwriter + Slidebuilder (done)

- [x] Anthropic client with retries, timeouts, JSON repair
- [x] Pydantic schemas: `SlideOutline`, `SEOMetadata`
- [x] Versioned prompts in `modules/scriptwriter/prompts/`
- [x] `--source-file` context support
- [x] Branded `python-pptx` theme + optional template
- [x] Speaker notes pane per slide
- [x] Tests with offline stub + PPTX roundtrip

---

## Phase 2 — Voice + Video assembler (done)

- [x] ChatterboxEngine (when package installed)
- [x] EdgeTTSEngine production free fallback
- [x] MacSayEngine, ElevenLabsEngine, XTTSEngine, SilenceEngine
- [x] Per-slide duration metadata (`audio/durations.json`)
- [x] Pillow frame renderer (LibreOffice optional)
- [x] FFmpeg still+audio clips, concat, optional crossfade
- [x] Real H.264/AAC `final.mp4`

---

## Phase 3 — Transcriber + Chapters + Subtitles (done)

- [x] faster-whisper path with word timestamps
- [x] WhisperX aligned path when installed
- [x] SRT/VTT export
- [x] Claude + heuristic chapter generation
- [x] YouTube rules: `0:00` first, min gap, max count
- [x] Merge chapters into SEO description
- [x] FFmpeg subtitle burn-in (`--burn-subtitles`)

---

## Phase 4 — Shorts / Vantage (done)

- [x] VantageClient multi-endpoint probe
- [x] Health check + auth header
- [x] Local keyword FFmpeg 9:16 fallback
- [x] `shorts/manifest.json`

---

## Phase 5 — Publisher + thumbnail + web UI (done)

- [x] OAuth desktop flow + token cache
- [x] Resumable upload, private default, thumbnail set
- [x] Public upload guard
- [x] Dry-run manifest without credentials
- [x] Shorts upload helper
- [x] Pillow branded thumbnails
- [x] FastAPI API + static dashboard (`cli.py serve`)

---

## Phase 6 — Polish (done)

- [x] Default PPTX template generator
- [x] Background music mixer (`music.*` config)
- [x] Crossfade transitions
- [x] Batch/queue mode (`cli.py batch`)
- [x] Expanded CLI flags (source, privacy, burn-subtitles)
- [x] Documentation without decorative noise

---

## Ongoing quality bar

1. Tests green before merge (`pytest`)
2. Stages remain resumable and idempotent with `--force`
3. No secrets committed
4. Failures are actionable in logs and `state.json`
5. Heavy deps optional; graceful engine fallbacks
