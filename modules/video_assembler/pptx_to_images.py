"""Convert PPTX slides to PNG frames via headless LibreOffice."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from core.logging_setup import get_logger

log = get_logger(__name__)


def find_libreoffice(configured: str = "") -> str | None:
    if configured:
        return configured if Path(configured).exists() or shutil.which(configured) else None
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    # Common macOS path
    mac = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    if mac.exists():
        return str(mac)
    return None


def pptx_to_pngs(
    pptx_path: Path,
    output_dir: Path,
    *,
    libreoffice_bin: str = "",
) -> list[Path]:
    """
    Convert each slide in `pptx_path` to PNG under `output_dir`.

    Phase 0 does not call this; Phase 2 wires it into the assembler.
    """
    binary = find_libreoffice(libreoffice_bin)
    if not binary:
        raise RuntimeError(
            "LibreOffice not found. Install it and ensure `soffice` is on PATH, "
            "or set video.libreoffice_bin in config.yaml"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        binary,
        "--headless",
        "--convert-to",
        "png",
        "--outdir",
        str(output_dir),
        str(pptx_path),
    ]
    log.info("LibreOffice convert: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"LibreOffice failed (exit {proc.returncode}): {proc.stderr or proc.stdout}"
        )

    frames = sorted(output_dir.glob("*.png"))
    if not frames:
        raise RuntimeError(f"No PNG frames produced in {output_dir}")
    return frames
