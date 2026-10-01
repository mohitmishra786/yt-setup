"""Word alignment, cue resolution, sentence chunking, prompt-window scoring."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from modules.voice.chatterbox_engine import good_enough, split_sentences, trim_edges
from modules.voice.cues import CueError, resolve_cues
from modules.voice.reference import SR, score_windows
from modules.voice.words import align, estimate, expand_numbers, number_words, similarity


def _heard(pairs: list[tuple[str, float, float]]) -> list[dict]:
    return [{"text": t, "start": s, "end": e} for t, s, e in pairs]


def test_align_maps_script_words_and_interpolates_misses() -> None:
    heard = _heard([("In", 0.1, 0.2), ("sea,", 0.2, 0.4), ("free", 0.5, 0.7), ("buffer", 0.9, 1.3)])
    words = align("In C, free a buffer", heard, 2.0)
    assert [w["text"] for w in words] == ["In", "C,", "free", "a", "buffer"]
    assert words[2]["start"] == 0.5
    # "C," (misheard) and "a" (missed) fall between their matched neighbours
    assert 0.2 <= words[1]["start"] <= words[2]["start"]
    assert 0.7 <= words[3]["start"] <= 0.9


def test_estimate_spreads_evenly() -> None:
    words = estimate("one two three four", 4.0)
    assert [w["start"] for w in words] == [0.0, 1.0, 2.0, 3.0]


def test_similarity() -> None:
    heard = _heard([("free", 0, 1), ("the", 1, 2), ("buffer", 2, 3)])
    assert similarity("free the buffer", heard) == 1.0
    assert similarity("free the buffer now", heard) < 1.0


WORDS_DOC = {
    "slides": [
        {"index": 1, "offset": 0.0, "duration": 3.0,
         "words": estimate("one dangling pointer can crash C", 3.0)},
        {"index": 2, "offset": 3.0, "duration": 4.0,
         "words": estimate("free the buffer then free it again", 4.0)},
    ]
}


def test_resolve_cues_phrase_occurrence_edge_offset() -> None:
    cues = resolve_cues(
        {"cues": [
            {"id": "dangling", "slide": 1, "at": "dangling pointer", "edge": "end"},
            {"id": "free2", "slide": 2, "at": "free", "occurrence": 2, "offset": -0.1},
        ]},
        WORDS_DOC,
    )
    assert cues["dangling"]["t"] == 1.5
    assert cues["free2"]["t"] == pytest.approx(4 * 4 / 7 - 0.1, abs=1e-3)
    assert cues["free2"]["abs"] == pytest.approx(3.0 + cues["free2"]["t"], abs=1e-3)


def test_resolve_cues_reports_every_miss() -> None:
    with pytest.raises(CueError) as exc:
        resolve_cues(
            {"cues": [
                {"id": "a", "slide": 1, "at": "segfault"},
                {"id": "b", "slide": 9, "at": "x"},
            ]},
            WORDS_DOC,
        )
    assert "a:" in str(exc.value) and "b:" in str(exc.value)


def test_split_sentences_merges_fragments_and_splits_long() -> None:
    assert split_sentences("Obvious. It compiles. Then it crashes!") == [
        "Obvious. It compiles.", "Then it crashes!",
    ]
    long = ("word " * 30).strip() + ", " + ("more " * 30).strip() + "."
    parts = split_sentences(long)
    assert len(parts) == 2 and all(len(p) <= 220 for p in parts)


def test_good_enough_is_length_aware() -> None:
    assert good_enough("In C, you can free a buffer and keep its address.", 0.86)
    assert not good_enough("In C, you can free a buffer and keep its address.", 0.7)
    assert good_enough("one two three four five six seven eight nine ten eleven twelve thirteen "
                       "fourteen fifteen sixteen seventeen eighteen nineteen twenty", 0.9)


def test_trim_edges_removes_silence() -> None:
    sr = 1000
    wav = np.concatenate([np.zeros(500), np.ones(300) * 0.5, np.zeros(700)]).astype(np.float32)
    out = trim_edges(wav, sr, pad_s=0.0)
    assert 280 <= len(out) <= 320


def test_score_windows_prefers_continuous_speech(tmp_path: Path) -> None:
    rng = np.random.default_rng(0)
    t = np.arange(int(SR * 30)) / SR
    tone = (0.3 * np.sin(2 * np.pi * 180 * t)).astype(np.float32)
    audio = tone.copy()
    audio[: SR * 1] = 0.001 * rng.standard_normal(SR).astype(np.float32)  # lead-in silence
    for gap in range(12, 30, 2):  # choppy second half: 1s pause every 2s
        audio[gap * SR : gap * SR + SR] = 0.001 * rng.standard_normal(SR).astype(np.float32)
    cands = score_windows(audio, tmp_path / "x.wav", length=10.0)
    best = max(cands, key=lambda c: c.score)
    assert best.start < 2.0 and best.longest_pause < 0.5


def test_numbers_expand_to_script_words() -> None:
    assert number_words(24) == ["twenty", "four"]
    assert number_words(1032) == ["one", "thousand", "thirty", "two"]
    heard = expand_numbers(_heard([("Ask", 0.0, 0.2), ("24", 0.2, 0.6), ("bytes.", 0.6, 0.9)]))
    assert [h["text"] for h in heard] == ["Ask", "twenty", "four", "bytes."]
    assert heard[2]["start"] == pytest.approx(0.4)
    assert similarity("Ask for twenty four bytes.", _heard([("Ask", 0, 1), ("for", 1, 2)]) ) < 1
    assert similarity("Ask twenty four bytes.", heard) == 1.0


def test_pacing_shifts_words_after_each_sentence_break() -> None:
    from modules.voice.pacing import insert_silence, pace_words, sentence_breaks

    words = [
        {"i": 0, "text": "Free", "start": 0.0, "end": 0.3},
        {"i": 1, "text": "it.", "start": 0.3, "end": 0.6},
        {"i": 2, "text": "Now", "start": 1.0, "end": 1.2},
        {"i": 3, "text": "malloc?", "start": 1.2, "end": 1.6},
        {"i": 4, "text": "Same.", "start": 2.0, "end": 2.4},
    ]
    assert sentence_breaks(words) == [(2, 0.8), (4, 1.8)]
    paced, cuts = pace_words(words, 0.5)
    assert [w["start"] for w in paced] == [0.0, 0.3, 1.5, 1.7, 3.0]
    audio = np.ones(100, dtype=np.float32)
    out = insert_silence(audio, [0.02, 0.05], 0.01, sr=1000)
    assert len(out) == 120 and out[20:30].sum() == 0 and out[30] == 1


def test_match_recordings_by_name_or_order(tmp_path: Path) -> None:
    from modules.voice.importer import match_recordings

    named = tmp_path / "named"
    named.mkdir()
    for n in (2, 1, 3):
        (named / f"Slide-0{n}.wav").write_bytes(b"x")
    (named / "notes.txt").write_text("ignore me")
    assert [p.name for p in match_recordings(named, 3)] == [
        "Slide-01.wav", "Slide-02.wav", "Slide-03.wav",
    ]
    ordered = tmp_path / "ordered"
    ordered.mkdir()
    for name in ("b-take.m4a", "a-take.m4a"):
        (ordered / name).write_bytes(b"x")
    assert [p.name for p in match_recordings(ordered, 2)] == ["a-take.m4a", "b-take.m4a"]
    with pytest.raises(FileNotFoundError, match="slide_01"):
        match_recordings(ordered, 3)
