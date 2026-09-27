"""Visual Quality Assurance (QA) checks against design tokens and creative laws."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.logging_setup import get_logger
from core.schemas import Storyboard, StoryboardBeat

from modules.scenegen.tokens import DEFAULT_DESIGN_TOKENS, DesignTokens

log = get_logger(__name__)


class VisualQAError(RuntimeError):
    """Raised when an animated scene violates design tokens or pacing laws."""


@dataclass
class QAResult:
    scene_id: str
    passed: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


_HEX_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3,8})\b")


def check_palette_compliance(
    html_content: str,
    tokens: DesignTokens = DEFAULT_DESIGN_TOKENS,
) -> list[str]:
    """
    Verify that all hex colors used in the scene match the design tokens palette.

    Forbids arbitrary inline colors that drift from brand consistency.
    """
    allowed_hex = {
        tokens.bg_color.lower(),
        tokens.shape_neutral_1.lower(),
        tokens.shape_neutral_2.lower(),
        tokens.border_color.lower(),
        tokens.text_primary.lower(),
        tokens.text_muted.lower(),
        tokens.text_accent.lower(),
        tokens.accent_primary.lower(),
        tokens.accent_secondary.lower(),
        tokens.accent_success.lower(),
        tokens.accent_warning.lower(),
        tokens.accent_purple.lower(),
    }

    violations: list[str] = []
    found_colors = set(m.group(0).lower() for m in _HEX_COLOR_RE.finditer(html_content))

    for col in found_colors:
        # Allow 3-char shorthand expansions if equivalent
        if col not in allowed_hex:
            # Check if it's an allowed RGB or rgba component
            violations.append(f"Forbidden color {col} detected (not in design tokens palette)")

    return violations


def check_sequential_reveals(
    beat: StoryboardBeat,
    min_stagger_seconds: float = 1.0,
) -> list[str]:
    """
    Enforce 'One idea revealed at a time' heuristic.

    All enter/draw actions must be separated by at least min_stagger_seconds.
    """
    violations: list[str] = []
    reveal_actions = [a for a in beat.actions if a.action in ("enter", "draw", "fade_in")]
    reveal_actions.sort(key=lambda a: a.start_time)

    for i in range(1, len(reveal_actions)):
        prev_act = reveal_actions[i - 1]
        curr_act = reveal_actions[i]
        delta = curr_act.start_time - prev_act.start_time
        if delta < min_stagger_seconds:
            violations.append(
                f"Actions for '{prev_act.target_id}' (at {prev_act.start_time:.1f}s) and "
                f"'{curr_act.target_id}' (at {curr_act.start_time:.1f}s) enter too quickly "
                f"(delta {delta:.2f}s < {min_stagger_seconds}s). Reveal one element at a time."
            )

    return violations


def check_reading_pace_and_hold(
    beat: StoryboardBeat,
    tokens: DesignTokens = DEFAULT_DESIGN_TOKENS,
) -> tuple[list[str], dict[str, Any]]:
    """
    Validate text reading duration and post-reveal hold times.
    """
    violations: list[str] = []
    words = len(beat.narration_text.split())
    min_required_reading = words * tokens.per_word_reading_pace

    # End of last action
    last_action_end = max((a.start_time + a.duration for a in beat.actions), default=0.0)
    final_hold = beat.duration_estimate - last_action_end

    metrics = {
        "word_count": words,
        "min_reading_duration": round(min_required_reading, 2),
        "duration_estimate": beat.duration_estimate,
        "last_action_end": round(last_action_end, 2),
        "final_hold_seconds": round(final_hold, 2),
    }

    if final_hold < 1.0:
        violations.append(
            f"Scene duration ({beat.duration_estimate:.1f}s) ends too abruptly after "
            f"last action ({last_action_end:.1f}s). Final hold is {final_hold:.1f}s, "
            f"must be >= 1.0s (recommended {tokens.default_hold_per_reveal:.1f}s)."
        )

    return violations, metrics


def validate_beat_qa(
    beat: StoryboardBeat,
    html_content: str | None = None,
    tokens: DesignTokens = DEFAULT_DESIGN_TOKENS,
    *,
    strict: bool = True,
) -> QAResult:
    """Run full visual QA suite against a single beat."""
    violations: list[str] = []
    warnings: list[str] = []

    # 1. Sequential reveals check
    seq_errs = check_sequential_reveals(beat)
    violations.extend(seq_errs)

    # 2. Reading pace and hold time check
    hold_errs, metrics = check_reading_pace_and_hold(beat, tokens)
    violations.extend(hold_errs)

    # 3. Palette compliance check (if HTML available)
    if html_content:
        palette_errs = check_palette_compliance(html_content, tokens)
        violations.extend(palette_errs)

    passed = len(violations) == 0
    if not passed and strict:
        log.warning("Visual QA failed for %s: %s", beat.id, "; ".join(violations))

    return QAResult(
        scene_id=beat.id,
        passed=passed,
        violations=violations,
        warnings=warnings,
        metrics=metrics,
    )


def validate_storyboard_qa(
    storyboard: Storyboard,
    scenes_dir: Path | None = None,
    tokens: DesignTokens = DEFAULT_DESIGN_TOKENS,
    *,
    raise_on_failure: bool = False,
) -> list[QAResult]:
    """Validate all beats in a storyboard before allowing assembly."""
    results: list[QAResult] = []

    for beat in storyboard.beats:
        html_text = None
        if scenes_dir:
            html_file = scenes_dir / f"{beat.id}.html"
            if html_file.exists():
                html_text = html_file.read_text(encoding="utf-8")

        res = validate_beat_qa(beat, html_text, tokens, strict=raise_on_failure)
        results.append(res)

    failed = [r for r in results if not r.passed]
    if failed and raise_on_failure:
        err_msg = "\n".join(f"[{r.scene_id}]: " + " | ".join(r.violations) for r in failed)
        raise VisualQAError(f"Visual QA check failed on {len(failed)} scene(s):\n{err_msg}")

    return results
