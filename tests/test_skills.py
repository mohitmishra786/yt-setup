"""Skill packages are complete: frontmatter, every referenced file exists, assets are valid."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILLS = ["create-video", "create-short"]


@pytest.mark.parametrize("name", SKILLS)
def test_frontmatter(name: str) -> None:
    text = (REPO / "skills" / name / "SKILL.md").read_text()
    m = re.match(r"---\nname: (.+)\ndescription: (.+)\n---\n", text)
    assert m, "SKILL.md must start with name/description frontmatter"
    assert m.group(1) == name
    assert len(m.group(2)) > 80


@pytest.mark.parametrize("name", SKILLS)
def test_every_referenced_path_exists(name: str) -> None:
    skill = REPO / "skills" / name
    text = (skill / "SKILL.md").read_text()
    paths = set(re.findall(r"`((?:references|templates|scripts|examples|assets)/[\w./-]+)`", text))
    paths |= {p.replace("<repo>/", "") for p in re.findall(r"`(<repo>/[\w./-]+)`", text)}
    paths |= set(re.findall(r"(skills/create-(?:video|short)/[\w./-]+\.(?:py|md|css))", text))
    assert paths, "expected the skill to reference its files"
    missing = []
    for p in paths:
        p = p.rstrip("/.")
        target = REPO / p if p.startswith("skills/") else skill / p
        if not target.exists():
            missing.append(p)
    assert not missing, f"{name}/SKILL.md references missing files: {missing}"


@pytest.mark.parametrize("name", SKILLS)
def test_agent_discovery_symlinks(name: str) -> None:
    for root in (".claude/skills", ".agents/skills", ".opencode/skills"):
        link = REPO / root / name
        assert link.exists() and (link / "SKILL.md").exists(), f"{root}/{name} not discoverable"


def test_short_python_assets_parse() -> None:
    for py in [*(REPO / "skills" / "create-short").rglob("*.py"),
               *(REPO / "skills" / "create-video" / "assets").glob("*.py")]:
        ast.parse(py.read_text(), filename=str(py))


def test_short_examples_are_consistent() -> None:
    ex = REPO / "skills" / "create-short" / "examples" / "kernel-stack"
    outline = json.loads((ex / "outline.json").read_text())
    anchors = json.loads((ex / "anchors.json").read_text())["cues"]
    notes = {int(s["index"]): s["speaker_notes"].lower() for s in outline["slides"]}
    for cue in anchors:
        assert cue["at"].lower() in notes[cue["slide"]], f"anchor {cue['id']} not in its slide"
    build = (ex / "build.py").read_text()
    for cid in {c["id"] for c in anchors}:
        assert f'"{cid}"' in build, f"cue {cid} never used by build.py"


def test_template_has_title_placeholder() -> None:
    tpl = (REPO / "skills" / "create-short" / "templates" / "build.py").read_text()
    assert "__TITLE__" in tpl and "_kit_dir" in tpl and 'set_layout("portrait")' in tpl
