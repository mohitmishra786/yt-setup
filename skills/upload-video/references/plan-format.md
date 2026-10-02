# `publish/upload.json`: the upload plan

`cli.py upload --project <id>` reads `projects/<id>/publish/upload.json` (or `--plan <path>`)
and records progress in `projects/<id>/publish/uploaded.json`. Paths in the plan are relative
to the project folder.

## Top level

| Field | Default | Meaning |
|---|---|---|
| `timezone` | `channel.timezone` | zone for `publish_at` values without an offset |
| `contains_synthetic_media` | `publisher.contains_synthetic_media` | AI disclosure. **Required**: the run refuses while both are unset |
| `made_for_kids` | `publisher.made_for_kids` (false) | `selfDeclaredMadeForKids` |
| `category_id` | `publisher.category_id` ("27" = Education) | YouTube category |
| `language` | `publisher.default_language` ("en") | snippet language + caption track language |
| `playlist` | `publisher.playlist` | playlist **title** for items with `"playlist": true` |
| `create_playlist` | false | create that playlist (public) if it doesn't exist |
| `items` | — | in posting order |

## Items

| Field | Required | Meaning |
|---|---|---|
| `key` | yes | unique id (`video`, `short_01`, …); used by `--only` and `{url:key}` |
| `file` | yes | the video file |
| `title` | yes | 1–100 chars, no `<` `>` |
| `description` | no | ≤ 5000 chars, no `<` `>`; `{url:<key>}` → `https://youtu.be/<id>` of an **earlier** item |
| `tags` | no | list; ≤ 500 chars total (commas count, a tag with a space counts +2) |
| `publish_at` | no | `"YYYY-MM-DD HH:MM"` in `timezone`, or ISO with offset. Set → uploaded private and scheduled. Must be ≥ 15 min ahead |
| `privacy` | no | only when there is no `publish_at`: `private` (default) / `unlisted` / `public` (public needs `--confirm-public`) |
| `kind` | no | `short` or `video`, checked against the file. YouTube decides by shape: vertical or square and ≤ 3 min means a Short |
| `thumbnail` | no | jpg/png ≤ 2 MB (long video: `poster.jpg`) |
| `captions` | no | SRT; long video: `publish/captions.srt` from `scripts/script_srt.py` |
| `playlist` | no | true → add to the top-level `playlist` |

## Mapping the publish kit

| Publish kit | upload.json |
|---|---|
| `video.md` → **Use:** title | `items[video].title` |
| `video.md` → Description block | `items[video].description` (verbatim) |
| `video.md` → Tags block | `items[video].tags` (split on commas) |
| `shorts.md` → per Short title / description / tags | one item each; `<FULL VIDEO LINK>` → `{url:video}` |
| `schedule.md` dates + `channel.post_time` | `publish_at` per item |
| `video.md` → Playlist | top-level `playlist` |
| A `/create-short` project (`publish/short.md`) | one item, `file: "final.mp4"`, and its "Full video" link written out literally if the long video is already live |

Not in the plan (the API can't do these): the pinned comment, end screen, cards, the Shorts
"Related video" link, the community poll, Test & Compare. They go on the checklist from
`SKILL.md` §6.

## Example (KernelKafe, pointers video; descriptions shortened here)

```json
{
  "timezone": "Asia/Kolkata",
  "playlist": "Systems Deep Dives",
  "create_playlist": false,
  "items": [
    {
      "key": "video",
      "file": "final.mp4",
      "publish_at": "2026-10-09 19:30",
      "title": "Pointers in C, Explained: Raw Pointers vs unique_ptr vs shared_ptr",
      "description": "A pointer is just an address, yet that one number is behind most crashes…\n\nChapters:\n0:00 A pointer is just a number\n…",
      "tags": ["pointers in c", "c pointers", "unique_ptr", "shared_ptr", "kernelkafe"],
      "thumbnail": "poster.jpg",
      "captions": "publish/captions.srt",
      "playlist": true
    },
    {
      "key": "short_02",
      "file": "shorts/short_02.mp4",
      "publish_at": "2026-10-10 19:30",
      "title": "This C bug prints garbage and exits 0 #shorts",
      "description": "A raw pointer owns nothing…\n\nFull video: {url:video}\n\n#cprogramming #debugging #memorysafety",
      "tags": ["use after free", "dangling pointer", "kernelkafe"]
    }
  ]
}
```

`contains_synthetic_media` is missing on purpose: KernelKafe sets it once in `config.yaml`
after the creator decides.

## `uploaded.json` (written by the command, never by hand except to drop a deleted test)

```json
{
  "_playlist_id": "PL…",
  "video": {
    "video_id": "abc123", "url": "https://youtu.be/abc123", "kind": "video",
    "privacy": "private", "publish_at": "2026-10-09T14:00:00Z",
    "steps": {"thumbnail": true, "captions": true, "playlist": true}
  }
}
```

A step value of `"failed: …"` is retried on the next run. Items with a `video_id` are never
uploaded again. If a video was deleted in Studio, remove its entry so it can be re-uploaded.
