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

## Gotchas an agent would otherwise hit

- **No CI, no pre-commit, no lint-clean baseline.** `ruff check .` currently reports ~84 findings
  (mostly `UP007`, `I001`, `E501`, and 15× `B008` from typer `Option(...)` defaults in `cli.py`).
  `B008` is a typer false positive — do not "fix" it. Scope lint fixes to files you touch.
- **No venv / deps installed in this checkout.** `requirements.txt` only mirrors `pyproject.toml`;
  extras `voice`/`transcribe` in `pyproject.toml` are intentionally empty (chatterbox-tts, whisperx
  must be pip-installed manually).
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
- `projects/`, `.env`, `.credentials/`, `modules/voice/voices/*/` are gitignored; the local
  `mohit` voice profile and `recordings/mohit/*.m4a` are untracked. Never commit them.

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
