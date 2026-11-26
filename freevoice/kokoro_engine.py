"""Kokoro-82M synthesis engine (Apache 2.0) with lazy pipeline loading."""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Tuple

import numpy as np

from freevoice.config import (
    DEFAULT_VOICE,
    KOKORO_REPO_ID,
    KOKORO_VOICE_MAP,
    OPENAI_VOICE_ALIASES,
    resolve_device,
)

logger = logging.getLogger(__name__)

KOKORO_SAMPLE_RATE = 24000


class KokoroEngine:
    """Thread-safe wrapper around Kokoro-82M KModel and per-language KPipeline instances."""

    def __init__(self, device: str = "auto", repo_id: str = KOKORO_REPO_ID) -> None:
        self.device = resolve_device(device)
        self.repo_id = repo_id
        self._model = None
        self._pipelines: Dict[str, object] = {}
        self._lock = threading.Lock()

    def _ensure_model(self):
        if self._model is None:
            from kokoro import KModel

            logger.info("Loading Kokoro-82M model (%s) on device=%s...", self.repo_id, self.device)
            self._model = KModel(repo_id=self.repo_id).to(self.device).eval()
        return self._model

    def _get_pipeline(self, lang_code: str):
        if lang_code not in self._pipelines:
            from kokoro import KPipeline

            model = self._ensure_model()
            logger.info("Initializing Kokoro pipeline for lang_code='%s'...", lang_code)
            self._pipelines[lang_code] = KPipeline(
                lang_code=lang_code,
                repo_id=self.repo_id,
                model=model,
            )
        return self._pipelines[lang_code]

    def resolve_voice(self, voice: str | None) -> str:
        """Resolve voice ID or OpenAI alias to a valid Kokoro voice ID."""
        if not voice:
            return DEFAULT_VOICE
        v = voice.strip()
        if v in OPENAI_VOICE_ALIASES:
            return OPENAI_VOICE_ALIASES[v]
        if v in KOKORO_VOICE_MAP:
            return v
        raise ValueError(f"Unknown Kokoro voice '{voice}'. Call GET /v1/voices to inspect available voices.")

    def synthesize(
        self,
        text: str,
        voice: str = DEFAULT_VOICE,
        speed: float = 1.0,
    ) -> Tuple[np.ndarray, int]:
        """Synthesize text to a 24 kHz mono float32 numpy waveform."""
        clean_text = (text or "").strip()
        if not clean_text:
            raise ValueError("Input text must not be empty.")

        resolved_voice = self.resolve_voice(voice)
        voice_meta = KOKORO_VOICE_MAP[resolved_voice]
        clamped_speed = float(np.clip(speed, 0.5, 2.0))

        with self._lock:
            pipeline = self._get_pipeline(voice_meta.lang_code)
            chunks: List[np.ndarray] = []
            for _, _, audio in pipeline(
                clean_text,
                voice=resolved_voice,
                speed=clamped_speed,
                split_pattern=r"\n+",
            ):
                if audio is not None:
                    if hasattr(audio, "detach"):
                        audio_np = audio.detach().cpu().numpy()
                    else:
                        audio_np = np.asarray(audio, dtype=np.float32)
                    if audio_np.size > 0:
                        chunks.append(audio_np.astype(np.float32))

        if not chunks:
            raise RuntimeError("Kokoro-82M returned empty audio for the provided input.")

        waveform = np.concatenate(chunks, axis=0)
        return waveform, KOKORO_SAMPLE_RATE