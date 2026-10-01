"""Scene kit for HyperFrames compositions in the house style (minimal, flat, one accent).

Branding (wordmark, handle, tagline, accent) comes from the `channel:` section of the repo's
config.yaml (falls back to config.yaml.example), so the same kit works for any channel.

Import from a project's composition/build.py:

    import sys; sys.path.insert(0, "<repo>/skills/create-video/assets")
    from scenekit import Scene, K, set_layout, title_card, outro, write_index

Every beat is timed as `CUE.<id> + offset` from cues.json (resolved from anchors.json by
`cli.py cues`), so visuals land on the spoken word. Position moves are converted to transforms
(x/y) automatically; arrows are invisible until drawn; notes + captions give every frame text.
"""

# ruff: noqa: N802, N806  (W/H/T read as canvas constants)
from __future__ import annotations

import html
import json
import math
import re
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def load_channel() -> dict:
    """The `channel:` block of config.yaml (or config.yaml.example), with safe defaults."""
    ch = {"name": "YourChannel", "wordmark": ["Your", "Channel"], "handle": "@yourchannel",
          "url": "", "tagline": "Subscribe for more deep dives", "accent": "#5aa9f0",
          "timezone": "UTC", "post_time": "14:00"}
    for cfg in (REPO / "config.yaml", REPO / "config.yaml.example"):
        if cfg.exists():
            try:
                import yaml

                data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
            except Exception:  # noqa: BLE001 — branding must never break a build
                continue
            if isinstance(data.get("channel"), dict):
                ch.update(data["channel"])
                break
    return ch


def _fill(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


CH = load_channel()

K = {
    "bg": "#121417", "surface": "#1c1f24", "surface2": "#252930", "line": "#3a3f48",
    "ink": "#e9eaec", "ink2": "#9aa0a8", "ink3": "#5d636c",
    "accent": CH["accent"], "accentFill": _fill(CH["accent"], 0.14),
    "bad": "#e5645c", "badFill": "rgba(229,100,92,0.14)",
}
EASE = "power2.inOut"
CHANNEL = tuple(CH["wordmark"]) or (CH["name"],)
HANDLE = CH["handle"]
TAGLINE = CH["tagline"]

LAYOUTS = {
    # kick: optional section label; note: explanatory line; area: where the focus stack
    # centers content (between the note and the captions)
    "landscape": {"W": 1920, "H": 1080, "kick": (120, 52, 28), "note": (120, 64, 46, None),
                  "area": (170, 910), "cap_top": 950, "cap_size": 44, "cap_words": 7,
                  "cap_side": 0},
    "portrait": {"W": 1080, "H": 1920, "kick": (90, 236, 30), "note": (90, 250, 50, 900),
                 "area": (420, 1350), "cap_top": 1410, "cap_size": 60, "cap_words": 4,
                 "cap_side": 90},
}

# Background: neutral charcoal, a soft centre lift and a faint dot grid. No colour, no glow.
BG_CSS = (f"background:radial-gradient(ellipse 85% 60% at 50% 46%, #1a1d22 0%, {K['bg']} 72%);")
DOTS_CSS = ("position:absolute; inset:0; pointer-events:none; opacity:0.55; "
            "background-image:radial-gradient(rgba(255,255,255,0.07) 1.3px, transparent 1.7px); "
            "background-size:36px 36px;")
L = dict(LAYOUTS["landscape"])


def set_layout(name: str) -> dict:
    L.clear()
    L.update(LAYOUTS[name])
    L["name"] = name
    return L


def caption_word(word: str) -> str:
    """Scripts spell some names phonetically for the voice; captions show the real names."""
    for spoken, shown in (("G-lib-C", "glibc"), ("J-E-malloc", "jemalloc"), ("G-C-C", "GCC"),
                          ("G-S", "GS")):
        word = word.replace(spoken, shown)
    return re.sub(r"[Mm]ee-malloc", "mimalloc", word)


class Scene:
    def __init__(self, n: int, cues: dict, fade_in: bool = True) -> None:
        self.n = n
        self.sid = f"scene-{n:02d}"
        self.p = f"s{n}"
        self.cues = {k: v["t"] for k, v in cues.items() if v["slide"] == n}
        self.html: list[str] = []
        self.js: list[str] = []
        self.fade_in = fade_in
        self.geom: dict[str, tuple[float, float]] = {}

    # ---- time -------------------------------------------------------------------------
    def T(self, cue: str | float, off: float = 0.0) -> str:
        if isinstance(cue, (int, float)):
            return f"{cue + off:.3f}"
        if cue not in self.cues:
            raise KeyError(f"{self.sid}: unknown cue {cue!r}")
        return f"CUE.{cue}+{off:.3f}" if off >= 0 else f"CUE.{cue}-{-off:.3f}"

    def i(self, name: str) -> str:
        return f"{self.p}-{name}"

    # ---- elements ---------------------------------------------------------------------
    def box(self, name, x, y, w, h, text="", *, kind="used", size=36, hidden=True,
            mono=False, weight=600, color=None, extra=""):
        fill, border, style = {
            "used": (K["surface2"], K["line"], "solid"),
            "empty": ("transparent", K["line"], "solid"),
            "free": ("transparent", K["ink3"], "dashed"),
            "live": (K["accentFill"], K["accent"], "solid"),
            "bad": (K["badFill"], K["bad"], "solid"),
            "panel": (K["surface"], K["line"], "solid"),
        }[kind]
        self.geom[name] = (x, y)
        fam = "var(--mono)" if mono else "var(--font)"
        self.html.append(
            f'<div id="{self.i(name)}" class="bx" style="left:{x}px;top:{y}px;width:{w}px;'
            f'height:{h}px;background:{fill};border:3px {style} {border};font-size:{size}px;'
            f'font-family:{fam};font-weight:{weight};color:{color or K["ink"]};'
            f'opacity:{0 if hidden else 1};{extra}">{text}</div>'
        )

    def text(self, name, x, y, text, *, size=38, color=None, mono=False, weight=600,
             hidden=True, w=None, align="left", wrap=False):
        self.geom[name] = (x, y)
        fam = "var(--mono)" if mono else "var(--font)"
        width = f"width:{w}px;" if w else ""
        ws = "white-space:normal;" if wrap else ""
        self.html.append(
            f'<div id="{self.i(name)}" class="tx" style="left:{x}px;top:{y}px;{width}{ws}'
            f'font-size:{size}px;font-family:{fam};font-weight:{weight};text-align:{align};'
            f'color:{color or K["ink"]};opacity:{0 if hidden else 1}">{text}</div>'
        )

    def panel(self, name, x, y, w, h, lines, *, size=34, lh=None, color=None, visible=None):
        """Code / terminal panel; each line is its own element `<name>-l<k>`."""
        lh = lh or round(size * 1.55)
        visible = set(range(len(lines))) if visible is None else set(visible)
        body = "".join(
            f'<div id="{self.i(f"{name}-l{k}")}" class="ln" '
            f'style="opacity:{1 if k in visible else 0}">'
            f'{html.escape(line) if line else "&nbsp;"}</div>' for k, line in enumerate(lines)
        )
        self.geom[name] = (x, y)
        self.html.append(
            f'<div id="{self.i(name)}" class="bx" style="left:{x}px;top:{y}px;width:{w}px;'
            f'height:{h}px;background:{K["surface"]};border:3px solid {K["line"]};opacity:0;'
            f'display:block;text-align:left;padding:24px 26px;font-family:var(--mono);'
            f'font-size:{size}px;line-height:{lh}px;color:{color or K["ink"]};white-space:pre">'
            f"{body}</div>"
        )

    def arrow(self, name, pts, *, color=None, head=True):
        color = color or K["ink2"]
        d = "M " + " L ".join(f"{x} {y}" for x, y in pts)
        length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:], strict=False))
        self.html.append(
            f'<svg class="wire" viewBox="0 0 {L["W"]} {L["H"]}">'
            f'<path id="{self.i(name)}" d="{d}" '
            f'fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" '
            f'stroke-linejoin="round" style="opacity:0;stroke-dasharray:{length:.1f};'
            f'stroke-dashoffset:{length:.1f}"/>'
            + (self._head(name, pts[-2], pts[-1], color) if head else "") + "</svg>"
        )

    def _head(self, name, a, b, color):
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        s = 16
        p1 = (b[0] - s * math.cos(ang - 0.45), b[1] - s * math.sin(ang - 0.45))
        p2 = (b[0] - s * math.cos(ang + 0.45), b[1] - s * math.sin(ang + 0.45))
        return (f'<polygon id="{self.i(name)}-h" points="{b[0]},{b[1]} {p1[0]:.1f},{p1[1]:.1f} '
                f'{p2[0]:.1f},{p2[1]:.1f}" fill="{color}" style="opacity:0"/>')

    def raw(self, markup: str):
        self.html.append(markup)

    @contextmanager
    def group(self, name, x, y, w, h, hidden=True):
        """`with s.group("g", x, y, w, h):` — children use coordinates relative to (x, y)
        and the whole group moves/dims as one element."""
        outer, self.html = self.html, []
        try:
            yield
        finally:
            inner = "".join(self.html)
            self.html = outer
            self.geom[name] = (x, y)
            self.html.append(
                f'<div id="{self.i(name)}" style="position:absolute;left:{x}px;top:{y}px;'
                f'width:{w}px;height:{h}px;opacity:{0 if hidden else 1}">{inner}</div>')

    # ---- focus stack --------------------------------------------------------------------
    def focus(self, heights: list[float], gap: float = 56) -> Focus:
        """Plan a focus stack: item k enters centred in the content area; earlier items slide
        up to make room and dim, so the thing being talked about is always centre-stage."""
        return Focus(self, heights, gap)

    # ---- motion -----------------------------------------------------------------------
    def sel(self, names):
        names = [names] if isinstance(names, str) else names
        return ",".join(f"#{self.i(n)}" for n in names)

    def to(self, names, at, off=0.0, dur=0.5, ease=EASE, stagger=None, **props):
        for css, axis, k in (("left", "x", 0), ("top", "y", 1)):
            if css in props:
                assert isinstance(names, str), "position moves take one element"
                props[axis] = props.pop(css) - self.geom[names][k]
        props["duration"] = dur
        props["ease"] = ease
        if stagger is not None:
            props["stagger"] = stagger
        body = ",".join(f"{k}:{json.dumps(v)}" for k, v in props.items())
        self.js.append(f'tl.to("{self.sel(names)}",{{{body}}},{self.T(at, off)});')

    def set(self, names, at, off=0.0, **props):
        body = ",".join(f"{k}:{json.dumps(v)}" for k, v in props.items())
        self.js.append(f'tl.set("{self.sel(names)}",{{{body}}},{self.T(at, off)});')

    def show(self, names, at, off=0.0, dur=0.5, stagger=None):
        self.to(names, at, off, dur, ease="power2.out", stagger=stagger, opacity=1)

    def hide(self, names, at, off=0.0, dur=0.4):
        self.to(names, at, off, dur, opacity=0)

    def draw(self, name, at, off=0.0, dur=0.7):
        self.set(name, at, off, opacity=1)
        self.to(name, at, off, dur, ease="power2.inOut", strokeDashoffset=0)
        if f'id="{self.i(name)}-h"' in "".join(self.html):
            self.js.append(f'tl.to("#{self.i(name)}-h",{{opacity:1,duration:0.15}},'
                           f'{self.T(at, off + dur - 0.1)});')

    def undraw(self, name, at, off=0.0, dur=0.3):
        self.hide([name, f"{name}-h"], at, off, dur)

    def state(self, names, kind, at, off=0.0, dur=0.4):
        fill, border, style = {
            "used": (K["surface2"], K["line"], "solid"),
            "free": ("rgba(0,0,0,0)", K["ink3"], "dashed"),
            "live": (K["accentFill"], K["accent"], "solid"),
            "livefree": ("rgba(0,0,0,0)", K["accent"], "dashed"),
            "bad": (K["badFill"], K["bad"], "solid"),
            "empty": ("rgba(0,0,0,0)", K["line"], "solid"),
            "panel": (K["surface"], K["line"], "solid"),
        }[kind]
        self.set(names, at, off, borderStyle=style)
        self.to(names, at, off, dur, backgroundColor=fill, borderColor=border)

    def line_mark(self, panel, k, kind, at, off=0.0):
        """Highlight line k of a panel: 'live' (accent), 'bad', or 'none'."""
        bg = {"live": K["accentFill"], "bad": K["badFill"], "none": "rgba(0,0,0,0)"}[kind]
        self.to(f"{panel}-l{k}", at, off, 0.3, backgroundColor=bg)

    # ---- text layer -------------------------------------------------------------------
    def add_notes(self, kicker: str | None, notes: list[tuple[str | float, str]]) -> None:
        """One explanatory line per beat at the top. `kicker` (a section label) is optional
        and off by default — it tends to be clutter; chapters carry that information."""
        nx, ny, ns, nw = L["note"]

        def at_s(at: str | float) -> float:
            return float(at) if isinstance(at, (int, float)) else self.cues[at]

        # a note that would be replaced within 1.2s is a flash: let the next one take its slot
        kept: list[tuple[str | float, str]] = []
        for k, (at, line) in enumerate(notes):
            nxt = notes[k + 1][0] if k + 1 < len(notes) else None
            if nxt is not None and at_s(nxt) - at_s(at) < 1.2:
                continue
            kept.append((at, line))
        if kept and notes and at_s(kept[0][0]) > at_s(notes[0][0]):
            kept[0] = (notes[0][0], kept[0][1])  # first surviving note shows from the start
        notes = kept
        if kicker:
            kx, ky, ks = L["kick"]
            self.text("kick", kx, ky, html.escape(kicker.upper()), size=ks, color=K["ink2"],
                      weight=700, hidden=False)
            self.html[-1] = self.html[-1].replace('class="tx"', 'class="tx" data-kicker="1"')
            ny += ks + 24
        for k, (_, line) in enumerate(notes):
            self.text(f"n{k}", nx, ny, html.escape(line), size=ns, weight=600, w=nw, wrap=bool(nw))
        for k, (at, _) in enumerate(notes):
            if k:
                self.hide(f"n{k-1}", at, -0.2, 0.18)
                self.show(f"n{k}", at, 0.0, 0.3)
            else:
                self.show("n0", at, 0.0, 0.3)

    def add_captions(self, words: list[dict]) -> None:
        chunks: list[list[dict]] = []
        cur: list[dict] = []
        for k, w in enumerate(words):
            cur.append(w)
            nxt = words[k + 1] if k + 1 < len(words) else None
            gap = nxt["start"] - w["end"] if nxt else 9.0
            if (nxt is None or len(cur) >= L["cap_words"] or gap > 0.35
                    or re.search(r"[.?!]$", w["text"])
                    or (re.search(r"[,:;]$", w["text"]) and len(cur) >= 2)):
                chunks.append(cur)
                cur = []
        for c, chunk in enumerate(chunks):
            spans = " ".join(
                f'<span id="{self.i(f"cw{c}_{j}")}" style="opacity:0.45">'
                f'{html.escape(caption_word(w["text"]))}</span>' for j, w in enumerate(chunk))
            self.raw(f'<div id="{self.i(f"cap{c}")}" class="cap" style="opacity:0">{spans}</div>')
            start = max(0.0, chunk[0]["start"] - 0.08)
            end = chunk[-1]["end"] + 0.35
            if c + 1 < len(chunks):
                end = min(end, chunks[c + 1][0]["start"] - 0.09)
            self.set(f"cap{c}", start, opacity=1)
            self.set(f"cap{c}", end, opacity=0)
            for j, w in enumerate(chunk):
                self.set(f"cw{c}_{j}", max(0.0, w["start"] - 0.02), opacity=1)

    # ---- output -----------------------------------------------------------------------
    def render(self, duration: float) -> str:
        W, H = L["W"], L["H"]
        side = L["cap_side"]
        intro = (f'tl.fromTo("#{self.i("wrap")}",{{opacity:0}},{{opacity:1,duration:0.3,'
                 f'ease:"power2.out"}},0);' if self.fade_in else "")
        wrap = f"#{self.i('wrap')}"
        return f"""<!doctype html>
<html><head><meta charset="UTF-8"><title>{self.sid}</title></head>
<body><template>
<style>
#root {{ position:absolute; inset:0; {BG_CSS} overflow:hidden; }}
#root .dots {{ {DOTS_CSS} }}
{wrap} {{ position:absolute; inset:0; }}
{wrap} .bx {{ position:absolute; box-sizing:border-box; border-radius:10px; display:flex;
  align-items:center; justify-content:center; text-align:center; line-height:1.1; }}
{wrap} .tx {{ position:absolute; line-height:1.2; white-space:nowrap; }}
{wrap} .tx[data-kicker] {{ letter-spacing:0.14em; }}
{wrap} .ln {{ border-radius:6px; padding:0 8px; margin:0 -8px; }}
{wrap} .cap {{ position:absolute; left:{side}px; top:{L["cap_top"]}px; width:{W - 2 * side}px;
  text-align:center; font-family:var(--font); font-size:{L["cap_size"]}px; font-weight:800;
  color:{K["ink"]}; line-height:1.15; }}
{wrap} svg.wire {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px;
  overflow:visible; pointer-events:none; }}
</style>
<div id="root" data-composition-id="{self.sid}" data-width="{W}" data-height="{H}"
  data-duration="{duration:.3f}">
<div class="dots"></div>
<div id="{self.i("wrap")}">
{chr(10).join(self.html)}
</div>
</div>
<script>
(function () {{
  const CUE = {json.dumps(self.cues)};
  const tl = gsap.timeline({{ paused: true }});
  {intro}
  {chr(10).join("  " + j for j in self.js)}
  window.__timelines["{self.sid}"] = tl;
}})();
</script>
</template></body></html>
"""


class Focus:
    def __init__(self, scene: Scene, heights: list[float], gap: float) -> None:
        self.s, self.h, self.gap = scene, heights, gap
        top, bottom = L["area"]
        self.pos: list[list[float]] = []  # pos[k][i]: y of item i while item k is newest
        for k in range(len(heights)):
            total = sum(heights[: k + 1]) + gap * k
            y0 = max(top, min((top + bottom - total) / 2, bottom - total))
            ys, y = [], y0
            for i in range(k + 1):
                ys.append(round(y))
                y += heights[i] + gap
            self.pos.append(ys)

    def y(self, i: int) -> float:
        """Where to create item i: its position at the moment it enters."""
        return self.pos[i][i]

    def run(self, names: list[str], cues: list[str | float], dim: float = 0.45,
            keep: tuple[int, ...] = ()) -> None:
        """Enter item k at cues[k]; slide earlier items up and dim them (except `keep`)."""
        s = self.s
        for k, (name, at) in enumerate(zip(names, cues, strict=True)):
            if k:
                for i in range(k):
                    s.to(names[i], at, -0.1, 0.55, top=self.pos[k][i])
                    if i not in keep and i == k - 1:
                        s.to(names[i], at, -0.1, 0.4, opacity=dim)
            s.show(name, at, 0.2 if k else 0.0, 0.4)


def wordmark(scene: Scene) -> str:
    """Channel wordmark: all parts but the last in ink, the last + a cursor in the accent."""
    *head, last = CHANNEL
    return (f'{html.escape("".join(head))}<span style="color:{K["accent"]}">{html.escape(last)}'
            f'</span><span id="{scene.i("cur")}" style="color:{K["accent"]}">_</span>')


def title_card(cues, title: str, seconds: float, n: int = 0) -> Scene:
    """Silent channel wordmark + topic title."""
    s = Scene(n, cues)
    W, H = L["W"], L["H"]
    big = 150 if L.get("name") != "portrait" else 120
    y = H // 2 - 170
    s.text("wm", 0, y, wordmark(s), size=big, weight=800, w=W, align="center")
    s.text("title", 60, y + big + 60, html.escape(title), size=52 if big == 150 else 56,
           color=K["ink2"], w=W - 120, align="center", wrap=True)
    s.js.append(f'tl.fromTo("#{s.i("wm")}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.45,'
                f'ease:"power3.out"}},0.05);')
    s.show("title", 0.35, 0.0, 0.35)
    s.hide(["wm", "title"], seconds - 0.3, 0.0, 0.25)
    return s


def outro(cues, seconds: float, n: int = 99) -> Scene:
    s = Scene(n, cues)
    W, H = L["W"], L["H"]
    big = 120 if L.get("name") != "portrait" else 110
    y = H // 2 - 260 if L.get("name") == "portrait" else 250
    s.text("wm", 0, y, wordmark(s), size=big, weight=800, w=W, align="center")
    s.text("handle", 0, y + big + 60, HANDLE, size=48, color=K["ink2"], w=W, align="center")
    s.text("sub", 60, y + big + 150, html.escape(TAGLINE), size=46,
           w=W - 120, align="center", wrap=True)
    s.js.append(f'tl.fromTo("#{s.i("wm")}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.5,'
                f'ease:"power3.out"}},0.1);')
    s.show("handle", 0.4, 0.0, 0.35)
    s.show("sub", 0.7, 0.0, 0.35)
    return s


def write_index(here: Path, seq: list[tuple[Scene, float, int | None, float]], title: str) -> float:
    """seq: (scene, slot seconds, narration slide index or None, narration seconds)."""
    W, H = L["W"], L["H"]
    (here / "compositions").mkdir(exist_ok=True)
    hosts, audio, t = [], [], 0.0
    for scene, sd, n, dur in seq:
        (here / "compositions" / f"{scene.sid}.html").write_text(scene.render(sd))
        hosts.append(
            f'<div id="{scene.sid}" class="clip scene" data-composition-id="{scene.sid}" '
            f'data-composition-src="compositions/{scene.sid}.html" data-start="{t:.3f}" '
            f'data-duration="{sd:.3f}" data-track-index="0" data-width="{W}" '
            f'data-height="{H}"></div>')
        if n is not None:
            audio.append(
                f'<audio id="voice-{n:02d}" src="assets/voice/slide_{n:02d}.mp3" '
                f'data-start="{t:.3f}" '
                f'data-duration="{dur:.3f}" data-track-index="10" data-volume="1"></audio>')
        t += sd
    res = "portrait" if L.get("name") == "portrait" else "landscape"
    (here / "index.html").write_text(f"""<!doctype html>
<html lang="en" data-resolution="{res}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width={W}, height={H}">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="assets/house.css">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:{K["bg"]}; }}
#root {{ position:relative; width:100%; height:100%; overflow:hidden; background:{K["bg"]}; }}
.scene {{ position:absolute; inset:0; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="{W}" data-height="{H}"
  data-fps="30" data-duration="{t:.3f}">
{chr(10).join(hosts)}
{chr(10).join(audio)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
window.__timelines["main"] = tl;
</script>
</body>
</html>
""")
    return t
