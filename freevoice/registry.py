"""Unified TTS router combining Kokoro-82M voices and Qwen3-TTS 0.6B cloned voices."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from freevoice.config import DEFAULT_VOICE, KOKORO_VOICES, OPENAI_VOICE_ALIASES
from freevoice.kokoro_engine import KokoroEngine
from freevoice.qwen_cloner import QwenVoiceCloner


class VoiceRegistry:
    """Single entry point used by both the CLI and FastAPI server."""

    def __init__(self, device: str = "auto") -> None:
        self.kokoro = KokoroEngine(device=device)
        self.cloner = QwenVoiceCloner(device=device)

    def list_all_voices(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        for profile in self.cloner.list_profiles():
            items.append(
                {
                    "id": profile.id,
                    "name": f"{profile.name} (Cloned)",
                    "language": profile.language,
                    "lang_code": "clone",
                    "gender": "Cloned",
                    "provider": "qwen3-tts-0.6b",
                    "description": f"3s cloned voice ({profile.duration_seconds}s sample)",
                }
            )

        for v in KOKORO_VOICES:
            items.append(
                {
                    "id": v.id,
                    "name": v.name,
                    "language": v.language,
                    "lang_code": v.lang_code,
                    "gender": v.gender,
                    "provider": "kokoro-82m",
                    "description": v.description,
                }
            )

        return items

    def synthesize(
        self,
        text: str,
        voice: str = DEFAULT_VOICE,
        speed: float = 1.0,
        language: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        selected = (voice or DEFAULT_VOICE).strip()
        if selected.startswith("clone:"):
            return self.cloner.synthesize_profile(
                text=text,
                voice_id=selected,
                language=language,
            )

        resolved = OPENAI_VOICE_ALIASES.get(selected, selected)
        return self.kokoro.synthesize(
            text=text,
            voice=resolved,
            speed=speed,
        )