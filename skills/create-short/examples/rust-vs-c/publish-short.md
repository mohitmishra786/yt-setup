# Short — publish kit

**File:** `final.mp4` (40.6s, 1080×1920) · **Category:** Education · **Not made for kids**
**Related video:** How malloc and free Really Work (the memory-allocators video; it explains
what free() actually does)

## Title

**Use:** C compiles this bug. Rust refuses. #shorts

Alternate: Same memory bug: C runs it, Rust won't build it #shorts

## Description

```
The same use-after-free in C and Rust. gcc 12 builds the C version (with -Wall it only warns) and it printed -1431448581 instead of 42. rustc 1.94 refuses to compile the Rust version: error[E0505], cannot move out of `data` because it is borrowed.

What free() really does: <FULL VIDEO LINK>

#rust #cprogramming #memorysafety
```

## Tags

```
rust, rust vs c, c programming, memory safety, use after free, borrow checker, dangling pointer, rustc, gcc, undefined behavior, systems programming, kernelkafe
```

## When to post

**Sun 4 Oct, 19:30 IST** (10:00 ET / 07:00 PT). That's day 6 of the allocators schedule, a
slot left open on purpose. It sits between Short 3 (Sat) and Short 4 (Mon) and points
viewers back to the long video.

## Pinned comment

```
Both outputs are real: gcc 12.2 on glibc 2.36 printed -1431448581 (your garbage value will differ; it's undefined behavior), and rustc 1.94.1 rejected the Rust version with E0505. Have you ever shipped a use-after-free?
```
