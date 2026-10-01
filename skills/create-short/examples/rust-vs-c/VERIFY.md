# Example: verifying a Short's claim before scripting ("C compiles this bug. Rust refuses.")

The script for this Short (`outline.json`) was written **after** running both programs. Its
lines quote what actually happened, including the gcc warning a sharp viewer would bring up.

## C: `uaf.c` on real glibc (Debian bookworm, gcc 12.2, glibc 2.36)

```bash
docker run --rm -v "$PWD":/w -w /w debian:bookworm-slim sh -c \
  "apt-get -qq update >/dev/null && apt-get -qq install -y gcc libc6-dev >/dev/null 2>&1 \
   && gcc -o uaf uaf.c && ./uaf; echo exit=\$?; gcc -Wall -o uaf2 uaf.c; echo build_exit=\$?"
```

Output (verbatim):

```
-1431448581
exit=0
uaf.c: In function 'main':
uaf.c:8:5: warning: pointer 'p' used after 'free' [-Wuse-after-free]
    8 |     printf("%d\n", *p);
      |     ^~~~~~~~~~~~~~~~~~
uaf.c:7:5: note: call to 'free' here
build_exit=0
```

What the script says because of this:
- "It compiles, runs, and prints garbage": it printed `-1431448581`, not 42.
- "GCC can warn about it, but it still builds": `-Wall` warns, and the exit status is 0.

On macOS the result differs (a different allocator), which is why glibc was tested in a
container.

## Rust: `uaf.rs` (rustc 1.94.1)

```bash
rustc uaf.rs
```

```
error[E0505]: cannot move out of `data` because it is borrowed
 --> uaf.rs:4:10
  |
2 |     let data = String::from("heap bytes");
  |         ---- binding `data` declared here
3 |     let view = &data;
  |                ----- borrow of `data` occurs here
4 |     drop(data);
  |          ^^^^ move out of `data` occurs here
5 |     println!("{view}");
  |                ---- borrow later used here
  |
help: consider cloning the value if the performance cost is acceptable
  |
3 |     let view = &data.clone();
  |                     ++++++++

error: aborting due to 1 previous error

For more information about this error, try `rustc --explain E0505`.
```

## Files

- `uaf.c`, `uaf.rs`: the programs shown on screen
- `outline.json`, `anchors.json`: the script and beats
- `publish-short.md`: the filled publish kit, with the pinned comment noting the garbage
  value varies

This Short's composition was built before the focus-stack layout existed, so use
`../kernel-stack/build.py` as the composition reference.
