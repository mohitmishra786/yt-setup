"""WhisperX aligned transcription (word-level timestamps + optional diarization)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.logging_setup import get_logger

log = get_logger(__name__)


def transcribe_aligned(
    audio_or_video: Path,
    *,
    model_name: str = "large-v3",
    device: str = "cpu",
    language: str = "en",
    diarize: bool = False,
    align: bool = True,
    hf_token: str | None = None,
    compute_type: str = "float16",
) -> dict[str, Any]:
    """
    Run WhisperX on a media file.

    Returns:
      { language, engine, segments: [{id, start, end, text, words: [...]}], duration }
    """
    try:
        import whisperx  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "whisperx is not installed. pip install whisperx (and torch)"
        ) from exc

    if device == "cpu" and compute_type == "float16":
        compute_type = "int8"

    log.info(
        "WhisperX load model=%s device=%s compute_type=%s",
        model_name,
        device,
        compute_type,
    )
    model = whisperx.load_model(model_name, device, compute_type=compute_type)
    audio = whisperx.load_audio(str(audio_or_video))
    result = model.transcribe(audio, language=language or None, batch_size=8)

    if align:
        align_model, metadata = whisperx.load_align_model(
            language_code=result.get("language") or language,
            device=device,
        )
        result = whisperx.align(
            result["segments"],
            align_model,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )

    if diarize:
        if not hf_token:
            log.warning("diarize=true but HF_TOKEN missing; skipping diarization")
        else:
            try:
                from whisperx.diarize import DiarizationPipeline  # type: ignore

                diarize_model = DiarizationPipeline(
                    use_auth_token=hf_token, device=device
                )
                diarize_segments = diarize_model(audio)
                result = whisperx.assign_word_speakers(diarize_segments, result)
            except Exception as exc:  # noqa: BLE001
                log.warning("Diarization failed: %s", exc)

    segments_out: list[dict[str, Any]] = []
    for i, seg in enumerate(result.get("segments") or []):
        words = []
        for w in seg.get("words") or []:
            if w.get("start") is None or w.get("end") is None:
                continue
            words.append(
                {
                    "word": str(w.get("word") or "").strip(),
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                }
            )
        segments_out.append(
            {
                "id": i,
                "start": float(seg.get("start") or 0.0),
                "end": float(seg.get("end") or 0.0),
                "text": str(seg.get("text") or "").strip(),
                "words": words,
            }
        )

    duration = 0.0
    if segments_out:
        duration = float(segments_out[-1]["end"])

    return {
        "language": result.get("language") or language,
        "engine": "whisperx",
        "segments": segments_out,
        "duration": duration,
    }
