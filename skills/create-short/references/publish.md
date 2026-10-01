# Publish kit for a Short

Write `projects/<id>/publish/short.md`. It must be copy-paste ready: real facts only, and
lengths checked. Filled examples: `examples/kernel-stack/publish-short.md` and
`examples/rust-vs-c/publish-short.md`.

~~~markdown
# Short — publish kit

**File:** `final.mp4` (<len>s, 1080×1920) · **Category:** Education · **Not made for kids**
**Related video:** <the long video this Short should drive viewers to, or "none yet">

## Title
**Use:** <≤ 60 characters> #shorts
Alternates:
- <alternate 1> #shorts
- <alternate 2> #shorts

## Description
```
<2–4 sentences: the claim, the mechanism, the proof (what was actually run or read).>
<Source shown: file / version / environment.>
<Optional: Full video: <FULL VIDEO LINK>>

#tag1 #tag2 #tag3
```

## Tags
```
<comma-separated, ≤ 500 characters, specific terms first, channel name last>
```

## When to post
**<Day date>, <channel.post_time> <channel.timezone>** (<US-morning equivalent>). <Why this slot.>

## Pinned comment
```
<Real outputs and caveats, e.g. "your garbage value will differ, it's UB"; then a question.>
```
~~~

Rules:

- **Title:** lead with the surprising outcome ("C compiles this bug. Rust refuses."), not
  the topic name. ≤ 60 characters before `#shorts`. No clickbait the Short doesn't pay off.
- **Description:** every factual sentence must be something the Short shows or the
  verification produced (tool versions, source file names).
- **Hashtags:** exactly 3 at the end. The first is the broad topic (`#linux`, `#rust`), then
  narrower ones.
- **Pinned comment:** put caveats here (config-dependent sizes, varying outputs), then ask
  one specific question that invites expert replies.
- **Schedule:** if a `publish/schedule.md` exists in a related long-video project, slot the
  Short into an open day there and note it in both places. Otherwise suggest the next
  `channel.post_time` that doesn't collide with another post.
- **Check lengths** before handing over: title ≤ 100, tags ≤ 500, description ≤ 5000
  characters.
