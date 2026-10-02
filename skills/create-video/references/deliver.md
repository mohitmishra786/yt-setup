# Render and deliver

## Poster frame

Pick the strongest **settled** frame — the payoff diagram or the hook, text fully in, not
mid-transition. Write its time to `projects/<id>/poster.json`:

```json
{ "time": 41.5 }
```

The `hyperframes` stage extracts it to `poster.jpg` and bakes it in as frame 0 of
`final.mp4` (replacing, not adding, a frame — duration and audio sync are unchanged), so
every platform's auto-thumbnail shows it. Omit `poster.json` to skip.

## Render

```bash
# optional quick review render first
YT_STUDIO_HF_QUALITY=draft .venv/bin/python cli.py run --project <id> --only hyperframes
# final
.venv/bin/python cli.py run --project <id> --only hyperframes
```

The stage runs `npx hyperframes check`, renders `composition/` to `final.mp4`, bakes the
poster, and checkpoints `state.json`. Long-form renders take a while (roughly
proportional to frame count) — run it in the background and wait for completion.

After render, extract 6–12 frames across the video with ffmpeg and look at them once more:

```bash
ffmpeg -v error -i projects/<id>/final.mp4 -vf "fps=1/5,scale=360:-1,tile=6x2" /tmp/<id>-sheet.png
```

## Downstream

```bash
.venv/bin/python cli.py run --project <id> --from-stage transcriber --dry-run-publish
```

Produces `transcript.srt/.json`, `chapters.txt`, auto Shorts (long-form only; skipped if
Vantage is not running — set `YT_STUDIO_SKIP_VANTAGE=1`), and `publish_manifest.json`.
Uploading and scheduling is `/upload-video` (`cli.py upload`), not this stage. Never upload
(drop `--dry-run-publish`) unless the user explicitly asks; public uploads
also need `--privacy public --confirm-public`.

## Share copy

Write `projects/<id>/share-copy.txt`: 1–3 sentences, postable as-is, specific to the topic,
matching the tone. No "excited to share", no "In this video". Lead with the hook claim.

## Tell the user

- Where `final.mp4`, `poster.jpg`, `share-copy.txt`, `chapters.txt` are.
- Actual duration vs requested.
- One sentence on the creative angle.
- Offer to re-roll a specific scene, change tone, or run the upload.
