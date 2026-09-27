"""ElevenLabs paid TTS fallback for high-stakes videos."""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from modules.voice.engine import VoiceEngine, VoiceEngineError


class ElevenLabsEngine(VoiceEngine):
    """Optional paid backend. Selected via config voice.engine: elevenlabs."""

    name = "elevenlabs"
    API_BASE = "https://api.elevenlabs.io/v1"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> None:
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY") or ""
        if not self.api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY is not set; cannot initialize ElevenLabsEngine"
            )
        self.model_id = model_id
        self.stability = stability
        self.similarity_boost = similarity_boost

    def synthesize(self, text: str, voice_id: str, output_path: Path) -> Path:
        if not voice_id or voice_id == "default":
            raise VoiceEngineError(
                "ElevenLabs requires a real voice_id (not 'default'). "
                "Set --voice <elevenlabs_voice_id>."
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{self.API_BASE}/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }
        payload = {
            "text": text.strip() or " ",
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
            },
        }
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                raise VoiceEngineError(
                    f"ElevenLabs HTTP {r.status_code}: {r.text[:500]}"
                )
            output_path.write_bytes(r.content)
        if output_path.stat().st_size < 100:
            raise VoiceEngineError("ElevenLabs returned empty audio")
        return output_path
