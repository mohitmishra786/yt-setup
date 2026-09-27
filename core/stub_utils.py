"""Helpers used by Phase-0 stub stages to pass dummy artifacts through."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_minimal_png(path: Path, width: int = 64, height: int = 64) -> None:
    """Write a tiny valid PNG without requiring Pillow (Phase 0)."""
    # 1x1 PNG fallback encoded; for non-1x1 we still write a valid 1x1
    # and note dimensions in a sidecar if needed. Keeps stubs dependency-light.
    _ = (width, height)
    png_1x1 = bytes(
        [
            0x89,
            0x50,
            0x4E,
            0x47,
            0x0D,
            0x0A,
            0x1A,
            0x0A,
            0x00,
            0x00,
            0x00,
            0x0D,
            0x49,
            0x48,
            0x44,
            0x52,
            0x00,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0x00,
            0x01,
            0x08,
            0x02,
            0x00,
            0x00,
            0x00,
            0x90,
            0x77,
            0x53,
            0xDE,
            0x00,
            0x00,
            0x00,
            0x0C,
            0x49,
            0x44,
            0x41,
            0x54,
            0x08,
            0xD7,
            0x63,
            0xF8,
            0xCF,
            0xC0,
            0x00,
            0x00,
            0x00,
            0x03,
            0x00,
            0x01,
            0x00,
            0x05,
            0xFE,
            0xD4,
            0xEF,
            0x00,
            0x00,
            0x00,
            0x00,
            0x49,
            0x45,
            0x4E,
            0x44,
            0xAE,
            0x42,
            0x60,
            0x82,
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_1x1)


def write_minimal_mp3(path: Path) -> None:
    """
    Write a minimal MPEG frame header so tools see a non-empty .mp3.

    Not a playable track — Phase 0 placeholder only.
    """
    # MPEG1 Layer3, 128kbps, 44100Hz, mono frame (padding=0) — common stub pattern
    frame = bytes(
        [
            0xFF,
            0xFB,
            0x90,
            0x00,
            *([0x00] * 413),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(frame)


def write_minimal_mp4(path: Path) -> None:
    """
    Write a minimal ISO BMFF 'ftyp' + empty 'mdat' box.

    Not a playable video — Phase 0 placeholder so paths exist end-to-end.
    """
    # ftyp box
    ftyp = b""
    major = b"isom"
    minor = (0).to_bytes(4, "big")
    brands = b"isomiso2mp41"
    ftyp_payload = major + minor + brands
    ftyp = (8 + len(ftyp_payload)).to_bytes(4, "big") + b"ftyp" + ftyp_payload
    # empty mdat
    mdat = (8).to_bytes(4, "big") + b"mdat"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(ftyp + mdat)


def write_minimal_pptx(path: Path) -> None:
    """
    Write a minimal ZIP-based PPTX container with required parts.

    Good enough for existence checks; Phase 1 replaces with python-pptx.
    """
    import zipfile

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>
"""
    presentation = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:sldIdLst/>
</p:presentation>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("ppt/presentation.xml", presentation)
