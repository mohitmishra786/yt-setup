"""Resolve word-anchored animation cues to exact times.

`projects/<id>/anchors.json` names *what is said* when each visual event must happen:

    {"cues": [
      {"id": "heap_freed", "slide": 2, "at": "free"},
      {"id": "ub_label",   "slide": 2, "at": "undefined behavior", "edge": "end", "offset": 0.1},
      {"id": "free_again", "slide": 2, "at": "free", "occurrence": 2}
    ]}

`resolve_cues` looks each phrase up in audio/words.json and returns, per cue id,
`t` (seconds from the start of that slide's narration = local scene time when the scene's
voice clip starts at the scene start) and `abs` (seconds from the start of the video when
scenes play back to back).
"""

from __future__ import annotations

from typing import Any

from modules.voice.words import norm, script_words


class CueError(ValueError):
    pass


def _find(words: list[dict[str, Any]], phrase: str, occurrence: int) -> tuple[int, int]:
    keys = [norm(w["text"]) for w in words]
    target = [norm(w) for w in script_words(phrase) if norm(w)]
    if not target:
        raise CueError(f"empty phrase {phrase!r}")
    seen = 0
    for i in range(len(keys) - len(target) + 1):
        if keys[i : i + len(target)] == target:
            seen += 1
            if seen == occurrence:
                return i, i + len(target) - 1
    raise CueError(f"phrase {phrase!r} (occurrence {occurrence}) not found; found {seen}")


def resolve_cues(anchors: dict[str, Any], words_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    slides = {int(s["index"]): s for s in words_doc.get("slides", [])}
    out: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for cue in anchors.get("cues", []):
        cid = str(cue.get("id") or "")
        try:
            if not cid:
                raise CueError("cue without id")
            if cid in out:
                raise CueError("duplicate id")
            slide = slides.get(int(cue["slide"]))
            if slide is None:
                raise CueError(f"slide {cue['slide']} not in words.json")
            first, last = _find(slide["words"], str(cue["at"]), int(cue.get("occurrence", 1)))
            edge = cue.get("edge", "start")
            if edge not in {"start", "end"}:
                raise CueError(f"edge must be start|end, got {edge!r}")
            words = slide["words"]
            base = words[first]["start"] if edge == "start" else words[last]["end"]
            t = max(0.0, float(base) + float(cue.get("offset", 0.0)))
            out[cid] = {
                "slide": int(cue["slide"]),
                "t": round(t, 3),
                "abs": round(float(slide["offset"]) + t, 3),
                "at": cue["at"],
            }
        except (CueError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{cid or '?'}: {exc}")
    if errors:
        raise CueError("unresolved cues:\n  " + "\n  ".join(errors))
    return out
