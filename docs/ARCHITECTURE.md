# Architecture

## Design principles

1. **Local-first** — media never leaves the machine unless you publish.
2. **Modular stages** — each stage is a class with `name` + `run(project) -> StageResult`.
3. **Plain artifacts** — JSON, MP3, PNG, MP4, SRT under `projects/<id>/` so stages are inspectable and swappable.
4. **Resumable** — `state.json` checkpoint; completed stages skip on re-run.
5. **Pluggable backends** — especially `VoiceEngine` and transcription engines.
6. **Safe defaults** — publisher privacy `private`; fail-fast pipeline; atomic checkpoint writes.

## Data flow

```
topic / source
    → outline.json + seo.json
    → storyboard.json
    → scenes/scene_XX.html + scene_XX.mp4 (Playwright + FFmpeg)
    → audio/slide_XX.mp3 (Chatterbox / TTS)
    → final.mp4 (scene concatenation + audio muxing)
    → transcript.json + .srt/.vtt
    → chapters.txt
    → shorts/* + publish_manifest.json
    → (optional) YouTube
```

## Core types

| Type | Role |
|---|---|
| `AppConfig` | Validated global settings |
| `Project` | Paths + checkpoint + run context |
| `Checkpoint` | Per-stage status + artifacts |
| `Stage` | Protocol for modules |
| `Pipeline` | Ordered execution + resume |

## Extending

1. Implement `class MyStage: name = "..."; def run(self, project): ...`
2. Register in `core/stages.py` → `build_default_registry()`
3. Add name to `config.yaml` → `pipeline.stages` if new position needed
4. Write tests with `tmp_path` projects

## Why stubs first

Heavy deps (torch, whisperx, chatterbox) must not block architecture validation.
Phase 0 proves orchestration, paths, and CLI. Each later phase replaces one stub
with production logic behind the same interface.
