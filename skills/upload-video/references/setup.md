# One-time setup: connect a YouTube channel to the API

About 20 minutes of browser clicks, plus Google's audit, which can take weeks. Walk the creator
through it **one part at a time**, and ask for a screenshot whenever they're unsure: the Google
Cloud console moves things around.

Fill these in from `config.yaml` → `channel:` and from the creator:

| Placeholder | Meaning | KernelKafe (worked example) |
|---|---|---|
| `<CHANNEL>` | channel name | KernelKafe |
| `<HANDLE>` | `channel.handle` | @kernelkafe |
| `<CHANNEL_URL>` | `channel.url` | https://www.youtube.com/@kernelkafe |
| `<EMAIL>` | the Google account that owns the channel | (the creator's Gmail) |
| `<GH_USER>` | their GitHub username (for the privacy page) | mohitmishra786 |
| `<PROJECT_ID>` | the Cloud project id, from part 1 | kernelkafe-publisher |

Use the Google account that **owns the channel** for everything below. If the channel is a
Brand Account, use the account that manages it; you pick the brand channel at login (part 6).

## Part 1: create the project and enable the API

1. Open https://console.cloud.google.com/projectcreate. Set the name to
   `<channel-slug>-publisher` and click **Create**.
2. Check that the project picker at the top shows the new project. The Welcome page
   shows **Project ID**: that's `<PROJECT_ID>`, which the audit form needs.
3. Enable the API: open
   `https://console.cloud.google.com/apis/library/youtube.googleapis.com?project=<PROJECT_ID>`
   and click **Enable**.
   - The dashboard and Welcome page have **no** Enable button. Use this link, or go to
     **APIs and services → + Enable APIs and services**, search "YouTube Data API v3",
     open it, and click **Enable**.
   - Choose **YouTube Data API v3**, not the Analytics or Reporting API.
   - You'll know it worked when the page shows **Manage** / **Disable API**.
4. Ignore the "$300 free trial / Start free" banner. The API needs no billing.

## Part 2: the OAuth consent screen ("Google Auth Platform")

Open `https://console.cloud.google.com/auth/overview?project=<PROJECT_ID>`, or search
"Google Auth Platform". The Welcome page doesn't link here directly.

1. Click **Get started** to open a four-section wizard:
   - **App information:** app name `<CHANNEL> Publisher`, support email `<EMAIL>`.
   - **Audience:** **External**. Internal is greyed out without an organisation, which is
     expected.
   - **Contact information:** `<EMAIL>`.
   - **Finish:** agree to the policy → **Continue** → **Create**. The toast says
     "OAuth configuration created".
2. **Data access** (left sidebar) → **Add or remove scopes** → filter `youtube` → tick
   **exactly two** rows:
   - `.../auth/youtube.upload`: uploads and thumbnails
   - `.../auth/youtube.force-ssl`: captions, playlists, comments, and reading video status

   Then **Update** → **Save**. Remove any extra YouTube scopes with the trash icon
   (`youtube`, `youtube.readonly`, `channel-memberships.creator`,
   `third-party-link.creator`). They aren't needed, and they widen what a leaked token can do.
3. **Branding** (left sidebar):
   - **Do not upload an app logo.** A logo forces Google's full app verification for a
     production app. If one was uploaded, click **Remove**.
   - **Application home page** and **Application privacy policy link**: both set to the
     privacy page from part 3 (e.g. `https://<GH_USER>.github.io/<channel-slug>-privacy/`).
   - **Terms of Service**: leave empty.
   - **Authorised domain 1**: the privacy page's domain (`<GH_USER>.github.io`). Don't use
     `youtube.com`; it isn't yours, and every link above must be on an authorised domain.
   - **Save**.
4. **Audience** → **Publish app** → **Confirm**. It should now say **In production**.
   - If **Publish app** is greyed out with "homepage URL and privacy policy URL are
     required", step 3 isn't saved yet.
   - **Why production matters:** in Testing, refresh tokens expire after 7 days, so the
     creator would have to log in again every week.
   - The yellow "Your app requires verification… Go to verification centre" banner is
     expected. **Ignore it.** That review is for apps that other people use. A single-user
     app runs unverified: the creator clicks past an "unverified app" screen once, and there's
     a 100-user cap. OAuth verification is also **separate from the YouTube API audit** in
     part 5.

## Part 3: the privacy-policy page

Google wants a public privacy-policy URL for the consent screen and for the audit. Use GitHub
Pages. Only create it with `gh` when the creator asks you to, since it's a public repo under
their account:

```bash
gh auth status                                   # must show <GH_USER>
D=$(mktemp -d) && cd "$D"
# fill the template: skills/upload-video/assets/privacy-policy.md -> README.md
git init -q -b main && git add README.md && git commit -q -m "Add privacy policy"
gh repo create <GH_USER>/<channel-slug>-privacy --public \
  --description "Privacy policy for <CHANNEL> Publisher" --source . --push
gh api -X POST repos/<GH_USER>/<channel-slug>-privacy/pages \
  -f "source[branch]=main" -f "source[path]=/"
# wait until it's live (about a minute):
curl -s -o /dev/null -w '%{http_code}\n' https://<GH_USER>.github.io/<channel-slug>-privacy/
```

Without `gh`, create the repo on github.com with a README, paste the template in, and set
**Settings → Pages → Deploy from a branch → main / (root)**.

## Part 4: the desktop OAuth client

1. **Clients** (left sidebar) → **+ Create client**. You can also use **Create OAuth client**
   on the Overview page.
2. **Application type: Desktop app**. Name it `yt-studio`.
3. **Leave "This client will be used by an AI-powered agent" unticked.** The client belongs to
   the repo's own CLI, which runs fixed code with the creator's own login. The agent only
   starts that command.
4. **Create** → **Download JSON**. Do it now, because the secret is only fully shown here.
5. Move the file into the repo. You can do this for the creator:

   ```bash
   mkdir -p .credentials && chmod 700 .credentials
   mv ~/Downloads/client_secret_*.apps.googleusercontent.com.json .credentials/client_secret.json
   chmod 600 .credentials/client_secret.json
   git check-ignore -v .credentials/client_secret.json   # must print the .gitignore rule
   ```

   Never print the file's contents, and never commit it.
6. A new client can take up to 5 minutes to start working.

## Part 5: the YouTube API audit (start it now; it's the slow part)

Without it, **every video uploaded through the API is locked private**, including scheduled
ones (see `api-facts.md`). Form: https://support.google.com/youtube/contact/yt_api_form

| Field | Answer |
|---|---|
| Project ID | `<PROJECT_ID>` |
| Use case | "Internal, single-user tool. Uploads and schedules my own videos and Shorts (with thumbnail, captions and playlist) to my own channel `<HANDLE>` (`<CHANNEL_URL>`). No other users; no data from other users is accessed or stored." |
| Volume | about 4–6 uploads per week, well within default quota |
| Privacy policy | the GitHub Pages URL from part 3 |

Google publishes no timeline. Reports range from about 2 weeks to several months. Everything
else works meanwhile, but uploads stay private.

## Part 6: log in once

The creator runs this in the Claude Code prompt (the `!` makes the browser open on their
machine):

```
! .venv/bin/python cli.py youtube-auth
```

1. Pick `<EMAIL>`. If asked, pick the `<CHANNEL>` channel.
2. On "Google hasn't verified this app": **Advanced → Go to `<CHANNEL>` Publisher (unsafe)**.
   That's expected for their own unverified app.
3. Tick both permissions → **Continue** → close the tab when it says the flow has completed.
4. The terminal prints `Authorised <CHANNEL> (<HANDLE>) channel id UC…`. A handle mismatch
   exits non-zero; re-run with `--relogin` and choose the right account or brand channel.

The token is saved to `.credentials/youtube_token.json` (mode 600) and refreshes itself. The
browser only comes back if the token is revoked
(https://myaccount.google.com/permissions) or a scope is added to `SCOPES`.

## Already done for KernelKafe (2026-10-02/03)

Project `kernelkafe-publisher`, API enabled, consent screen **In production** with the two
scopes, privacy page https://mohitmishra786.github.io/kernelkafe-privacy/ (repo
`mohitmishra786/kernelkafe-privacy`), Desktop client `yt-studio`, and a token authorised for
Kernel Kafe (@kernelkafe), channel id `UCOOCHObiwKlOrcNigGQC5AQ`. The channel is
phone-verified (custom thumbnails allowed). The audit form is the step still to check.
