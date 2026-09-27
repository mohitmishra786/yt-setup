"""SRT/VTT export helpers."""

from __future__ import annotations

from modules.transcriber.export_srt_vtt import segments_to_srt, segments_to_vtt


def test_srt_basic() -> None:
    segs = [{"start": 0.0, "end": 1.5, "text": "Hello world"}]
    srt = segments_to_srt(segs)
    assert "1\n" in srt
    assert "00:00:00,000 --> 00:00:01,500" in srt
    assert "Hello world" in srt


def test_vtt_basic() -> None:
    segs = [{"start": 65.0, "end": 70.0, "text": "Later"}]
    vtt = segments_to_vtt(segs)
    assert vtt.startswith("WEBVTT")
    assert "00:01:05.000 --> 00:01:10.000" in vtt
