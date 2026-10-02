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
   - **Application home page**: the site's homepage from part 3
     (`https://<GH_USER>.github.io/<channel-slug>-privacy/`).
   - **Application privacy policy link**: `…/privacy.html` on that site.
   - **Application Terms of Service link**: `…/terms.html` on that site.
   - **Authorised domain 1**: the site's domain (`<GH_USER>.github.io`). Don't use
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

## Part 3: the policy site (homepage, privacy policy, terms)

The consent screen needs a homepage and a privacy-policy URL. The audit form (part 5) asks for
screenshots of all three pages: a privacy policy with YouTube sections, the Google Privacy
Policy link and deletion steps; a homepage that links to it with YouTube visible; and Terms of
Service. The templates in `assets/site/` cover all of that. Host them on GitHub Pages. Only
create the repo with `gh` when the creator asks you to, because it's a public repo under their
account.

Fill the placeholders: `<CHANNEL>` (short name, e.g. KernelKafe), `<CHANNEL_TITLE>` (title as
YouTube shows it), `<HANDLE>`, `<CHANNEL_URL>`, `<CHANNEL_URL_SHORT>` (without `https://www.`),
`<WHAT_THE_CHANNEL_MAKES>`, `<SOURCE_URL>` (this repo's public URL), `<EMAIL>`, `<DATE>`.
Keep every statement true; edit the text if the creator's setup differs. For example, if the
repo isn't public, drop the source-code line.

```bash
gh auth status                                   # must show <GH_USER>
D=$(mktemp -d) && cp skills/upload-video/assets/site/* "$D"/ && cd "$D"
# replace the <PLACEHOLDERS> in index.md, privacy.md, terms.md, _config.yml (sed or by hand)
grep -n '<[A-Z_]*>' *.md _config.yml             # must print nothing
git init -q -b main && git add -A && git commit -q -m "Add homepage, privacy policy and terms"
gh repo create <GH_USER>/<channel-slug>-privacy --public \
  --description "Policies for <CHANNEL> Publisher" --source . --push
gh api -X POST repos/<GH_USER>/<channel-slug>-privacy/pages \
  -f "source[branch]=main" -f "source[path]=/"
for p in "" privacy.html terms.html; do        # wait until all three return 200 (about a minute)
  curl -s -o /dev/null -w "%{http_code} /$p\n" "https://<GH_USER>.github.io/<channel-slug>-privacy/$p"
done
```

Without `gh`, create the repo on github.com, upload the four files, and set
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

Without it, **every video uploaded through the API can be locked private**, including scheduled
ones (see `api-facts.md`). Nobody sends you this form; the creator submits it:
https://support.google.com/youtube/contact/yt_api_form. Fill it in honestly as a single-user
tool. Overstating usage or users makes rejection more likely. Answers that worked for
KernelKafe (submitted 2026-10-03):

**Section 1, request type:** "Complete a compliance audit to request additional quota" (the
other option is only for re-audits Google requested). Say in Section 5 that no extra quota is
needed.

**Section 2, organisation and contact:**

| Field | Answer |
|---|---|
| Applying as | **An individual user** |
| Legal name, address | the creator's own (only they can fill this) |
| Organisation's legal name / parent company | `self` |
| Primary website | `<CHANNEL_URL>` |
| Organisation size/type | **Independent developer/sole trader** |
| Contacts | the creator's name + `<EMAIL>`; technical and business contacts "Same as primary contact" |

**Section 3, business model:**
- **Describe your work:** the channel, what it makes, and that "<CHANNEL> Publisher" is a
  private single-user CLI that uploads and schedules the owner's own videos (title,
  description, tags, thumbnail, captions, playlist, publishAt). It never touches other
  channels or users' data, has no other users, and stores only its OAuth token locally.
- **Target audience:** **Internal users** only.
- **Monetisation:** **Other**: "Not monetised; a private tool used only by the channel owner."
- **Google Partner Manager:** No. Content owner IDs and Ads IDs: leave empty.

**Section 4, API client:**

| Field | Answer |
|---|---|
| API client name | `<CHANNEL> Publisher` (contains "YouTube"? **No**; the name must not) |
| Primary access URL | the public source repo (`<SOURCE_URL>`), since there is no hosted app |
| Privacy policy URL | `…/privacy.html` |
| Terms of Service URL | `…/terms.html` |
| Publicly accessible? | **No** |

These fields prefill `https://`, so pasting a full URL gives `https://https://…` and the error
"Must start with https://". Select all, delete, then paste.

"Not publicly accessible" adds a **demo account** block. **Never enter the creator's Google
email or password.** Use `N/A` for the credentials and explain in "special instructions" that
it's a CLI with no login of its own, signing in with the owner's Google account via OAuth, with
evidence attached and the source public.

**Section 5, use case and quota:**

| Field | Answer |
|---|---|
| Project number | from the Cloud console Welcome page (e.g. `651592352294`) |
| Use case | only **Video uploading and account management**. "Internal company tool" adds dashboard evidence and doesn't fit an individual |
| Uses Google sign-in (OAuth)? | **Yes** |
| Expected API usage volume | **Fewer than 1,000 requests per day** (a full scheduling day is about 20 requests) |
| Endpoints | videos.insert, thumbnails.set, captions.insert, playlistItems.insert, playlists.list, videos.list, channels.list |
| Total quota | **No change/Default quota (10K quota points)** |
| If per-day/per-minute/justification fields still appear | `10000` / `600` / "No quota increase is needed … the reason for this request is the audit itself: uploads from this unaudited project are restricted to private, and scheduled uploads (status.publishAt) need to become public on time." A separate videos.insert box: `10` |

**Evidence**: one file per slot, PNG/JPEG/PDF, ≥ 1280×720, under 10 MB:

| Slot | File | Who makes it |
|---|---|---|
| Privacy policy screenshots | `privacy-policy-page.png`: browser with address bar on `…/privacy.html`, YouTube API Services, the Google Privacy Policy link and the deletion section visible (zoom out with Cmd − to fit) | creator |
| Homepage screenshot | `homepage-privacy-link.png`: the site root, showing the YouTube API Services notice and the Privacy/Terms links | creator |
| Terms of Service documentation | `terms-of-service-page.png` | creator |
| Conditional (OAuth + upload interface) | one PDF with: the Google consent screen listing both scopes (`cli.py youtube-auth --relogin`, screenshot before **Continue**, then continue); https://myaccount.google.com/permissions → the app's entry (don't remove it); and `upload-interface-cli.png`. Merge into one PDF for them | creator + you |
| Architecture diagram / User flow diagrams / Other supporting materials | `architecture-diagram.png` / `user-flow-diagram.png` / `upload-interface-cli.png` | you: `scripts/audit_evidence.py --out ~/Desktop/youtube-audit-evidence --project <uploaded id>` |

The CLI evidence needs a project that's already been uploaded, so run a private test upload
first if needed. Screenshots of web pages must be real, taken in the creator's browser; don't
fake browser chrome.

**Section 7:** the creator reads and ticks every attestation.

Google publishes no timeline. Reports range from about 2 weeks to several months, and the
reply comes by email to the contact address. Everything else works meanwhile. In practice the
uploads may still show **Scheduled** in Studio (KernelKafe's did, 2026-10-03). The proof is
whether the first one actually turns public at its time: `cli.py upload --verify`.

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

- Cloud project `kernelkafe-publisher`, YouTube Data API v3 enabled.
- Consent screen **In production** with the two scopes; no logo.
- Policy site https://mohitmishra786.github.io/kernelkafe-privacy/ (homepage, `privacy.html`,
  `terms.html`), repo `mohitmishra786/kernelkafe-privacy`.
- Desktop client `yt-studio`; token authorised for Kernel Kafe (@kernelkafe), channel id
  `UCOOCHObiwKlOrcNigGQC5AQ`. Channel phone-verified (custom thumbnails allowed).
- Audit form submitted 2026-10-03. The 7 uploads scheduled for 3–9 Oct showed **Scheduled**
  (not locked) in Studio right after upload.
- The evidence diagrams submitted are in `assets/diagrams/`.
