"""Scene kit (skills/create-video/assets/scenekit.py): focus stack, notes, branding."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[1] / "skills" / "create-video" / "assets"
sys.path.insert(0, str(ASSETS))
import scenekit as kit  # noqa: E402
from core.config import AppConfig, ChannelSettings  # noqa: E402


@pytest.fixture(autouse=True)
def portrait():
    kit.set_layout("portrait")
    yield
    kit.set_layout("landscape")


def test_focus_first_item_is_centred_then_pushed_up() -> None:
    s = kit.Scene(1, {})
    f = s.focus([200, 120], gap=50)
    top, bottom = kit.L["area"]
    centre = (top + bottom) / 2
    assert f.y(0) == round(centre - 100)                 # alone: centred
    assert f.pos[1][0] < f.y(0)                          # second arrives: first moves up
    stack = 200 + 50 + 120
    assert f.pos[1][0] == round(centre - stack / 2)      # the pair is centred together
    assert f.pos[1][1] == f.pos[1][0] + 250


def test_focus_never_leaves_the_content_area() -> None:
    s = kit.Scene(1, {})
    f = s.focus([600, 600, 600])
    top, _ = kit.L["area"]
    assert min(min(row) for row in f.pos) >= top


def test_focus_run_moves_and_dims_previous_item() -> None:
    s = kit.Scene(2, {"s2_a": {"slide": 2, "t": 1.0}, "s2_b": {"slide": 2, "t": 3.0}})
    f = s.focus([100, 100])
    for k, n in enumerate(("a", "b")):
        s.box(n, 90, f.y(k), 900, 100)
    f.run(["a", "b"], ["s2_a", "s2_b"])
    js = "\n".join(s.js)
    assert 'tl.to("#s2-a",{y:' in js and "opacity:0.45" in js


def test_notes_drop_flashes_and_skip_section_label() -> None:
    s = kit.Scene(3, {"s3_x": {"slide": 3, "t": 0.4}, "s3_y": {"slide": 3, "t": 4.0}})
    s.add_notes(None, [(0.0, "first"), ("s3_x", "second"), ("s3_y", "third")])
    html = "".join(s.html)
    assert "first" not in html                 # replaced after 0.4s: a flash, dropped
    assert "second" in html and "third" in html
    assert "data-kicker" not in html           # no section label by default


def test_wordmark_uses_last_part_as_accent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(kit, "CHANNEL", ("Byte", "Bistro"))
    mark = kit.wordmark(kit.Scene(0, {}))
    assert mark.startswith("Byte<span") and ">Bistro</span>" in mark


def test_accent_fill_and_caption_names() -> None:
    assert kit._fill("#5aa9f0", 0.14) == "rgba(90,169,240,0.14)"
    assert kit.caption_word("G-lib-C,") == "glibc,"
    assert kit.caption_word("Mee-malloc") == "mimalloc"


def test_channel_settings_default_is_generic() -> None:
    ch = AppConfig().channel
    assert isinstance(ch, ChannelSettings)
    assert ch.wordmark == ["Your", "Channel"] and ch.handle == "@yourchannel"
