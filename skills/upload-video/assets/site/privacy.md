---
title: Privacy Policy · <CHANNEL> Publisher
---

# <CHANNEL> Publisher: Privacy Policy

*Last updated: <DATE>* · [Home](./) · [Terms of Service](terms.html)

<CHANNEL> Publisher ("the tool") is a private command-line tool used only by the owner of the
YouTube channel <HANDLE> (<CHANNEL_URL>) to upload and schedule videos,
thumbnails, captions and playlist entries on that channel. It has no other users.

## YouTube API Services and Google

The tool uses **YouTube API Services**. By using the tool you agree to be bound by the
[YouTube Terms of Service](https://www.youtube.com/t/terms). Google's handling of data is
described in the [Google Privacy Policy](https://policies.google.com/privacy)
(https://policies.google.com/privacy).

## What the tool accesses

When the owner signs in with Google (OAuth 2.0), the tool requests two permissions for the
owner's own channel:

- `youtube.upload`: to upload the owner's videos and set their thumbnails.
- `youtube.force-ssl`: to add caption files and playlist entries, and to read back the
  upload and publishing status of the owner's own videos.

It does not access any other channel, any other user's data, comments, subscribers,
analytics or payment information.

## How the data is used

The tool uses this access only to upload the owner's own files and to confirm that each video
was uploaded and scheduled correctly. Nothing is used for advertising, profiling, analytics or
any other purpose.

## What is stored, and where

- **OAuth token:** one access/refresh token, stored only in a file on the owner's own computer
  (readable only by the owner). It is never sent anywhere except to Google.
- **Upload records:** for each of the owner's uploads, a local file records its video ID,
  title, privacy and scheduled publish time, so an interrupted upload can resume and be
  checked. It stays in the owner's project folder on their computer.

Nothing is stored on any server operated by the tool, because there is none.

## Sharing

No data is sold, shared with, or disclosed to any third party. The only service the tool
talks to is Google/YouTube, through YouTube API Services.

## Deleting data and revoking access

- **Revoke access** at any time from the Google Account security settings page:
  https://security.google.com/settings/security/permissions (or
  https://myaccount.google.com/permissions). After that the tool can no longer access the
  channel.
- **Delete stored data** by deleting the token file (`.credentials/youtube_token.json`) and the
  upload records (`publish/uploaded.json`) from the owner's computer. No copy exists anywhere
  else.
- Videos already uploaded remain on YouTube and are managed or deleted in YouTube Studio.

## Changes and contact

Changes to this policy are published on this page with a new date.
Contact: <EMAIL>
