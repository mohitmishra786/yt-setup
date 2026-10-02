# AGENTS.md — yt-studio

Local-first YouTube pipeline: `topic -> outline.json/seo.json -> slides.pptx -> audio/slide_XX.mp3 -> frames + final.mp4 -> transcript/chapters -> shorts -> (optional) YouTube upload`.

## Commands

```bash
pip install -e ".[dev]"          # add ".[web]" only for the (currently empty) web UI

python cli.py run --topic "Rust async explained"
python cli.py run --project <id> --only voice,transcriber     # --only re-runs even if completed
python cli.py run --project <id> --from-stage voice            # resume from a stage
python cli.py list | status | stages

python -m pytest                                             # testpaths=tests, pythonpath=.
python -m pytest tests/test_pipeline_stub.py -k only_stage -q
ruff check . && mypy                                          # mypy strict, packages=core,modules
```

Requires Python **3.11+** (`StrEnum` in `core/checkpoint.py`). The system `python3` has no
pytest installed — use a venv (`python3 -m venv .venv`). `ffmpeg` must be on PATH; LibreOffice
is optional (Pillow frame renderer is the fallback).

Fully offline smoke run (no API key, no TTS, no whisper, no Vantage, no upload):

```bash
YT_STUDIO_STUB_VOICE=1 YT_STUDIO_STUB_TRANSCRIBE=1 YT_STUDIO_SKIP_VANTAGE=1 \
  python cli.py run --topic "Demo" --dry-run-publish
```

## Agent video surface (`/create-video`, `/create-short`)

User-facing walkthrough: `docs/GUIDE.md` (install → channel → voice → make → publish).

Visuals come from **HyperFrames**, not the legacy `storyboard`/`scenegen`/`video_assembler` stages
(those remain only for the API-key `cli.py run --topic` path). Flow: agent writes `outline.json` →
`cli.py import-outline` → `--only voice` → agent writes `video-plan.md` + HyperFrames project in
`projects/<id>/composition/` → `--only hyperframes` (check + render + poster bake) →
`--from-stage transcriber`. Rules live in `skills/create-video/references/`; compositions are
written on the shared scene kit `skills/create-video/assets/scenekit.py` (focus stack, notes,
captions, title card/outro). `/create-short` has its own `references/` (vertical laws, script,
compose, publish), `templates/build.py`, `scripts/scaffold.py` + `scripts/verify_short.py`, and a
worked example in `examples/kernel-stack/` (kept byte-identical to a shipped Short). Branding is read from `config.yaml` → `channel:` (`ChannelSettings`
in `core/config.py`) — never hardcode a channel. Shorts: `skills/create-video/assets/build_shorts.py`. `hyperframes` is an
opt-in stage (not in `pipeline.stages`); `--only` keeps registry order for such stages. Needs
Node 22+; `YT_STUDIO_HF_QUALITY=draft|standard|high`.

### Uploading and scheduling (`/upload-video`)

`cli.py youtube-auth` (one-time browser login, checks the channel against `channel.handle`) and
`cli.py upload --project <id> [--dry-run|--yes|--verify|--only|--no-schedule]` →
`modules/publisher/scheduler.py`. The plan is `projects/<id>/publish/upload.json` and progress
goes to `publish/uploaded.json` (resumable; an item with a video id is never re-uploaded).
YouTube schedules via `status.publishAt` (private until then), so nothing runs at post time.
Until the Cloud project passes the YouTube API audit, API uploads are locked private. Setup
walkthrough: `skills/upload-video/references/setup.md`. Tokens use the `youtube.upload` and
`youtube.force-ssl` scopes. Captions come from the script (`skills/upload-video/scripts/script_srt.py`),
not `transcript.srt`. The `publisher` pipeline stage still uploads when `.credentials/client_secret.json`
exists, so pass `--dry-run-publish` on manual `cli.py run`s.

### Narration quality and sync

- Chatterbox conditions on only the first ~10s of the reference, so `cli.py voice-prompt --voice <id>`
  writes a curated `prompt.wav` (preferred by `VoiceProfile.resolve_reference`) plus audition clips.
- The Chatterbox engine generates per sentence (fixed seeds, `YT_STUDIO_VOICE_SEED`), verifies each
  with Whisper and retakes (`YT_STUDIO_VOICE_TRIES`, `YT_STUDIO_VOICE_VERIFY=0` to skip), then masters
  to -16 LUFS. Narration ASR uses Whisper `medium` (`YT_STUDIO_VOICE_ASR_MODEL`) — `base` mishears
  accented speech/jargon and causes false retakes.
- Chatterbox runs on CPU by default: MPS starts faster but collapses to 1-3 s/step after ~100 steps
  (a 3-min script took 12h). `YT_STUDIO_VOICE_DEVICE=mps` to opt in. Finished slides are reused
  via `audio/slide_XX.key` (engine + voice + prompt hash + text), so edits regenerate only changed slides.
- `cli.py voice-check` prints script vs what Whisper heard per slide (a flipped word like
  "can't" -> "can" can still score 0.9; reword — identical text reproduces the same take).
  `cli.py voice-import --dir` uses narration the user recorded themselves instead of a clone.
  `cli.py pace --gap` inserts silence at sentence breaks (idempotent; originals in `audio/unpaced/`).
- The voice stage also writes `audio/words.json` (script words with timings). `cli.py cues --project <id>`
  resolves `anchors.json` (beat → spoken phrase) to `cues.json`; compositions embed those times.

## Gotchas an agent would otherwise hit

- **No CI, no pre-commit, no lint-clean baseline.** `ruff check .` currently reports ~84 findings
  (mostly `UP007`, `I001`, `E501`, and 15× `B008` from typer `Option(...)` defaults in `cli.py`).
  `B008` is a typer false positive — do not "fix" it. Scope lint fixes to files you touch.
- **No venv / deps installed in this checkout.** `requirements.txt` only mirrors `pyproject.toml`;
  extra `voice` installs Chatterbox (`uv pip install --python .venv/bin/python -e ".[voice]"`; the
  venv is uv-made and has no `pip`); `transcribe` is intentionally empty (whisperx manual).
- **`web_ui/api` and `web_ui/frontend` are empty directories.** `python cli.py serve` imports
  `web_ui.api.main:app` and will fail; `fastapi` is not a base dependency. README overstates this.
- **Code defaults ≠ `config.yaml.example`** for `transcription`: `core/config.py` defaults to
  `whisperx` / `large-v3` / `float16`, the example YAML uses `faster-whisper` / `base` / `int8`.
  Tests build `AppConfig(...)` directly, so they get the code defaults — never assume the YAML.
- **`voice.require_clone` defaults to `true` with `engine: chatterbox`**, so the voice stage raises a
  multi-line install error unless `chatterbox-tts` + a voice profile exist. Use
  `YT_STUDIO_STUB_VOICE=1`, or `voice.require_clone: false` / `YT_STUDIO_ALLOW_GENERIC_TTS=1`.
- **Scriptwriter silently stubs** when `ANTHROPIC_API_KEY` is unset, and *raises* if Claude fails
  unless `YT_STUDIO_ALLOW_LLM_FALLBACK=1`.
- Env switches are scattered across modules; grep `os.getenv("YT_STUDIO_` before adding a new one.
  README's env table is incomplete (e.g. `YT_STUDIO_FORCE_STUB`, `YT_STUDIO_KEEP_EXTRACT`,
  `YT_STUDIO_FAST_TRANSCRIBE` exist in code but not in the README).
- `projects/`, `config.yaml`, `.env`, `.credentials/`, `recordings/`, `modules/voice/voices/*/`
  and all media files are gitignored — local voice profiles, recordings and renders are personal.
  Never commit them.

## Architecture

- `cli.py` — the only entrypoint (typer). Console script `yt-studio = "cli:app"` targets a Typer
  object, not a callable; use `python cli.py`.
- `core/` — `config.py` (pydantic settings; `load_config()` walks up for `pyproject.toml` to find
  repo root, then loads `./config.yaml` + `.env`), `project.py` (`Project` + `ProjectPaths`),
  `checkpoint.py` (atomic `state.json`), `pipeline.py` (ordered execution, resume), `stages.py`
  (`Stage` protocol + `build_default_registry()`), `llm.py`, `schemas.py`, `stub_utils.py`.
- `modules/<stage>/` — one class per stage with `name: str` and `run(project) -> StageResult`.
  Heavy/optional imports (torch, whisper, chatterbox, fastapi) are deliberately function-local.

### Adding or changing a stage

1. Implement the class in `modules/<name>/`, returning `StageResult` with project-relative artifacts.
2. Register it in `core/stages.py:build_default_registry()` (import + instantiate + ordered list).
3. Add its name to `pipeline.stages` in `config.yaml` **and** the `PipelineSettings.stages` default
   in `core/config.py` — **stage order is config-driven**, not code-driven.
4. Add artifact path properties to `ProjectPaths` (`core/project.py`); never hardcode paths.
5. Test with a `tmp_path` project and stub env vars (see `tests/test_pipeline_stub.py`).

### Resume semantics (`core/pipeline.py`)

- Order comes from `config.pipeline.stages`; `--only` re-runs selected stages even when
  `COMPLETED` (so `--only` implies `--force`), other completed stages are skipped.
- `fail_fast: true` by default: the first exception marks the stage `FAILED` in `state.json` and
  stops the run.

## Conventions

- `from __future__ import annotations` at the top of every module; full type hints.
- Logging via `core.logging_setup.get_logger(__name__)`. No `print()` in `core/` or `modules/` —
  `rich.Console` output lives only in `cli.py`.
- ruff: line-length 100, `select = E,F,I,UP,B,SIM,N`. mypy: `strict = true` over `core` + `modules`
  (tests are not type-checked).
- Tests construct `AppConfig` with `ProjectSettings(root=tmp_path / "projects")` and
  `monkeypatch.setenv` rather than loading `config.yaml`; markers `integration` and `gpu` exist for
  heavy suites.
- Agent role wiring lives in `agentroles.yaml` (source of truth) generating `opencode.json` and
  `.claude/agents/*.md` — edit `agentroles.yaml`, not the generated files.
