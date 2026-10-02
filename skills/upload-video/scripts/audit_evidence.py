"""Evidence images for the YouTube API Services audit form (references/setup.md, part 5).

Writes 1600px-wide PNGs (the form wants at least 1280x720) into an output folder:

- architecture-diagram.png  → Section 6 "Architecture diagram"
- user-flow-diagram.png     → Section 6 "User flow diagrams"
- upload-interface-cli.png  → Section 6 "Other supporting materials", and part of the
  conditional "upload interface" evidence. Real output of `cli.py youtube-auth`,
  `upload --dry-run` and `upload --verify` for a project you already uploaded, so it
  needs --project and a working login.

    .venv/bin/python skills/upload-video/scripts/audit_evidence.py \
        --out ~/Desktop/youtube-audit-evidence [--project <id>]

Channel name and handle come from config.yaml `channel:`. Screenshots of web pages (privacy
policy, homepage, terms, Google consent and revocation pages) must be taken by the creator
in a real browser with the address bar visible; this script can't fake those, and shouldn't.
"""

# ruff: noqa: E501  (embedded HTML/CSS reads better unwrapped)
from __future__ import annotations

import argparse
import glob
import html
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from core.config import load_config  # noqa: E402

CSS = """
*{box-sizing:border-box} body{margin:0;width:1600px;height:900px;background:#fff;
 font-family:-apple-system,Helvetica,Arial,sans-serif;color:#1f2328}
h1{font-size:34px;margin:36px 56px 6px} .sub{margin:0 56px 26px;color:#57606a;font-size:19px}
.box{position:absolute;border:3px solid #1f2328;border-radius:14px;padding:16px 20px;
 background:#f6f8fa} .box h2{margin:0 0 8px;font-size:23px}
.box p,.box li{margin:3px 0;font-size:17px;line-height:1.35} .box ul{margin:4px 0 0 18px;padding:0}
.yt{border-color:#c4302b;background:#fff5f5} .g{border-color:#1a73e8;background:#f2f7ff}
.arrow{position:absolute;font-size:17px;text-align:center} .line{position:absolute;background:#1f2328}
.note{position:absolute;left:56px;right:56px;bottom:28px;font-size:17px;color:#57606a;
 border-top:1px solid #d0d7de;padding-top:12px}
code{font-family:Menlo,monospace;font-size:15px;background:#eaeef2;padding:1px 4px;border-radius:4px}
.step{position:absolute;left:56px;width:1488px;height:78px;border:3px solid #1f2328;
 border-radius:12px;background:#f6f8fa;padding:10px 20px 10px 90px}
.step b.n{position:absolute;left:22px;top:14px;width:46px;height:46px;border-radius:50%;
 background:#1f2328;color:#fff;font-size:24px;text-align:center;line-height:46px}
.step h3{margin:0;font-size:21px} .step p{margin:4px 0 0;font-size:16px;color:#3d444d}
"""


def find_chrome() -> str:
    candidates = [
        os.getenv("CHROME_BIN", ""),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        *sorted(glob.glob(str(Path.home() / ".cache/hyperframes/chrome/**/chrome-headless-shell"),
                          recursive=True)),
        shutil.which("google-chrome") or "", shutil.which("chromium") or "",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    raise SystemExit("No Chrome found; set CHROME_BIN to a Chrome/Chromium binary.")


def shoot(chrome: str, doc: str, out: Path, height: int = 900) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as fh:
        fh.write(doc)
    subprocess.run([chrome, "--headless=new", "--hide-scrollbars", f"--screenshot={out}",
                    f"--window-size=1600,{height}", f"file://{fh.name}"],
                   check=True, capture_output=True)
    print(f"wrote {out}")


def architecture(app: str, channel: str, handle: str) -> str:
    e = html.escape
    return f"""<html><head><style>{CSS}</style></head><body>
<h1>{e(app)}: architecture</h1>
<div class=sub>Single-user command-line tool. Runs only on the channel owner's computer; there is
no server and no other user.</div>
<div class=box style="left:56px;top:150px;width:560px;height:560px">
<h2>Channel owner's computer</h2>
<p><b>yt-setup CLI</b> (open source): <code>cli.py youtube-auth</code>, <code>cli.py upload</code></p>
<ul><li>Reads the owner's finished files: videos, Shorts, thumbnail, caption file</li>
<li>Reads the upload plan <code>publish/upload.json</code> (titles, descriptions, tags,
publish times)</li>
<li>Validates everything locally before any API call (<code>--dry-run</code>)</li>
<li>Stores the OAuth token in <code>.credentials/youtube_token.json</code> (file mode 600,
never committed or shared)</li>
<li>Records own upload ids/status in <code>publish/uploaded.json</code> to resume and verify</li>
</ul></div>
<div class="box g" style="left:820px;top:150px;width:724px;height:150px">
<h2>Google OAuth 2.0 (accounts.google.com)</h2>
<p>Owner signs in once in their browser and grants exactly two scopes:</p>
<p><code>youtube.upload</code> · <code>youtube.force-ssl</code></p></div>
<div class="box yt" style="left:820px;top:350px;width:724px;height:250px">
<h2>YouTube Data API v3</h2>
<ul><li><code>videos.insert</code>: upload as private with <code>status.publishAt</code>
(YouTube publishes on schedule)</li>
<li><code>thumbnails.set</code>, <code>captions.insert</code>, <code>playlistItems.insert</code></li>
<li><code>videos.list</code>, <code>channels.list</code>, <code>playlists.list</code>: read back
own status</li></ul><p>A handful of uploads per week; default quota.</p></div>
<div class="box yt" style="left:820px;top:640px;width:724px;height:90px">
<h2>The owner's own channel: {e(channel)} ({e(handle)})</h2></div>
<div class=line style="left:616px;top:222px;width:204px;height:3px"></div>
<div class=arrow style="left:620px;top:186px;width:196px">HTTPS: sign-in, token ⇄</div>
<div class=line style="left:616px;top:470px;width:204px;height:3px"></div>
<div class=arrow style="left:620px;top:434px;width:196px">HTTPS API calls ⇄</div>
<div class=line style="left:1180px;top:600px;width:3px;height:40px"></div>
<div class=note>No other users, no hosting, no third parties. Data leaves the computer only to
Google/YouTube. Access can be revoked at any time at
security.google.com/settings/security/permissions; deleting the two local files removes all
stored data.</div></body></html>"""


def user_flow(app: str, handle: str) -> str:
    steps = [
        ("Finish the video locally",
         "The owner produces the long video and Shorts in the yt-setup project folder."),
        ("Sign in once: cli.py youtube-auth",
         "Browser opens Google's consent screen; owner grants youtube.upload + youtube.force-ssl;"
         f" the CLI confirms the signed-in channel is {handle}."),
        ("Write and review the plan: publish/upload.json",
         "Titles, descriptions, tags, thumbnail, captions, playlist and the publish time for each "
         "video."),
        ("Preview: cli.py upload --dry-run",
         "Validates lengths, files and times and prints a table. No API calls are made."),
        ("Owner confirms: cli.py upload",
         "Each video is uploaded as private with publishAt; then thumbnail, captions and playlist "
         "entry. Progress saved locally."),
        ("Check: cli.py upload --verify",
         "Reads back privacy, publish time and processing status of the owner's own uploads."),
        ("YouTube publishes on schedule",
         "At publishAt YouTube makes the video public. Nothing on the owner's computer has to run."),
        ("Revoke / delete any time",
         "Revoke at security.google.com/settings/security/permissions; delete the local token and "
         "upload records."),
    ]
    doc = (f"<html><head><style>{CSS}</style></head><body><h1>{html.escape(app)}: user flow</h1>"
           "<div class=sub>The only user is the channel owner. Every step runs on their computer; "
           "only steps 2, 5 and 6 call Google/YouTube.</div>")
    for k, (t, d) in enumerate(steps):
        doc += (f'<div class=step style="top:{128 + k * 94}px"><b class=n>{k + 1}</b>'
                f"<h3>{html.escape(t)}</h3><p>{html.escape(d)}</p></div>")
    return doc + "</body></html>"


def cli_output(app: str, project: str) -> tuple[str, int]:
    py = str(REPO / ".venv" / "bin" / "python")
    env = {**os.environ, "COLUMNS": "150"}
    parts = []
    for args in (["youtube-auth"], ["upload", "--project", project, "--dry-run"],
                 ["upload", "--project", project, "--verify"]):
        res = subprocess.run([py, "cli.py", *args], cwd=REPO, env=env, capture_output=True,
                             text=True)
        out = "\n".join(line for line in (res.stdout + res.stderr).splitlines()
                        if "pkg_resources" not in line and "resource_filename" not in line)
        parts.append(f"$ python cli.py {' '.join(args)}\n{out.strip()}\n")
    body = "\n".join(parts)
    height = 200 + body.count("\n") * 21 + 60
    doc = f"""<html><body style="margin:0;background:#fff;font-family:-apple-system,Helvetica,sans-serif">
<div style="margin:28px 40px 10px;font-size:26px;font-weight:700;color:#1f2328">{html.escape(app)}:
upload interface (real terminal output)</div>
<div style="margin:0 40px 16px;font-size:16px;color:#57606a">The tool has no web UI: it is a
command-line program. Sign-in check, the pre-upload review table (--dry-run) and the status
read-back (--verify) of the owner's scheduled uploads.</div>
<pre style="margin:0 40px 30px;background:#0d1117;color:#e6edf3;padding:22px 24px;border-radius:10px;
font:14px/21px Menlo,monospace;white-space:pre">{html.escape(body)}</pre></body></html>"""
    return doc, height


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--project", help="an already-uploaded project id, for the CLI evidence")
    a = ap.parse_args()
    cfg = load_config()
    channel, handle = cfg.channel.name, cfg.channel.handle
    app = f"{channel} Publisher"
    out = a.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()
    shoot(chrome, architecture(app, channel, handle), out / "architecture-diagram.png")
    shoot(chrome, user_flow(app, handle), out / "user-flow-diagram.png")
    if a.project:
        doc, height = cli_output(app, a.project)
        shoot(chrome, doc, out / "upload-interface-cli.png", height)


if __name__ == "__main__":
    main()
