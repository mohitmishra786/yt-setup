# Composing a Short (portrait) on the scene kit

The engine is shared: `skills/create-video/assets/scenekit.py` (it's found by walking up to
the repo root). This file is the portrait-specific workflow and the sizing recipes that
worked. The complete worked example is `examples/kernel-stack/build.py`.

## 0. Scaffold

```bash
.venv/bin/python cli.py cues --project <id>                         # anchors.json -> cues.json
.venv/bin/python skills/create-short/scripts/scaffold.py projects/<id>
cd projects/<id>/composition && ../../../.venv/bin/python build.py   # rough cut builds immediately
```

`scaffold.py` runs HyperFrames init (portrait) and copies `house.css` and the narration in.
It writes `build.py` from `templates/build.py`, where every slide starts as a placeholder card
showing its `visual_beat`. Replace scenes one at a time and register each in `SCENES`.
Re-run `scaffold.py` after regenerating the voice; it refreshes the audio and never touches
`build.py`.

## 1. Plan each scene as a focus stack

List what appears, in order, and give each item a height. The kit centres the group in the
content area (y 420–1350, a 930px band). Keep the total stack, including 56px gaps, **under
~900px**.

```python
f = s.focus([290, 190])            # heights of item 0, item 1 (top to bottom)
...create item k at y = f.y(k)...
f.run(["code", "term"], [0.05, "s1_compiles"], keep=(0,))
```

- `run` shows item 0 at its cue and, at each later cue, slides earlier items up and dims the
  previous one.
- `keep=(i,)` keeps item *i* bright when it's still being referenced (code whose lines keep
  lighting up).
- Item 0 should usually appear at **0.05s**, so the scene is never empty.
- To move a multi-part diagram as one unit, wrap it in `with s.group("name", X, f.y(k), PW, h):`.
  Children then use coordinates relative to the group.

## 2. Sizing recipes (portrait, content column x = 90, width 900)

| Thing | Recipe |
|---|---|
| Code panel | `s.panel(name, X, y, PW, h, lines, size=34, lh=52)` with `h = 48 + 52 × lines` (4 lines → 256; 7 → 412). First line is the source comment; colour it `ink2` with `s.set(f"{name}-l0", 0.0, color=K["ink2"])` |
| Terminal / output | Same panel. `visible=[0]` shows only the prompt, then `s.show(f"{name}-l1", cue)` as each line "prints" |
| Long code line | ≤ ~41 characters at 34px. Break at a comma or paren: `movq %rsp,` / `  PER_CPU_VAR(…)` |
| Register / variable card | `s.box(name, x, y, 230–250, 140–150, "rsp", kind="live", size=56–64, mono=True, weight=700)` |
| Labelled block | `s.box(name, x, y, w, 100–160, "label", size=36–48)`; add a 32–36px `ink2` caption 12px below |
| Two side-by-side boxes | widths 420 + 60 gap + 420 (x = 0 and 480 inside a group) |
| Full-width band | `s.box(name, X, y, PW, 110–120, "syscall → kernel mode", kind="panel", mono=True, size=44–46)` |
| Arrow between boxes | `s.arrow(name, [(x1 + 8, y), (x2 - 8, y)], color=K["accent"])`; `s.draw(name, cue, off, 0.4)` |
| A tall diagram alone | One focus item of 560–640 px (e.g. the stack + guard page) |

States: `s.state(name, "live" | "bad" | "free" | "livefree" | "used", cue, off)`. Code lines:
`s.line_mark(panel, k, "live" | "bad" | "none", cue, off)`. Swing a pointer: `s.undraw(a, cue)`
then `s.draw(b, cue, 0.15)`.

## 3. Notes, captions, branding

```python
NOTES[2] = [(0.0, "entry_SYSCALL_64: the syscall entry point"),
            ("s2_stash", "Your rsp is parked in a per-CPU slot")]
scene.add_notes(None, NOTES[2])     # None = no section label (house rule)
scene.add_captions(words[2])        # from audio/words.json
```

- **Notes:** ≤ 2 lines at 50px (~40 characters per line). A note replaced within 1.2s is
  dropped automatically. If the narration hits the first beat within ~1s of the scene start,
  start the scene with that note instead.
- **Branding:** `title_card(cues, TITLE, 1.8)` first and `outro(cues, 2.5)` last. They read
  the `channel:` section of `config.yaml`. The template already wires both.

## 4. Review loop (don't skip)

```bash
../../../.venv/bin/python build.py && npx hyperframes lint
npx hyperframes snapshot --timeout 60000 --no-end \
  --at $(../../../.venv/bin/python ../../../skills/create-short/scripts/verify_short.py .. --times)
npx hyperframes check          # 0 errors; fix warnings too (contrast, overlapping tweens)
```

Look at every snapshot and ask:

1. Is the thing being talked about **centred**? Is there dead space top or bottom?
2. Does each beat show what its word names, about 0.9s after the word?
3. Is any text smaller than the minimums, or using `ink3`?
4. Is red only on the thing that's wrong?
5. Does the diagram match reality (direction, order, sizes)?

Common fixes, all from real Shorts:

| Symptom | Fix |
|---|---|
| A ghost note at a scene start | Drop or merge that note (it was replaced within ~1s) |
| `overlapping_gsap_tweens` | Two tweens on one element overlap in time; move one or merge them |
| Contrast warning on a comment line | Use `ink2`, not `ink3` |
| Code too small on a phone | 34px and break the lines; increase the panel height in the focus list |
| Element collides with the note | Increase the focus heights/gap total or drop an item; the stack must stay under ~900px |

## 5. Render

`poster.json` → `{"time": 0.9}` (title card, cursor visible). Then:

```bash
.venv/bin/python cli.py run --project <id> --only hyperframes
.venv/bin/python skills/create-short/scripts/verify_short.py projects/<id>    # gate + contact sheet
```
