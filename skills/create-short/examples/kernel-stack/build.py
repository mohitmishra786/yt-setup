"""How Linux remembers its kernel stack pointer — vertical Short (focus-stack layout).

WORKED EXAMPLE (skills/create-short/examples/kernel-stack). Copy patterns from here:
  scene1: a group (register card -> arrow -> stack) + two more items in a focus stack;
          `keep=(0,)` keeps the first item bright because it changes state later.
  scene2: a real-source code panel (34px, long lines broken) + a per-CPU card that enters
          below it; lines light up on their spoken words.
  scene3: a pointer that swings between two targets (undraw one arrow, draw the other).
  scene4: a single centred diagram that fills up and overflows into a red guard page.
To render it for real, run it from projects/<id>/composition with that project's audio/cues.

Beats come from ../cues.json (cli.py cues). Source excerpts are verbatim from Linux 7.3-rc5:
arch/x86/entry/entry_64.S (entry_SYSCALL_64), arch/x86/kernel/process_64.c:671 (__switch_to).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


def _kit_dir() -> Path:
    """The shared scene kit lives in the repo at skills/create-video/assets/."""
    for base in (HERE, *HERE.parents):
        kit = base / "skills" / "create-video" / "assets"
        if (kit / "scenekit.py").exists():
            return kit
    sys.exit("scenekit.py not found: this Short must live inside the yt-setup repo "
             "(projects/<id>/composition). https://github.com/mohitmishra786/yt-setup")


sys.path.insert(0, str(_kit_dir()))
from scenekit import K, Scene, outro, set_layout, title_card, write_index  # noqa: E402

set_layout("portrait")
TITLE = "How Linux remembers its kernel stack pointer"
PAD, TITLE_S, OUTRO_S = 0.6, 1.8, 2.5
X, PW = 90, 900

NOTES = {
    1: [(0.0, "Every syscall starts on your stack"),
        ("s1_trust", "That's user memory: the kernel can't trust it"),
        ("s1_where", "So where is the kernel's own stack?")],
    2: [(0.0, "entry_SYSCALL_64: the syscall entry point"),
        ("s2_swap", "swapgs: GS now points at this CPU's data"),
        ("s2_stash", "Your rsp is parked in a per-CPU slot"),
        ("s2_load", "rsp = this CPU's cpu_current_top_of_stack")],
    3: [(0.0, "__switch_to() rewrites it on every switch"),
        ("s3_right", "So it always points at the right stack")],
    4: [(0.0, "Why you should care"),
        ("s4_16", "Each thread gets only 16 KiB of kernel stack"),
        ("s4_recursion", "No deep recursion, no big local arrays"),
        ("s4_guard", "VMAP_STACK: a guard page catches the overflow")],
}


def scene1(cues):
    s = Scene(1, cues)
    f = s.focus([200, 120, 170])
    with s.group("user", X, f.y(0), PW, 200):
        s.box("rsp", 0, 0, 250, 150, "rsp", kind="live", size=60, mono=True, weight=700,
              hidden=False)
        s.arrow("a", [(258, 75), (452, 75)], color=K["accent"])
        s.box("ustack", 460, 0, 440, 150, "your stack", kind="used", size=48, hidden=False)
        s.text("ul", 460, 162, "user memory", size=34, color=K["ink2"], w=440, align="center",
               hidden=False)
    s.box("sys", X, f.y(1), PW, 120, "syscall  →  kernel mode", kind="panel", size=46,
          weight=700, mono=True)
    s.box("kq", X, f.y(2), PW, 170, "kernel stack ?", kind="free", size=54, weight=700,
          color=K["ink2"])
    s.draw("a", 0.25, 0.0, 0.4)
    f.run(["user", "sys", "kq"], [0.05, "s1_enter", "s1_where"], keep=(0,))
    s.state("ustack", "bad", "s1_trust", -0.05)
    s.state("rsp", "bad", "s1_trust", -0.05)
    s.to("a", "s1_trust", -0.05, 0.3, stroke=K["bad"])
    s.to("a-h", "s1_trust", -0.05, 0.3, fill=K["bad"])
    s.state("kq", "livefree", "s1_where", 0.6)
    return s


def scene2(cues):
    s = Scene(2, cues)
    f = s.focus([420, 300])
    lines = ["// entry_SYSCALL_64 · Linux 7.3", "swapgs",
             "movq %rsp,", "  PER_CPU_VAR(cpu_tss_rw + TSS_sp2)",
             "SWITCH_TO_KERNEL_CR3 scratch_reg=%rsp",
             "movq PER_CPU_VAR(", "  cpu_current_top_of_stack), %rsp"]
    s.panel("code", X, f.y(0), PW, 420, lines, size=34, lh=52)
    s.set("code-l0", 0.0, color=K["ink2"])
    with s.group("pcpu", X, f.y(1), PW, 300):
        s.text("t", 0, 0, "this CPU's per-CPU area", size=34, color=K["ink2"], hidden=False)
        s.box("slot1", 0, 60, 560, 100, "tss.sp2 (scratch)", kind="panel", size=32, mono=True,
              hidden=False)
        s.box("v1", 620, 60, 280, 100, "your rsp", kind="used", size=36, weight=700)
        s.box("slot2", 0, 190, 560, 100, "cpu_current_top_of_stack", kind="panel", size=30,
              mono=True)
        s.box("v2", 620, 190, 280, 100, "kernel rsp", kind="live", size=36, weight=700)
        s.arrow("a2", [(566, 240), (612, 240)], color=K["accent"])
    f.run(["code", "pcpu"], [0.05, "s2_stash"], keep=(0,))
    s.line_mark("code", 1, "live", "s2_swap", -0.05)
    s.line_mark("code", 1, "none", "s2_stash", -0.1)
    s.line_mark("code", 2, "live", "s2_stash", -0.05)
    s.line_mark("code", 3, "live", "s2_stash", -0.05)
    s.show("v1", "s2_stash", 0.5, 0.3)
    s.line_mark("code", 2, "none", "s2_load", -0.1)
    s.line_mark("code", 3, "none", "s2_load", -0.1)
    s.line_mark("code", 5, "live", "s2_load", -0.05)
    s.line_mark("code", 6, "live", "s2_load", -0.05)
    s.show("slot2", "s2_load", 0.1, 0.3)
    s.draw("a2", "s2_load", 0.4, 0.3)
    s.show("v2", "s2_load", 0.6, 0.3)
    return s


def scene3(cues):
    s = Scene(3, cues)
    f = s.focus([430, 210])
    with s.group("dia", X, f.y(0), PW, 430):
        s.box("slot", 0, 0, PW, 110, "cpu_current_top_of_stack", kind="panel", size=38,
              mono=True, hidden=False)
        s.box("ta", 0, 240, 420, 190, "thread A<br>kernel stack", kind="live", size=40,
              hidden=False)
        s.box("tb", 480, 240, 420, 190, "thread B<br>kernel stack", kind="used", size=40,
              hidden=False)
        s.arrow("pa", [(210, 118), (210, 232)], color=K["accent"])
        s.arrow("pb", [(690, 118), (690, 232)], color=K["accent"])
    s.panel("code", X, f.y(1), PW, 210, ["// __switch_to() · process_64.c",
                                         "raw_cpu_write(cpu_current_top_of_stack,",
                                         "      task_top_of_stack(next_p));"], size=34, lh=52)
    s.set("code-l0", 0.0, color=K["ink2"])
    s.draw("pa", 0.2, 0.0, 0.4)
    f.run(["dia", "code"], [0.05, "s3_switch"], keep=(0,))
    s.line_mark("code", 1, "live", "s3_switch", 0.4)
    s.line_mark("code", 2, "live", "s3_switch", 0.4)
    s.undraw("pa", "s3_next", 0.0)
    s.draw("pb", "s3_next", 0.15, 0.4)
    s.state("ta", "used", "s3_next", 0.1)
    s.state("tb", "live", "s3_next", 0.3)
    s.state("slot", "live", "s3_right", 0.0)
    return s


def scene4(cues):
    s = Scene(4, cues)
    f = s.focus([640])
    fh, fg = 58, 8
    with s.group("st", X, f.y(0), PW, 640):
        # x86 stacks grow down (toward lower addresses); the VMAP_STACK guard page sits below
        s.box("bar", 170, 0, 460, 510, "", kind="empty", hidden=False)
        s.box("guard", 170, 530, 460, 110, "", kind="free", hidden=False)
        s.text("kib", 660, 170, "16 KiB", size=58, weight=800)
        s.text("grow", 660, 250, "grows down ↓", size=32, color=K["ink2"])
        s.text("gl", 660, 562, "guard page", size=36, color=K["ink2"], hidden=False)
        for k in range(7):  # 7 frames fill the bar from the top down
            s.box(f"fr{k}", 180, 10 + k * (fh + fg), 440, fh, "", kind="used")
        s.box("ov0", 180, 556, 440, fh, "", kind="bad")  # the frame too many lands in the guard
    f.run(["st"], [0.05])
    s.show(["kib", "grow"], "s4_16", 0.0, 0.4)
    s.state("bar", "live", "s4_16", 0.0)
    s.state("bar", "empty", "s4_16", 1.4)
    s.show([f"fr{k}" for k in range(5)], "s4_recursion", 0.0, 0.2, stagger=0.18)
    s.show([f"fr{k}" for k in range(5, 7)], "s4_arrays", 0.0, 0.2, stagger=0.18)
    s.show("ov0", "s4_overflow", 0.1, 0.2)
    s.state("guard", "bad", "s4_overflow", 0.3)
    s.to("gl", "s4_overflow", 0.3, 0.3, color=K["bad"])
    return s


def main() -> None:
    cues = json.loads((PROJECT / "cues.json").read_text())
    durs = json.loads((PROJECT / "audio" / "durations.json").read_text())["durations"]
    words = {int(sl["index"]): sl["words"]
             for sl in json.loads((PROJECT / "audio" / "words.json").read_text())["slides"]}
    seq = [(title_card(cues, TITLE, TITLE_S), TITLE_S, None, 0.0)]
    for n, build in enumerate([scene1, scene2, scene3, scene4], start=1):
        sc = build(cues)
        sc.add_notes(None, NOTES[n])
        sc.add_captions(words[n])
        seq.append((sc, durs[n - 1] + PAD + (0.8 if n == 4 else 0.0), n, durs[n - 1]))
    seq.append((outro(cues, OUTRO_S), OUTRO_S, None, 0.0))
    total = write_index(HERE, seq, TITLE)
    print(f"built {len(seq)} scenes, total {total:.2f}s")


if __name__ == "__main__":
    main()
