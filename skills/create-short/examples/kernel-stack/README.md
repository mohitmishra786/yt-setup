# Example: "How Linux remembers its kernel stack pointer" (40.5s)

A complete, shipped Short. Use it as the reference for structure, sizing and timing.

| File | What it is |
|---|---|
| `outline.json` | The script: 4 slides, ~100 words, names spelled for the voice (`G-S`) |
| `seo.json` | Title / description / tags fed to `import-outline` |
| `anchors.json` | 14 beats, each tied to a spoken phrase (`cli.py cues` turns them into times) |
| `build.py` | The composition on the scene kit. **Byte-identical** to the one that rendered the Short |
| `publish-short.md` | The filled publish kit |

## Shape

| Scene | Narration (paced) | On screen |
|---|---|---|
| Title card | 1.8s | Wordmark + "How Linux remembers its kernel stack pointer" |
| 1 Hook | ~7s | `rsp → your stack` centred → slides up as `syscall → kernel mode` arrives → turns red on "refuses to use it" → dashed "kernel stack ?" |
| 2 Mechanism | ~8.6s | Real `entry_SYSCALL_64` (Linux 7.3) centred, lines lighting up → per-CPU card enters below |
| 3 Turn | ~5.5s | Per-CPU slot → thread A stack; real `__switch_to` line; pointer swings to thread B |
| 4 Why care | ~11.8s | 16 KiB stack (grows down) fills with frames → one too many hits the red guard page |
| Outro | 2.5s | Wordmark, handle, tagline |

## Verification behind it

All of this was read from the Linux source (`master`, 7.3-rc5) before scripting:
- `arch/x86/entry/entry_64.S`: `swapgs`; user `%rsp` → `cpu_tss_rw + TSS_sp2`; `movq PER_CPU_VAR(cpu_current_top_of_stack), %rsp`
- `arch/x86/kernel/process_64.c:671`: `raw_cpu_write(cpu_current_top_of_stack, task_top_of_stack(next_p));`
- `arch/x86/include/asm/page_64_types.h`: `THREAD_SIZE = PAGE_SIZE << (2 + KASAN_STACK_ORDER)` → 16 KiB, or 32 KiB with KASAN
- `arch/Kconfig`: `VMAP_STACK` (default y) uses guard pages, so overflows are "caught immediately"

## What went wrong first (and the rule it became)

- "The kernel **can't** trust it" was heard as "can trust it" → reworded to "refuses to use
  it" (avoid flippable words).
- "recursion" came out as "percussion" → changed the sentence slightly for a fresh take
  (identical text reproduces the identical take).
- The first stack diagram grew upward → x86 stacks grow **down**; the guard page goes below.
- A note replaced 0.7s after the scene start showed as a ghost → the kit now drops notes
  shorter than 1.2s.
- 30px code was too small on a phone → 34px with lines broken at commas.

## Reuse

Copy `build.py` into `projects/<new-id>/composition/` (or start from `templates/build.py`),
keep the helpers and constants, and replace the scene functions, `NOTES` and `TITLE`. Scene N
must be outline slide N, and cue ids must exist in that project's `cues.json`.
