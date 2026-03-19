from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from faster_whisper import WhisperModel

from app.config import Settings


@lru_cache(maxsize=1)
def get_whisper_model(model_name: str, device: str, compute_type: str) -> WhisperModel:
    return WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )


def transcribe_audio(settings: Settings, audio_path: Path) -> str:
    model = get_whisper_model(
        settings.whisper_model,
        settings.whisper_device,
        settings.whisper_compute_type,
    )
    segments, _info = model.transcribe(str(audio_path), vad_filter=True, beam_size=5)
    return " ".join(segment.text.strip() for segment in segments).strip()
