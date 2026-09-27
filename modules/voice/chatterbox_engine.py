"""Chatterbox (Resemble AI) — MIT local voice cloning (ElevenLabs-class quality target)."""

from __future__ import annotations

from pathlib import Path

from core.logging_setup import get_logger
from modules.voice.engine import VoiceEngine, VoiceEngineError, convert_to_mp3
from modules.voice.profile import get_profile, validate_profile_for_cloning

log = get_logger(__name__)


class ChatterboxEngine(VoiceEngine):
    """
    Production voice backend using Resemble AI Chatterbox (MIT).

    Zero-shot cloning: pass a clean reference.wav from a VoiceProfile.
    Quality depends heavily on reference audio (see docs/VOICE_CLONING.md).
    """

    name = "chatterbox"

    def __init__(self, *, exaggeration: float | None = None, cfg_weight: float | None = None) -> None:
        import importlib.util

        if (
            importlib.util.find_spec("chatterbox") is None
            and importlib.util.find_spec("chatterbox_tts") is None
        ):
            raise ImportError(
                "chatterbox package not installed.\n"
                "  pip install chatterbox-tts\n"
                "  or: pip install git+https://github.com/resemble-ai/chatterbox.git\n"
                "See docs/VOICE_CLONING.md"
            )
        self._model = None
        self._device: str | None = None
        self.exaggeration = exaggeration
        self.cfg_weight = cfg_weight

    def _resolve_device(self) -> str:
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                return "mps"
        except Exception:  # noqa: BLE001
            pass
        return "cpu"

    def warmup(self) -> None:
        if self._model is not None:
            return
        self._device = self._resolve_device()
        log.info("Loading Chatterbox model on device=%s", self._device)
        try:
            from chatterbox.tts import ChatterboxTTS  # type: ignore

            self._model = ChatterboxTTS.from_pretrained(device=self._device)
        except Exception as exc:  # noqa: BLE001
            raise VoiceEngineError(
                f"Failed to load Chatterbox on {self._device}: {exc}"
            ) from exc

    def synthesize(self, text: str, voice_id: str, output_path: Path) -> Path:
        self.warmup()
        assert self._model is not None
        text = (text or " ").strip()
        if not text:
            text = " "

        profile = get_profile(voice_id)
        for w in validate_profile_for_cloning(profile):
            log.warning("voice profile: %s", w)
        ref = profile.resolve_reference()
        log.info(
            "Chatterbox clone voice_id=%s ref=%s text_chars=%d",
            voice_id,
            ref.name,
            len(text),
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        gen_kwargs: dict = {"audio_prompt_path": str(ref)}
        # Optional expressiveness knobs when supported by installed version
        if self.exaggeration is not None:
            gen_kwargs["exaggeration"] = self.exaggeration
        if self.cfg_weight is not None:
            gen_kwargs["cfg_weight"] = self.cfg_weight

        try:
            try:
                wav = self._model.generate(text, **gen_kwargs)
            except TypeError:
                # Older API without extra kwargs
                wav = self._model.generate(text, audio_prompt_path=str(ref))
        except TypeError:
            # Last resort: no prompt (default speaker) — not a real clone
            log.error(
                "Chatterbox API rejected audio_prompt_path; install a current chatterbox build"
            )
            wav = self._model.generate(text)
        except Exception as exc:  # noqa: BLE001
            raise VoiceEngineError(f"Chatterbox generate failed: {exc}") from exc

        wav_path = output_path.with_suffix(".wav")
        self._save_wav(wav, wav_path)

        if output_path.suffix.lower() == ".mp3":
            convert_to_mp3(wav_path, output_path)
            wav_path.unlink(missing_ok=True)
        elif wav_path != output_path:
            wav_path.replace(output_path)
        return output_path

    def _save_wav(self, wav, wav_path: Path) -> None:
        if isinstance(wav, (str, Path)):
            Path(wav).replace(wav_path)
            return
        sample_rate = int(getattr(self._model, "sr", None) or getattr(self._model, "sample_rate", 24000))
        try:
            import torch
            import torchaudio

            if isinstance(wav, torch.Tensor):
                t = wav.detach().cpu()
                if t.dim() == 1:
                    t = t.unsqueeze(0)
                torchaudio.save(str(wav_path), t, sample_rate)
                return
        except Exception as exc:  # noqa: BLE001
            log.debug("torchaudio save path failed: %s", exc)
        try:
            import numpy as np
            import soundfile as sf

            arr = np.asarray(wav)
            if arr.ndim > 1:
                arr = arr.squeeze()
            sf.write(str(wav_path), arr, sample_rate)
            return
        except Exception as exc:  # noqa: BLE001
            raise VoiceEngineError(
                f"Could not save Chatterbox audio (install torchaudio or soundfile): {exc}"
            ) from exc
