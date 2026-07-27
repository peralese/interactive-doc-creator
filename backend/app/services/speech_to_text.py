"""Lazy-loaded local Whisper transcription."""

from __future__ import annotations

import asyncio
import math
import os
import tempfile
from collections.abc import AsyncGenerator, AsyncIterable
from pathlib import Path
from typing import Any

from ..config import settings


class SpeechToTextService:
    def __init__(self) -> None:
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
        return self._model

    def _transcribe_sync(self, audio_file_path: str) -> dict[str, Any]:
        segments, info = self._get_model().transcribe(
            audio_file_path, language=settings.whisper_language
        )
        materialized = list(segments)
        text = " ".join(segment.text.strip() for segment in materialized).strip()
        confidence = (
            sum(math.exp(segment.avg_logprob) for segment in materialized) / len(materialized)
            if materialized
            else 0.0
        )
        return {"text": text, "confidence": max(0.0, min(1.0, confidence)), "language": info.language}

    async def transcribe(self, audio_file_path: str) -> dict[str, Any]:
        if not Path(audio_file_path).is_file():
            raise FileNotFoundError(audio_file_path)
        return await asyncio.to_thread(self._transcribe_sync, audio_file_path)

    async def transcribe_stream(
        self, audio_stream: AsyncIterable[bytes]
    ) -> AsyncGenerator[str, None]:
        fd, path = tempfile.mkstemp(suffix=".webm")
        try:
            with os.fdopen(fd, "wb") as output:
                async for chunk in audio_stream:
                    output.write(chunk)
            result = await self.transcribe(path)
            if result["text"]:
                yield result["text"]
        finally:
            Path(path).unlink(missing_ok=True)
