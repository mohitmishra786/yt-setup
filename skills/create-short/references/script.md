# Writing a Short script

A Short lives or dies on its first sentence and on being **true**. Write the script, verify
every claim, then let the voice and visuals follow.

## 1. Pick the one mechanism

Answer these before writing:
1. What single mechanism does the viewer watch happen?
2. What's the surprising, concrete hook: a crash, a wrong answer, a "wait, what?"
3. What **real** artifact proves it: code and its output, a source excerpt, a measured
   number?
4. What's the one-line payoff the viewer repeats to a friend?

If you can't answer #3, find the artifact first. Shorts without real material feel generic.

## 2. Shape: 3–5 slides, one narration unit each

| Slide | Job | Example that shipped |
|---|---|---|
| 1. Hook | The surprising fact, ending on a question or a twist | "This C program frees memory, then reads it anyway. It compiles, runs, and prints garbage." |
| 2. Mechanism | What actually happens, shown step by step | "The entry code swaps G-S, stashes your stack pointer in a per-CPU slot, and loads the kernel's from another per-CPU variable: current top of stack." |
| 3. Contrast / turn | The other side, the fix, or the "and here's the clever part" | "Now the same bug in Rust. … The compiler refuses to build it." |
| 4. Why it matters / payoff | The consequence, concrete, then the takeaway | "Same mistake. C lets it reach runtime. Rust stops it before the code ever runs." |

## 3. Word budget

The cloned voice runs ~3 words/s before pacing. For a 45s Short:

| Part | Time |
|---|---|
| Title card | 1.8s |
| Narration after `pace --gap 0.3` | ~33–36s → **95–105 words** |
| Scene gaps + last hold + outro | ~5.5s |

30s ≈ 60–70 words. 60s ≈ 140–150 words. After `voice`, the narration total is the truth; if
it misses by more than ~10%, rewrite and regenerate (only changed slides regenerate).

## 4. Write for the ear

- **Spell names how they're spoken:** `G-C-C`, `G-S`, `G-lib-C`, `J-E-malloc`, `mee-malloc`.
  Captions map them back (`caption_word()` in scenekit; add new ones there).
- **Avoid flippable words.** "can't" is often heard as "can" (and Chatterbox may swallow the
  "t"). Prefer "refuses to", "won't", "never". Watch near-homophones: program/problem,
  recursion/percussion.
- **Numbers as words:** "sixteen kilobytes", not "16 KiB" (captions show what you wrote;
  notes can use "16 KiB").
- Short sentences. One idea each. No parentheses, no code syntax in `speaker_notes`.

## 5. Verify, then show the proof

- **Code:** compile and run it, in the right environment. glibc and gcc behaviour → a Debian
  container:
  ```bash
  docker run --rm -v "$PWD":/w -w /w debian:bookworm-slim sh -c \
    "apt-get -qq update >/dev/null && apt-get -qq install -y gcc libc6-dev >/dev/null 2>&1 \
     && gcc -Wall uaf.c -o uaf && ./uaf"
  ```
  Keep the exact output, warnings included. A sharp viewer will mention `-Wall` if you hide
  it. Then build the script's claim around what really happened.
- **Kernel or library claims:** read the current source (e.g.
  `curl -sL https://raw.githubusercontent.com/torvalds/linux/master/<path>`) and quote it
  verbatim, with the version, in the code panel's first line.
- **Numbers:** trace them to a definition (`THREAD_SIZE = PAGE_SIZE << (2 + KASAN_STACK_ORDER)`
  → 16 KiB, or 32 KiB with KASAN). Put any caveat in the pinned comment.
- Keep the artifacts (`uaf.c`, `uaf.rs`, the source excerpts) in the project folder. See
  `examples/rust-vs-c/VERIFY.md`.

## 6. outline.json

```json
{
  "title": "<full topic title>",
  "target_duration_minutes": 1.0,
  "audience": "<who>",
  "slides": [
    {"index": 1, "title": "<beat name>",
     "speaker_notes": "<exact words to speak>",
     "visual_beat": "<what the viewer watches happen>"}
  ]
}
```

Plus `seo.json` (`title` ≤ 100 characters ending in `#shorts`, `description`, `tags`,
`hashtags`, `thumbnail_text`, `hook_line`). See `examples/kernel-stack/` for a complete
pair.
