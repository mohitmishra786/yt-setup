#!/usr/bin/env python3
"""Generate modules/slidebuilder/templates/default.pptx master shell."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pptx import Presentation  # noqa: E402
from pptx.util import Inches  # noqa: E402

from modules.slidebuilder.theme import DEFAULT_THEME  # noqa: E402


def main() -> None:
    out = ROOT / "modules" / "slidebuilder" / "templates" / "default.pptx"
    out.parent.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    prs.slide_width = Inches(DEFAULT_THEME.width_in)
    prs.slide_height = Inches(DEFAULT_THEME.height_in)
    prs.save(str(out))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
