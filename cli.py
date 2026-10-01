#!/usr/bin/env python3
"""yt-studio CLI — run the local YouTube creation pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from core.config import load_config
from core.logging_setup import ensure_utf8_stdio, setup_logging
from core.pipeline import Pipeline
from core.project import Project, make_project_id

app = typer.Typer(
    name="yt-studio",
    help="Local-first YouTube creation pipeline (topic -> video -> chapters -> Shorts).",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def _parse_csv(value: Optional[str]) -> list[str] | None:
    if value is None or value.strip() == "":
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


@app.command("run")
def run_cmd(
    topic: Optional[str] = typer.Option(
        None,
        "--topic",
        "-t",
        help="Video topic / working title (required when creating a new project).",
    ),
    project_id: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Existing project id under projects/ (e.g. 2026-07-09_my-video).",
    ),
    voice: Optional[str] = typer.Option(
        None,
        "--voice",
        "-v",
        help="Voice id (reference clip name under modules/voice/voices/).",
    ),
    only: Optional[str] = typer.Option(
        None,
        "--only",
        help="Comma-separated stages to run (e.g. scriptwriter,storyboard,scenegen).",
    ),
    skip: Optional[str] = typer.Option(
        None,
        "--skip",
        help="Comma-separated stages to skip.",
    ),
    from_stage: Optional[str] = typer.Option(
        None,
        "--from-stage",
        help="Start from this stage (inclusive), using configured order.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Re-run stages even if already completed in state.json.",
    ),
    keywords: Optional[str] = typer.Option(
        None,
        "--keywords",
        help="Comma-separated keywords for the Shorts / Vantage stage.",
    ),
    source_file: Optional[Path] = typer.Option(
        None,
        "--source-file",
        help="Optional markdown/text file fed to the scriptwriter as source material.",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        help="Slide template filename under modules/slidebuilder/templates/.",
    ),
    dry_run_publish: bool = typer.Option(
        False,
        "--dry-run-publish",
        help="Never call YouTube API; write publish_manifest.json only.",
    ),
    burn_subtitles: bool = typer.Option(
        False,
        "--burn-subtitles",
        help="After transcription, burn SRT into final_subtitled.mp4.",
    ),
    privacy: Optional[str] = typer.Option(
        None,
        "--privacy",
        help="YouTube privacy: private|unlisted|public (public requires confirm).",
    ),
    confirm_public: bool = typer.Option(
        False,
        "--confirm-public",
        help="Required together with --privacy public.",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config.yaml (default: ./config.yaml).",
    ),
    new: bool = typer.Option(
        False,
        "--new",
        help="Force create a fresh project folder (deletes existing id if present).",
    ),
    pptx: Optional[Path] = typer.Option(
        None,
        "--pptx",
        help="Import an existing .pptx (skips scriptwriter+slidebuilder). From Claude.ai UI etc.",
    ),
    outline_json: Optional[Path] = typer.Option(
        None,
        "--outline-json",
        help="Import a hand-written / Claude.ai-exported outline.json (no API key needed).",
    ),
) -> None:
    """
    Run the full pipeline or a subset of stages.

    Examples:

      python cli.py run --topic "Rust async explained"

      python cli.py run --project 2026-07-09_rust-async --only slidebuilder --force

      python cli.py run --topic "Docker networking" --voice mohit --skip publisher
    """
    ensure_utf8_stdio()
    cfg = load_config(config)
    setup_logging(cfg.pipeline.log_level)

    only_list = _parse_csv(only)
    skip_list = _parse_csv(skip)
    kw_list = _parse_csv(keywords) or []

    options: dict = {"keywords": kw_list}
    if source_file is not None:
        options["source_file"] = str(source_file)
    if template is not None:
        options["template"] = template
    if dry_run_publish:
        options["dry_run"] = True
    if burn_subtitles:
        options["burn_subtitles"] = True
    if privacy:
        options["privacy"] = privacy
    if confirm_public:
        options["confirm_public"] = True

    context: dict = {"topic": topic or ""}
    if source_file is not None:
        context["source_file"] = str(source_file)

    # Auto-topic from imports when missing
    if not topic and pptx is not None:
        topic = pptx.stem.replace("_", " ").replace("-", " ")
    if not topic and outline_json is not None:
        topic = outline_json.stem.replace("_", " ").replace("-", " ")

    if project_id:
        if new and topic:
            proj = Project.create(
                cfg,
                topic,
                project_id=project_id,
                voice_id=voice,
                options=options,
                context=context,
                force=True,
            )
        else:
            proj = Project.load(cfg, project_id)
            if voice:
                proj.checkpoint.voice_id = voice
            proj.checkpoint.options.update(options)
            proj.context.update(context)
            if topic and not proj.checkpoint.topic:
                proj.checkpoint.topic = topic
            proj.save()
    else:
        if not topic:
            console.print(
                "[red]Error:[/red] provide --topic, --pptx, --outline-json, or --project."
            )
            raise typer.Exit(code=2)
        proj = Project.create(
            cfg,
            topic,
            voice_id=voice,
            options=options,
            context=context,
            force=new,
        )

    # Bring-your-own deck / outline (no Anthropic API)
    if pptx is not None:
        from modules.slidebuilder.import_pptx import import_pptx_into_project

        if not pptx.exists():
            console.print(f"[red]PPTX not found:[/red] {pptx}")
            raise typer.Exit(code=2)
        info = import_pptx_into_project(
            proj.paths.root,
            pptx,
            deck_title=topic,
            topic=topic,
        )
        console.print(
            f"[green]Imported PPTX[/green] slides={info['slide_count']} title={info['title']!r}"
        )
        # Mark early stages complete so pipeline resumes at voice by default
        proj.checkpoint.mark_completed(
            "scriptwriter",
            artifacts=["outline.json", "seo.json"],
            meta={"imported": True, "source": "pptx"},
        )
        if "slidebuilder" in proj.checkpoint.stages:
            proj.checkpoint.mark_completed(
                "slidebuilder",
                artifacts=["slides.pptx"],
                meta={"imported": True, "source": str(pptx)},
            )
        proj.save()
        if from_stage is None and only_list is None:
            from_stage = "voice" if "voice" in proj.checkpoint.stages else "storyboard"
            console.print(f"[dim]Starting from {from_stage} (scriptwriter imported)[/dim]")

    if outline_json is not None:
        from modules.slidebuilder.import_pptx import import_outline_json

        if not outline_json.exists():
            console.print(f"[red]Outline not found:[/red] {outline_json}")
            raise typer.Exit(code=2)
        info = import_outline_json(proj.paths.root, outline_json)
        console.print(
            f"[green]Imported outline[/green] slides={info['slide_count']} title={info['title']!r}"
        )
        proj.checkpoint.mark_completed(
            "scriptwriter",
            artifacts=["outline.json", "seo.json"],
            meta={"imported": True, "source": "outline_json"},
        )
        proj.save()
        if from_stage is None and only_list is None:
            from_stage = "storyboard" if "storyboard" in proj.checkpoint.stages else "scenegen"
            console.print(f"[dim]Starting from {from_stage} (outline imported)[/dim]")

    console.print(f"[bold]Project[/bold]  {proj.project_id}")
    console.print(f"[bold]Path[/bold]     {proj.paths.root}")

    pipeline = Pipeline(cfg)
    try:
        result = pipeline.run(
            proj,
            only=only_list,
            skip=skip_list,
            force=force,
            from_stage=from_stage,
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    table = Table(title="Stage status")
    table.add_column("Stage")
    table.add_column("Status")
    for name, status in proj.checkpoint.summary().items():
        style = {
            "completed": "green",
            "failed": "red",
            "skipped": "yellow",
            "running": "cyan",
            "pending": "dim",
        }.get(status, "")
        table.add_row(name, f"[{style}]{status}[/{style}]" if style else status)
    console.print(table)

    if not result.ok:
        console.print(f"[red]Failed at[/red] {result.failed}: {result.error}")
        raise typer.Exit(code=1)

    console.print("[green]Pipeline OK[/green]")


@app.command("import-pptx")
def import_pptx_cmd(
    pptx: Path = typer.Argument(..., help="Path to an existing .pptx file"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t"),
    voice: Optional[str] = typer.Option(None, "--voice", "-v"),
    project_id: Optional[str] = typer.Option(None, "--project", "-p"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Import a PPTX created in Claude.ai / PowerPoint / Keynote (no API key)."""
    ensure_utf8_stdio()
    cfg = load_config(config)
    setup_logging(cfg.pipeline.log_level)
    if not pptx.exists():
        console.print(f"[red]Not found:[/red] {pptx}")
        raise typer.Exit(code=2)
    topic = topic or pptx.stem.replace("_", " ").replace("-", " ")
    proj = Project.create(cfg, topic, project_id=project_id, voice_id=voice)
    from modules.slidebuilder.import_pptx import import_pptx_into_project

    info = import_pptx_into_project(proj.paths.root, pptx, deck_title=topic, topic=topic)
    proj.checkpoint.mark_completed(
        "scriptwriter", artifacts=["outline.json", "seo.json"], meta={"imported": True}
    )
    if "slidebuilder" in proj.checkpoint.stages:
        proj.checkpoint.mark_completed(
            "slidebuilder", artifacts=["slides.pptx"], meta={"imported": True}
        )
    proj.save()
    console.print(f"[green]Project[/green] {proj.project_id}")
    console.print(f"  slides: {info['slide_count']}")
    console.print(f"  path:   {proj.paths.root}")
    console.print(
        f"Next: python cli.py run --project {proj.project_id} --from-stage storyboard"
        + (f" --voice {voice}" if voice else "")
    )


@app.command("import-outline")
def import_outline_cmd(
    outline: Path = typer.Argument(..., help="outline.json from Claude.ai or hand-written"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t"),
    seo: Optional[Path] = typer.Option(None, "--seo", help="Optional seo.json"),
    voice: Optional[str] = typer.Option(None, "--voice", "-v"),
    project_id: Optional[str] = typer.Option(None, "--project", "-p"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Import outline JSON without Anthropic API; run storyboard next."""
    ensure_utf8_stdio()
    cfg = load_config(config)
    setup_logging(cfg.pipeline.log_level)
    if not outline.exists():
        console.print(f"[red]Not found:[/red] {outline}")
        raise typer.Exit(code=2)
    topic = topic or outline.stem.replace("_", " ").replace("-", " ")
    proj = Project.create(cfg, topic, project_id=project_id, voice_id=voice)
    from modules.slidebuilder.import_pptx import import_outline_json

    info = import_outline_json(proj.paths.root, outline, seo_path=seo)
    proj.checkpoint.mark_completed(
        "scriptwriter", artifacts=["outline.json", "seo.json"], meta={"imported": True}
    )
    proj.save()
    console.print(f"[green]Project[/green] {proj.project_id} slides={info['slide_count']}")
    console.print(
        f"Next: python cli.py run --project {proj.project_id} --from-stage storyboard"
    )


@app.command("prepare-voice")
def prepare_voice_cmd(
    voice: str = typer.Option(..., "--voice", "-v", help="Voice id, e.g. mohit"),
    audio: list[Path] = typer.Option(
        ...,
        "--audio",
        "-a",
        help="Clean recording file(s). Repeat flag for multiple takes.",
    ),
    name: Optional[str] = typer.Option(None, "--name", help="Display name"),
    language: str = typer.Option("en", "--language"),
    consent: bool = typer.Option(
        False,
        "--consent",
        help="Confirm you own/have rights to this voice.",
    ),
) -> None:
    """
    Build a professional voice-clone profile from your clean recordings.

    Target: 30-90+ seconds of dry, single-speaker audio (see docs/VOICE_CLONING.md).
    """
    ensure_utf8_stdio()
    setup_logging("INFO")
    missing = [str(p) for p in audio if not p.exists()]
    if missing:
        console.print(f"[red]Audio not found:[/red] {missing}")
        raise typer.Exit(code=2)
    from modules.voice.profile import prepare_voice_profile, validate_profile_for_cloning

    profile = prepare_voice_profile(
        voice,
        list(audio),
        display_name=name,
        language=language,
        consent=consent,
    )
    meta = profile.load_meta()
    console.print(f"[green]Voice profile ready[/green] id={voice}")
    console.print(f"  path:     {profile.root}")
    console.print(f"  duration: {meta.get('reference_duration_seconds')}s")
    console.print(f"  quality:  {meta.get('quality_tier')}")
    for note in meta.get("notes") or []:
        console.print(f"  note: {note}")
    for w in validate_profile_for_cloning(profile):
        console.print(f"[yellow]warning:[/yellow] {w}")
    console.print(
        f"Use with: python cli.py run --pptx deck.pptx --voice {voice}"
    )
    console.print("Install clone engine if needed: pip install chatterbox-tts")


@app.command("voice-prompt")
def voice_prompt_cmd(
    voice: str = typer.Option(..., "--voice", "-v", help="Voice id, e.g. mohit"),
    source: Optional[Path] = typer.Option(
        None, "--source", help="Recording to cut from (default: the profile's original recordings)."
    ),
    start: Optional[float] = typer.Option(
        None, "--start", help="Use this start second instead of the auto-picked best window."
    ),
    candidates: int = typer.Option(3, "--candidates", help="Also write N audition clips."),
) -> None:
    """
    Build prompt.wav — the ~10s clip Chatterbox actually conditions on.

    Auto-picks the cleanest continuous-speech window from your original recordings and writes
    audition clips to <profile>/prompt_candidates/ so you can listen and override with --start.
    """
    ensure_utf8_stdio()
    setup_logging("INFO")
    from modules.voice.profile import get_profile
    from modules.voice.reference import best_candidates, cut_clean

    profile = get_profile(voice)
    if source is not None:
        sources = [source]
    else:
        root = load_config().repo_root
        sources = [root / s for s in profile.load_meta().get("created_from", [])]
        sources = [s for s in sources if s.exists()] or [profile.reference_wav]
    missing = [str(s) for s in sources if not s.exists()]
    if missing:
        console.print(f"[red]Audio not found:[/red] {missing}")
        raise typer.Exit(code=2)

    if start is not None:
        chosen_src, chosen_start = sources[0], start
    else:
        picks = best_candidates(sources, top=max(1, candidates))
        if not picks:
            console.print("[red]No usable speech window found.[/red]")
            raise typer.Exit(code=1)
        cand_dir = profile.root / "prompt_candidates"
        if cand_dir.exists():
            shutil.rmtree(cand_dir)
        for i, c in enumerate(picks, start=1):
            clip = cut_clean(c.source, c.start, cand_dir / f"cand_{i}_{c.source.stem}_{c.start:.1f}s.wav")
            console.print(
                f"  cand {i}: {c.source.name} @ {c.start:.1f}s  speech={c.speech_ratio:.0%} "
                f"longest_pause={c.longest_pause:.2f}s -> {clip.name}"
            )
        chosen_src, chosen_start = picks[0].source, picks[0].start

    cut_clean(chosen_src, chosen_start, profile.prompt_wav)
    meta = profile.load_meta()
    meta["prompt"] = {"source": str(chosen_src), "start": round(chosen_start, 3), "seconds": 10.0}
    profile.save_meta(meta)
    console.print(f"[green]prompt.wav[/green] <- {chosen_src.name} @ {chosen_start:.1f}s ({profile.prompt_wav})")


@app.command("voice-import")
def voice_import_cmd(
    project_id: str = typer.Option(..., "--project", "-p"),
    folder: Path = typer.Option(
        ..., "--dir", "-d", help="Folder with one recording per slide (slide_01.wav, …)."
    ),
    keep_silence: bool = typer.Option(
        False, "--keep-silence", help="Don't trim leading/trailing room tone."
    ),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Use narration you recorded yourself (no voice cloning): master it and time every word."""
    from modules.voice.importer import import_narration

    ensure_utf8_stdio()
    setup_logging("INFO")
    cfg = load_config(config)
    proj = Project.load(cfg, project_id)
    if not folder.is_dir():
        console.print(f"[red]Not a folder:[/red] {folder}")
        raise typer.Exit(code=2)
    try:
        info = import_narration(proj, folder, trim_silence=not keep_silence)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]imported[/green] {info['slides']} recording(s), {info['total']}s total. "
        f"Next: cli.py voice-check / pace / cues --project {project_id}"
    )


@app.command("voice-check")
def voice_check_cmd(
    project_id: str = typer.Option(..., "--project", "-p"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Transcribe each narration slide and show it next to the script (catch 'can't' -> 'can')."""
    import json

    from modules.voice.words import asr_words, similarity

    ensure_utf8_stdio()
    cfg = load_config(config)
    proj = Project.load(cfg, project_id)
    outline = json.loads(proj.paths.outline.read_text(encoding="utf-8"))
    worst = 1.0
    for slide in outline.get("slides") or []:
        idx = int(slide["index"])
        audio = proj.paths.audio_for_slide(idx)
        if not audio.exists():
            console.print(f"[red]slide {idx}: missing {audio.name}[/red]")
            continue
        heard = asr_words(audio)
        score = similarity(str(slide["speaker_notes"]), heard)
        worst = min(worst, score)
        colour = "green" if score >= 0.9 else "yellow" if score >= 0.8 else "red"
        console.print(f"[{colour}]slide {idx:02d}  match {score:.2f}[/{colour}]")
        console.print(f"  script: {slide['speaker_notes']}")
        console.print(f"  heard:  {' '.join(w['text'] for w in heard)}")
    console.print(
        "Read every line: a single flipped word (can't -> can, program -> problem) changes the "
        "meaning even at a high score. Reword the sentence and re-run --only voice to fix it."
    )
    if worst < 0.8:
        raise typer.Exit(code=1)


@app.command("cues")
def cues_cmd(
    project_id: str = typer.Option(..., "--project", "-p"),
    anchors: Optional[Path] = typer.Option(None, "--anchors", help="Default: projects/<id>/anchors.json"),
    out: Optional[Path] = typer.Option(
        None, "--out", help="Default: projects/<id>/cues.json"
    ),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Resolve word-anchored cues (anchors.json) to exact times using audio/words.json."""
    import json

    from modules.voice.cues import CueError, resolve_cues

    ensure_utf8_stdio()
    cfg = load_config(config)
    proj = Project.load(cfg, project_id)
    anchors_path = anchors or proj.paths.root / "anchors.json"
    words_path = proj.paths.audio_dir / "words.json"
    for need in (anchors_path, words_path):
        if not need.exists():
            console.print(f"[red]Missing[/red] {need}")
            raise typer.Exit(code=2)
    try:
        cues = resolve_cues(
            json.loads(anchors_path.read_text(encoding="utf-8")),
            json.loads(words_path.read_text(encoding="utf-8")),
        )
    except CueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    dest = out or proj.paths.root / "cues.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(cues, indent=2) + "\n", encoding="utf-8")
    for cid, c in cues.items():
        console.print(f"  {cid:<24} slide {c['slide']:>2}  t={c['t']:>7.3f}s  abs={c['abs']:>8.3f}s  ({c['at']})")
    console.print(f"[green]{len(cues)} cue(s)[/green] -> {dest}")


@app.command("pace")
def pace_cmd(
    project_id: str = typer.Option(..., "--project", "-p"),
    gap: float = typer.Option(
        0.45, "--gap", help="Extra silence (s) added at every sentence break."
    ),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Slow narration down by adding pauses between sentences (no re-synthesis; re-run cues after)."""
    from modules.voice.pacing import pace_project

    ensure_utf8_stdio()
    cfg = load_config(config)
    proj = Project.load(cfg, project_id)
    info = pace_project(proj, gap)
    console.print(
        f"[green]paced[/green] {info['slides']} slide(s), +{gap}s per sentence break, "
        f"narration now {info['total']}s. Next: cli.py cues --project {project_id}"
    )


@app.command("batch")
def batch_cmd(
    topics_file: Path = typer.Argument(
        ...,
        help="Text file with one topic per line (blank lines and # comments ignored).",
    ),
    voice: Optional[str] = typer.Option(None, "--voice", "-v"),
    skip: Optional[str] = typer.Option(None, "--skip"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    dry_run_publish: bool = typer.Option(True, "--dry-run-publish/--no-dry-run-publish"),
) -> None:
    """Queue multiple videos from a topics file (sequential)."""
    ensure_utf8_stdio()
    cfg = load_config(config)
    setup_logging(cfg.pipeline.log_level)
    if not topics_file.exists():
        console.print(f"[red]File not found:[/red] {topics_file}")
        raise typer.Exit(code=2)

    skip_list = _parse_csv(skip)
    lines = [
        ln.strip()
        for ln in topics_file.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not lines:
        console.print("No topics in file.")
        raise typer.Exit(code=2)

    failures = 0
    for topic in lines:
        console.rule(topic)
        options: dict = {"keywords": []}
        if dry_run_publish:
            options["dry_run"] = True
        proj = Project.create(cfg, topic, voice_id=voice, options=options)
        result = Pipeline(cfg).run(proj, skip=skip_list)
        if not result.ok:
            failures += 1
            console.print(f"[red]FAILED[/red] {proj.project_id}: {result.error}")
        else:
            console.print(f"[green]OK[/green] {proj.project_id}")

    if failures:
        console.print(f"[red]{failures}/{len(lines)} failed[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]All {len(lines)} topics completed[/green]")


@app.command("list")
def list_cmd(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """List projects under the configured projects directory."""
    cfg = load_config(config)
    root = cfg.projects_dir()
    if not root.exists():
        console.print(f"No projects dir yet: {root}")
        raise typer.Exit()

    rows = sorted(
        [p for p in root.iterdir() if p.is_dir() and (p / "state.json").exists()],
        key=lambda p: p.name,
        reverse=True,
    )
    if not rows:
        console.print("No projects found.")
        raise typer.Exit()

    table = Table(title=f"Projects in {root}")
    table.add_column("Project ID")
    table.add_column("Completed stages")
    for p in rows:
        try:
            proj = Project.load(cfg, p.name)
            done = sum(1 for s in proj.checkpoint.summary().values() if s == "completed")
            total = len(proj.checkpoint.stages)
            table.add_row(p.name, f"{done}/{total}")
        except Exception as exc:  # noqa: BLE001
            table.add_row(p.name, f"error: {exc}")
    console.print(table)


@app.command("status")
def status_cmd(
    project_id: str = typer.Argument(..., help="Project id"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Show checkpoint state for a project."""
    cfg = load_config(config)
    try:
        proj = Project.load(cfg, project_id)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold]{proj.project_id}[/bold]  topic={proj.topic!r}")
    table = Table()
    table.add_column("Stage")
    table.add_column("Status")
    table.add_column("Artifacts")
    for name, rec in proj.checkpoint.stages.items():
        table.add_row(name, rec.status.value, ", ".join(rec.artifacts[:5]))
    console.print(table)


@app.command("stages")
def stages_cmd(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Print configured pipeline stage order."""
    cfg = load_config(config)
    for i, name in enumerate(cfg.pipeline.stages, start=1):
        console.print(f"{i:2d}. {name}")


@app.command("new-id")
def new_id_cmd(
    topic: str = typer.Argument(..., help="Topic to slugify into a project id"),
) -> None:
    """Print the project id that would be generated for a topic today."""
    console.print(make_project_id(topic))


@app.command("serve")
def serve_cmd(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port"),
) -> None:
    """Start the optional FastAPI web UI backend."""
    try:
        import uvicorn
    except ImportError as exc:
        console.print("Install web extras: pip install -e '.[web]'")
        raise typer.Exit(code=1) from exc
    uvicorn.run("web_ui.api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
