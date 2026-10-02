# YouTube Data API facts this skill relies on

Checked 2026-10-02. Re-check the linked pages if something behaves differently; quotas and
policies have changed twice since late 2025.

## Scheduling (`status.publishAt`)

- **Only private videos can be scheduled.** You can set `publishAt` only when
  `privacyStatus` is `private` and the video has never been published. When you set it with
  `videos.update`, you must send `privacyStatus: private` again.
- Format is ISO 8601. `cli.py upload` sends UTC (`2026-10-09T14:00:00Z`).
- **A time in the past publishes the video immediately.** That's why `load_plan` refuses
  anything less than 15 minutes ahead.
- YouTube does the publishing at that time, so nothing has to keep running.

Source: https://developers.google.com/youtube/v3/docs/videos (status.publishAt)

## The audit lock (the big one)

> All videos uploaded via the `videos.insert` endpoint from unverified API projects created
> after 28 July 2020 will be restricted to private viewing mode. To lift this restriction,
> each API project must undergo an audit.

- The upload **succeeds**, then the video is locked private, and `publishAt` doesn't override
  the lock. A scheduled upload from an unaudited project never goes public.
- Fix: the YouTube API Services audit, at https://support.google.com/youtube/contact/yt_api_form.
  Google gives no timeline; developer reports run from about 2 weeks to several months.
- This is **not** the same as OAuth app verification (the yellow banner on the consent
  screen). A single-user app can skip OAuth verification but still needs the audit to post
  publicly.

Sources: https://developers.google.com/youtube/v3/docs/videos/insert ·
https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits

## OAuth token lifetime

- If the consent screen is **External + Testing**, refresh tokens expire after 7 days. Use
  **In production**. (Source: https://developers.google.com/identity/protocols/oauth2)
- An unverified production app shows an "unverified app" screen at login and has a 100-user
  lifetime cap. Neither matters for one creator.

## Quota (default, per Cloud project, resets at midnight Pacific)

| Call | Cost |
|---|---|
| `videos.insert` | 1 unit from a separate **Video Uploads** bucket of 100 per day (since 1 June 2026; it used to be 1,600 units of 10,000) |
| `thumbnails.set`, `playlistItems.insert`, `playlists.insert`, `videos.update` | 50 units each from the shared 10,000 |
| `captions.insert` | 400 |
| `videos.list`, `channels.list`, `playlists.list` | 1 |

A long video plus 3 Shorts with thumbnail, captions and playlist costs about 4 uploads and
about 520 shared units. Failed and invalid calls still cost quota, so validate first (that's
what `--dry-run` is for).

Sources: https://developers.google.com/youtube/v3/docs/videos/insert ·
https://www.outstand.so/blog/youtube-api-pricing-quota

## Shorts

- There's no Shorts endpoint or flag. A **vertical or square** video of **3 minutes or less**
  (since 15 Oct 2024) is classified as a Short automatically. `#shorts` in the title doesn't
  decide it. `load_plan` reads the real shape and length with ffprobe.
- `thumbnails.set` works on Shorts, but YouTube shows a custom Short thumbnail only on some
  surfaces (channel page, search, embeds), not in the Shorts feed.

Sources: https://postproxy.dev/blog/youtube-upload-api-guide/ ·
https://developers.google.com/youtube/v3/docs/thumbnails/set

## Metadata limits

- Title: 1–100 characters. Description: 5,000. Tags: 500 characters total, counting the comma
  between tags and adding 2 for any tag that contains a space (it gets quoted).
- **`<` and `>` are rejected** in titles and descriptions (`invalidTitle` /
  `invalidDescription`).
- `status.containsSyntheticMedia`: disclosure for realistic altered or synthetic content, such
  as making a real person appear to say something they didn't. A cloned narration voice is the
  creator's call; the skill asks them. `selfDeclaredMadeForKids` is always sent explicitly.
- Custom thumbnails need a phone-verified channel; the file must be ≤ 2 MB through the API.

## What the API can't do (so the skill hands these over as a checklist)

| Want | API |
|---|---|
| Pin a comment | can post (`commentThreads.insert`), **cannot pin** |
| Shorts "Related video" link | no field |
| End screens, cards | no API |
| Community posts, polls | no API |
| Test & Compare (title/thumbnail A/B) | no API |
