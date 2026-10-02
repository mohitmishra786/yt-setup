# Shorts + publish kit (every long video ends with this)

## 1. Cut 3–5 Shorts from the finished video

Write `projects/<id>/shorts.json`. Each Short covers whole scenes, so every cut lands on a
narration boundary:

```json
{"accent": "#5aa9f0", "shorts": [
  {"id": "short_01", "slides": [1, 2], "hook": ["Where do your", "bytes actually go?"]}
]}
```

- **Length: 30–45s each, hard max 60s.** Scene slot lengths are in
  `composition/index.html` (`data-duration` of each `scene-NN`). The script refuses anything
  over 60s.
- Pick segments that stand alone: one idea each, opening on a sentence that doesn't lean on
  the previous scene. The on-screen hook (2 lines, ≤ ~22 characters per line; the second line
  is drawn in the accent) supplies the missing context.
- Skip the intro, agenda, recap and outro scenes.
- Scene host ids must be `scene-NN`, where NN is the outline slide index (the long-form
  builder already follows this).

```bash
.venv/bin/python skills/create-video/assets/build_shorts.py projects/<id>          # all
.venv/bin/python skills/create-video/assets/build_shorts.py projects/<id> --only 2 --draft
```

For each Short, the script:
- cuts the range from `final.mp4`, cropped to the diagram area
- builds a portrait HyperFrames project with the hook, big word-by-word captions and the
  channel wordmark (config.yaml `channel:`), all inside the Shorts safe zones
- runs `hyperframes check` and renders to `shorts/short_NN.mp4`

Then pull 3–4 frames per Short and look at them before handing over.

## 2. Write `projects/<id>/publish/`

- **`video.md`:**
  - title plus 2 alternates for Test & Compare (≤ 70 characters ideal, 100 max)
  - description: hook line, what's covered, chapters, sources/real-output note, channel link, 3 hashtags
  - tags (≤ 500 characters total)
  - category, captions file, pinned comment, playlist, end-screen and cards notes
- **`shorts.md`:** for each Short:
  - file and length
  - title (≤ 60 characters plus `#shorts`)
  - 2–3 line description ending with `Full video: <FULL VIDEO LINK>` and 3 hashtags
  - tags
  - "Related video → the long video"
- **`schedule.md`:** 7–10 days:
  - long video on day 1
  - Shorts every 1–2 days, strongest hook first
  - one community post (poll)
  - a review day with concrete thresholds (CTR, drop-off point)
  - times in `channel.timezone` at `channel.post_time`, noting the US-morning equivalent

- **`upload.json`:** the same titles, descriptions, tags and dates as a machine plan for
  `/upload-video` (format: `skills/upload-video/references/plan-format.md`). Use `{url:video}`
  where the Shorts say `<FULL VIDEO LINK>`; no `<` or `>` anywhere.

Rules:
- Every factual line in titles and descriptions must be something the video actually shows.
- No clickbait the video doesn't pay off.
- Check lengths: titles ≤ 100, tags ≤ 500, description ≤ 5000 characters.
