"""XTTS v2 voice engine — broader language coverage; check Coqui license for commercial use."""

from __future__ import annotations

from pathlib import Path

from modules.voice.engine import VoiceEngine, VoiceEngineError, convert_to_mp3

VOICES_DIR = Path(__file__).resolve().parent / "voices"


class XTTSEngine(VoiceEngine):
    """
    Optional multi-language fallback (Coqui TTS / XTTS v2).

    License note: XTTS v2 is NOT MIT; commercial use may require a Coqui license.
    Prefer Chatterbox for commercial channels unless you have confirmed rights.
    """

    name = "xtts"

    def __init__(self) -> None:
        import importlib.util

        if importlib.util.find_spec("TTS") is None:
            raise ImportError(
                "Coqui TTS not installed. See https://github.com/coqui-ai/TTS"
            )
        self._tts = None

    def warmup(self) -> None:
        if self._tts is not None:
            return
        from TTS.api import TTS  # type: ignore

        self._tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

    def _reference(self, voice_id: str) -> Path:
        for name in (f"{voice_id}.wav", "default.wav"):
            cand = VOICES_DIR / name
            if cand.exists():
                return cand
        raise VoiceEngineError(
            f"XTTS requires a reference wav at {VOICES_DIR / (voice_id + '.wav')}"
        )

    def synthesize(self, text: str, voice_id: str, output_path: Path) -> Path:
        self.warmup()
        assert self._tts is not None
        ref = self._reference(voice_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wav_path = output_path.with_suffix(".wav")
        self._tts.tts_to_file(
            text=text.strip() or " ",
            file_path=str(wav_path),
            speaker_wav=str(ref),
            language="en",
        )
        if output_path.suffix.lower() == ".mp3":
            convert_to_mp3(wav_path, output_path)
            wav_path.unlink(missing_ok=True)
        else:
            wav_path.replace(output_path)
        return output_path
