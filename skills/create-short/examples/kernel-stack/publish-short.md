# Short — publish kit

**File:** `final.mp4` (40.5s, 1080×1920) · **Category:** Education · **Not made for kids**
**Related video:** How malloc and free Really Work (the channel's current long video; the
nearest topic). Switch it to a syscalls/kernel long video once one exists.

## Title

**Use:** How Linux finds its kernel stack on every syscall #shorts

Alternates:
- Where does the kernel's stack come from? #shorts
- How Linux remembers its kernel stack pointer #shorts

## Description

```
On every system call, the CPU arrives in the kernel with your stack pointer, and the kernel refuses to use it. entry_SYSCALL_64 runs swapgs, parks your rsp in a per-CPU slot, and loads cpu_current_top_of_stack. __switch_to() rewrites that variable on every context switch. And the stack it points at is only 16 KiB per thread, with a guard page (VMAP_STACK) to catch overflows.

Source shown is from Linux 7.3 (arch/x86/entry/entry_64.S, arch/x86/kernel/process_64.c).

#linux #kernel #operatingsystems
```

## Tags

```
linux kernel, kernel stack, system call, syscall, x86-64, entry_SYSCALL_64, swapgs, context switch, per-cpu variables, VMAP_STACK, operating systems, systems programming, kernelkafe
```

## When to post

**Tue 6 Oct, 19:30 IST** (10:00 ET / 07:00 PT). That's day 8 of the current schedule, the
open slot, between the arenas Short (Mon) and the jemalloc/mimalloc Short (Wed).

## Pinned comment

```
All code on screen is real Linux 7.3 source. The 16 KiB figure is THREAD_SIZE on x86-64 without KASAN (KASAN doubles it). Want the full syscall path, from the syscall instruction to your handler, as a long video?
```
