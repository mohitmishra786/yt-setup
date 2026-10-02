---
name: upload-video
description: Upload and schedule a finished long video and its Shorts to the creator's own YouTube channel through the YouTube Data API — exact-script captions, thumbnail, playlist, AI-content disclosure, YouTube-side scheduling (publishAt), resumable and verified — plus the one-time Google Cloud / OAuth / audit setup walked through step by step. Use when someone says "/upload-video", "upload/schedule/publish my video or shorts", "post this to YouTube", or asks how to connect their channel to the API.
---

# /upload-video

You take a finished project (`/create-video` or `/create-short`) and put it on the creator's
channel **on the schedule from its publish kit**. YouTube does the scheduling: each video is
uploaded now as *private* with a `publishAt` time and YouTube makes it public at that moment.
Nothing has to run at post time — no cron, no cloud agent, the laptop can be off.

**The channel** (name, handle, timezone, posting slot) comes from `config.yaml` → `channel:`;
upload defaults from `config.yaml` → `publisher:`. Never hardcode a channel. The OAuth token in
`.credentials/` decides which channel is written to, and `cli.py youtube-auth` checks it against
`channel.handle`.

**This is outward-facing.** Uploading publishes the creator's work under their name. Show the
dry run and get an explicit "yes" before any real upload, every time. Never use
`--confirm-public` unless they asked for an immediate public post.

## 0. Is this machine connected?

```bash
.venv/bin/python cli.py youtube-auth      # prints "Authorised <channel> (@handle) channel id UC…"
```

- **Works** → step 1.
- **"client secrets not found"** → first-time setup. Walk the creator through
  `references/setup.md` **one part at a time** (it is all browser clicks in Google Cloud; ask
  for a screenshot when they are unsure — the console UI moves around). Do the parts you can
  yourself: moving the downloaded JSON, publishing the privacy-policy page with `gh` (only when
  they ask you to; it creates a public repo under their account).
- **Browser login needed** → the creator runs it with a leading `!` in the Claude Code prompt
  (`! .venv/bin/python cli.py youtube-auth`) so the browser opens on their machine.
- **Handle mismatch** → `--relogin` and pick the right Google account / Brand channel.

Also ask once whether their Google Cloud project has **passed the YouTube API audit**. Until it
has, every API upload is locked private and `publishAt` is ignored (`references/api-facts.md`).
Scheduling still "succeeds", so check before promising a schedule; offer the test upload in
step 4 if they don't know.

## 1. Captions from the script, not from Whisper

```bash
.venv/bin/python skills/upload-video/scripts/script_srt.py projects/<id>   # -> publish/captions.srt
```

`transcript.srt` is Whisper listening to the render, so it carries every mishearing the voice
check caught. `script_srt.py` uses `audio/words.json` + the real clip starts in
`composition/index.html`, and maps phonetic spellings back (`caption_word()`). Skim the first
cues. Shorts already have burned-in captions; no caption track needed.

## 2. Write `projects/<id>/publish/upload.json`

Translate the publish kit (`publish/video.md`, `shorts.md`, `schedule.md`, or a Short's
`publish/short.md`) into the machine plan. Format, rules and a full example:
`references/plan-format.md`. In short:

- One item per file, **in posting order**; the long video first (key `video`).
- `publish_at` = the date/time from `schedule.md`, local to `channel.timezone`
  (`"2026-10-09 19:30"`). Must be ≥ 15 min in the future (a past time publishes immediately).
- Titles ≤ 100 chars, descriptions ≤ 5000, tags ≤ 500 (commas and quotes count). **No `<` or
  `>` anywhere in titles/descriptions** — YouTube rejects them (`unique_ptr<int>` → `unique_ptr`).
- Link a Short to the long video with `{url:video}`; it becomes `https://youtu.be/<id>` once
  the video is uploaded (the link works when the video goes public).
- Long video: `"thumbnail": "poster.jpg"`, `"captions": "publish/captions.srt"`,
  `"playlist": true`. Shorts: no thumbnail by default (the API sets it but YouTube shows it
  only on some surfaces).
- **AI disclosure (`contains_synthetic_media`)**: ask the creator once. A cloned voice saying
  words they never recorded is the kind of realistic synthetic content YouTube asks to label;
  recommend `true`, but it is their call. Suggest saving the answer in `config.yaml` →
  `publisher.contains_synthetic_media` so you never ask again. The command refuses to run
  while it's unset.

## 3. Dry run → show → get a yes

```bash
.venv/bin/python cli.py upload --project <id> --dry-run
```

It validates everything (files, lengths, `<>`, links, times, Short shape via ffprobe) and prints
the table: key, kind, duration and size, go-live time in the channel timezone **and** UTC,
title, already-uploaded state. Paste the table to the creator with one line per item and ask
for an explicit go-ahead. Fix every validation error by editing `upload.json`, not by
skipping items.

## 4. Upload

```bash
# first time on a new API project, or audit status unknown: one private test draft
.venv/bin/python cli.py upload --project <id> --only short_01 --no-schedule --yes
# the real run (after the creator said yes) — long uploads: run in the background
.venv/bin/python cli.py upload --project <id> --yes
```

- Each item: `videos.insert` (private + `publishAt`, made-for-kids flag, synthetic flag,
  language) → thumbnail → captions → playlist. The video id is written to
  `publish/uploaded.json` **before** the side steps, so a crash never causes a re-upload.
- Re-running the same command resumes: finished uploads are skipped, failed side steps retry.
- A `--no-schedule` test draft stays private forever. Tell the creator to delete it in Studio
  after checking it (you don't delete videos), then remove its entry from `uploaded.json`
  before the real run, or it will be treated as done.

## 5. Verify what YouTube actually has

```bash
.venv/bin/python cli.py upload --project <id> --verify
```

| privacy | publishes | meaning |
|---|---|---|
| private | a date | scheduled correctly |
| private | – | a `--no-schedule` draft — or, if it was scheduled, the API project isn't audited (locked) |
| public | – | live |
| any | problem column set | processing/rejection failure: read it to the creator |

The API returning success is not proof; Studio is. Ask the creator to glance at Studio →
Content once after the first real run on a new setup.

## 6. Hand over the manual checklist

The API cannot do these; list them per date from `schedule.md`:
- **Pin the comment** (the API can post, not pin) — text is in `video.md`.
- **Shorts → "Related video"** link to the long video (no API field).
- **End screens and cards** (no API).
- **Community posts / polls** (no API).
- **Test & Compare** title/thumbnail A/B (no API).

## Gates (do not skip)

- [ ] `youtube-auth` shows the creator's channel and it matches `channel.handle`.
- [ ] Audit status known; if not audited, the creator knows scheduled posts will stay private.
- [ ] Captions built from the script (`publish/captions.srt`), not `transcript.srt`.
- [ ] `contains_synthetic_media` decided by the creator, not by you.
- [ ] Dry run clean (no errors), shown to the creator, explicit yes received.
- [ ] `--verify` run after uploading; every scheduled item shows its publish time.
- [ ] Manual checklist handed over.

## Files

- `references/setup.md` — one-time Google Cloud + OAuth + audit walkthrough, with every
  console pitfall met so far.
- `references/api-facts.md` — the API rules this relies on (publishAt, audit lock, quotas,
  Shorts detection, what the API can't do), with sources.
- `references/plan-format.md` — `upload.json` schema and a complete example.
- `scripts/script_srt.py` — exact-script captions.
- `assets/privacy-policy.md` — privacy-policy template for the OAuth consent screen.
- Code: `cli.py upload` / `cli.py youtube-auth` → `modules/publisher/scheduler.py`,
  `modules/publisher/youtube_upload.py`; tests in `tests/test_upload_scheduler.py`.
