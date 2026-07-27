"""Speech-to-text HTTP and WebSocket endpoints."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel

from ..config import settings
from ..services.speech_to_text import SpeechToTextService

logger = logging.getLogger(__name__)
router = APIRouter()


class TranscriptionResponse(BaseModel):
    """Completed transcription and persisted audio metadata."""

    text: str
    confidence: float
    language: str
    audio_path: str
    session_id: UUID | None = None


@lru_cache(maxsize=1)
def get_speech_service() -> SpeechToTextService:
    """Share one lazily initialized Whisper model between requests."""
    return SpeechToTextService()


SpeechService = Annotated[SpeechToTextService, Depends(get_speech_service)]


def _audio_destination(filename: str | None, session_id: UUID | None) -> Path:
    suffix = Path(filename or "recording.webm").suffix.lower() or ".webm"
    if len(suffix) > 10 or not suffix[1:].isalnum():
        suffix = ".webm"
    directory = Path(settings.audio_storage_path)
    if session_id is not None:
        directory /= str(session_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{uuid4()}{suffix}"


async def _save_upload(upload: UploadFile, destination: Path) -> None:
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_audio_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Audio exceeds the {settings.max_audio_size}-byte limit",
                    )
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="The uploaded audio file is empty")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


@router.post("/", response_model=TranscriptionResponse)
async def transcribe_audio(
    speech: SpeechService,
    audio: Annotated[UploadFile, File(description="Audio recording")],
    session_id: Annotated[UUID | None, Form()] = None,
):
    """Persist and transcribe one uploaded recording."""
    destination = _audio_destination(audio.filename, session_id)
    await _save_upload(audio, destination)
    try:
        result = await speech.transcribe(str(destination))
    except Exception as exc:
        destination.unlink(missing_ok=True)
        logger.exception("Audio transcription failed")
        raise HTTPException(status_code=422, detail=f"Unable to transcribe audio: {exc}") from exc
    return TranscriptionResponse(
        **result,
        audio_path=str(destination),
        session_id=session_id,
    )


@router.websocket("/stream")
async def transcribe_audio_stream(websocket: WebSocket) -> None:
    """Collect binary audio frames and transcribe after a `stop` text frame.

    Server messages are JSON objects with `ready`, `transcribing`, `result`, or
    `error` event names. This buffered protocol works with browser MediaRecorder
    chunks while leaving incremental decoding as a future optimization.
    """
    await websocket.accept()
    speech = get_speech_service()
    chunks: list[bytes] = []
    total_size = 0
    await websocket.send_json({"event": "ready"})
    try:
        while True:
            message: dict[str, Any] = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            chunk = message.get("bytes")
            if chunk is not None:
                total_size += len(chunk)
                if total_size > settings.max_audio_size:
                    await websocket.send_json(
                        {
                            "event": "error",
                            "detail": f"Audio exceeds the {settings.max_audio_size}-byte limit",
                        }
                    )
                    await websocket.close(code=1009)
                    return
                chunks.append(chunk)
                continue
            command = (message.get("text") or "").strip().lower()
            if command == "stop":
                break
            if command == "cancel":
                await websocket.close(code=1000)
                return
        if not chunks:
            await websocket.send_json({"event": "error", "detail": "No audio received"})
            await websocket.close(code=1003)
            return
        await websocket.send_json({"event": "transcribing"})

        async def stream():
            for chunk in chunks:
                yield chunk

        text = ""
        async for transcript in speech.transcribe_stream(stream()):
            text = transcript
        await websocket.send_json({"event": "result", "text": text})
        await websocket.close(code=1000)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        logger.exception("Streaming transcription failed")
        await websocket.send_json({"event": "error", "detail": str(exc)})
        await websocket.close(code=1011)
