"""FastAPI server providing the Web Studio UI, voice cloning endpoints, and OpenAI-compatible TTS API."""

from __future__ import annotations

import io
import logging
import tempfile
import time
import zipfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from freevoice import __version__
from freevoice.audio import encode_audio
from freevoice.config import DEFAULT_DEVICE, DEFAULT_VOICE
from freevoice.registry import VoiceRegistry

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


class SpeechRequest(BaseModel):
    model: str = Field(default="kokoro-82m", description="Model identifier (kokoro-82m or qwen3-tts-0.6b)")
    input: str = Field(..., min_length=1, description="Text to synthesize into speech")
    voice: str = Field(default=DEFAULT_VOICE, description="Voice ID (e.g. af_heart, bm_george, or clone:my_voice)")
    response_format: str = Field(default="mp3", description="Output audio format: mp3, wav, ogg, or flac")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speaking speed multiplier (0.5 to 2.0)")
    language: Optional[str] = Field(default=None, description="Optional language override for cloned voices")


class BatchItem(BaseModel):
    filename: Optional[str] = None
    text: str = Field(..., min_length=1)
    voice: Optional[str] = None
    speed: Optional[float] = None


class BatchRequest(BaseModel):
    items: List[BatchItem] = Field(..., min_length=1)
    default_voice: str = Field(default=DEFAULT_VOICE)
    response_format: str = Field(default="mp3")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


def create_app(device: str = DEFAULT_DEVICE) -> FastAPI:
    app = FastAPI(
        title="FreeVoice API",
        version=__version__,
        description="Free, unlimited open-source TTS and 3-second voice cloning API compatible with OpenAI's audio speech schema.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    registry = VoiceRegistry(device=device)
    app.state.registry = registry

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__, "device": registry.kokoro.device}

    @app.get("/v1/voices")
    def list_voices():
        voices = registry.list_all_voices()
        return {
            "object": "list",
            "count": len(voices),
            "voices": voices,
        }

    @app.post("/v1/audio/speech")
    def create_speech(req: SpeechRequest):
        try:
            waveform, sample_rate = registry.synthesize(
                text=req.input,
                voice=req.voice,
                speed=req.speed,
                language=req.language,
            )
            audio_bytes, mime_type = encode_audio(
                waveform=waveform,
                sample_rate=sample_rate,
                response_format=req.response_format,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        ext = req.response_format.lower().strip()
        filename = f"freevoice_{int(time.time())}.{ext}"
        return Response(
            content=audio_bytes,
            media_type=mime_type,
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    @app.post("/v1/voices/clone")
    async def clone_voice(
        name: str = Form(..., description="Display name for the cloned voice"),
        ref_text: str = Form(default="", description="Transcript of the 3-second reference audio"),
        language: str = Form(default="English", description="Primary spoken language of the sample"),
        sample: UploadFile = File(..., description="3-second clean audio sample (WAV, MP3, OGG, FLAC)"),
    ):
        suffix = Path(sample.filename or "sample.wav").suffix or ".wav"
        raw_bytes = await sample.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = Path(tmp.name)

        try:
            profile = registry.cloner.save_profile(
                name=name,
                source_audio_path=tmp_path,
                ref_text=ref_text,
                language=language,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        finally:
            tmp_path.unlink(missing_ok=True)

        return {
            "id": profile.id,
            "name": profile.name,
            "language": profile.language,
            "duration_seconds": profile.duration_seconds,
            "ref_text": profile.ref_text,
        }

    @app.delete("/v1/voices/clone/{voice_slug}")
    def delete_cloned_voice(voice_slug: str):
        deleted = registry.cloner.delete_profile(voice_slug)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Cloned voice '{voice_slug}' not found.")
        return {"deleted": True, "id": f"clone:{voice_slug.removeprefix('clone:')}"}

    @app.post("/v1/audio/batch")
    def batch_speech(req: BatchRequest):
        ext = req.response_format.lower().strip()
        zip_buf = io.BytesIO()
        try:
            with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for idx, item in enumerate(req.items, start=1):
                    voice = item.voice or req.default_voice
                    speed = item.speed if item.speed is not None else req.speed
                    waveform, sr = registry.synthesize(
                        text=item.text,
                        voice=voice,
                        speed=speed,
                    )
                    audio_bytes, _ = encode_audio(
                        waveform=waveform,
                        sample_rate=sr,
                        response_format=ext,
                    )
                    raw_name = item.filename or f"line_{idx:03d}.{ext}"
                    if not raw_name.lower().endswith(f".{ext}"):
                        raw_name = f"{Path(raw_name).stem}.{ext}"
                    zf.writestr(raw_name, audio_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return Response(
            content=zip_buf.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="freevoice_batch.zip"'},
        )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    return app