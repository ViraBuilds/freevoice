"""Qwen3-TTS 0.6B 3-second zero-shot voice cloning module (Apache 2.0)."""

from __future__ import annotations

import json
import logging
import re
import shutil
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf

from freevoice.audio import load_reference_audio
from freevoice.config import CLONES_DIR, QWEN_CLONE_REPO_ID, resolve_device

logger = logging.getLogger(__name__)


@dataclass
class ClonedVoiceProfile:
    id: str
    name: str
    ref_audio_path: str
    ref_text: str
    language: str = "English"
    duration_seconds: float = 0.0


class QwenVoiceCloner:
    """Manages saved 3-second voice samples and Qwen3-TTS-12Hz-0.6B-Base inference."""

    def __init__(
        self,
        device: str = "auto",
        repo_id: str = QWEN_CLONE_REPO_ID,
        clones_dir: Path = CLONES_DIR,
    ) -> None:
        self.device = resolve_device(device)
        self.repo_id = repo_id
        self.clones_dir = Path(clones_dir)
        self.clones_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self):
        if self._model is None:
            import torch
            from qwen_tts import Qwen3TTSModel

            dtype = torch.bfloat16 if self.device in {"cuda", "mps"} else torch.float32
            device_map = "cuda:0" if self.device == "cuda" else self.device
            logger.info("Loading Qwen3-TTS 0.6B cloning model (%s) on %s...", self.repo_id, device_map)
            self._model = Qwen3TTSModel.from_pretrained(
                self.repo_id,
                device_map=device_map,
                dtype=dtype,
            )
        return self._model

    @staticmethod
    def sanitize_slug(name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower()).strip("_")
        return slug or "custom_voice"

    def list_profiles(self) -> List[ClonedVoiceProfile]:
        profiles: List[ClonedVoiceProfile] = []
        if not self.clones_dir.exists():
            return profiles
        for meta_file in sorted(self.clones_dir.glob("*/profile.json")):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                profiles.append(ClonedVoiceProfile(**data))
            except Exception as exc:
                logger.warning("Skipping corrupt clone profile %s: %s", meta_file, exc)
        return profiles

    def get_profile(self, voice_id: str) -> Optional[ClonedVoiceProfile]:
        clean_id = voice_id.removeprefix("clone:")
        meta_file = self.clones_dir / clean_id / "profile.json"
        if not meta_file.exists():
            return None
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        return ClonedVoiceProfile(**data)

    def save_profile(
        self,
        name: str,
        source_audio_path: str | Path,
        ref_text: str = "",
        language: str = "English",
    ) -> ClonedVoiceProfile:
        """Validate, normalize, and store a 3-second reference clip for voice cloning."""
        wav, sr = load_reference_audio(source_audio_path)
        duration = len(wav) / float(sr)
        if duration < 1.5:
            raise ValueError(
                f"Reference audio is too short ({duration:.2f}s). Provide at least 2-3 seconds of clean speech."
            )
        # Trim overly long clips to 15 seconds to keep prompt encoding fast
        if duration > 15.0:
            wav = wav[: int(15.0 * sr)]
            duration = 15.0

        slug = self.sanitize_slug(name)
        voice_id = f"clone:{slug}"
        profile_dir = self.clones_dir / slug
        profile_dir.mkdir(parents=True, exist_ok=True)

        stored_wav_path = profile_dir / "reference.wav"
        sf.write(str(stored_wav_path), wav, sr, subtype="PCM_16")

        profile = ClonedVoiceProfile(
            id=voice_id,
            name=name.strip() or slug,
            ref_audio_path=str(stored_wav_path),
            ref_text=ref_text.strip(),
            language=language.strip() or "English",
            duration_seconds=round(duration, 2),
        )
        (profile_dir / "profile.json").write_text(
            json.dumps(asdict(profile), indent=2),
            encoding="utf-8",
        )
        return profile

    def delete_profile(self, voice_id: str) -> bool:
        clean_id = voice_id.removeprefix("clone:")
        profile_dir = self.clones_dir / clean_id
        if not profile_dir.exists():
            return False
        shutil.rmtree(profile_dir)
        return True

    def synthesize_from_reference(
        self,
        text: str,
        ref_audio_path: str | Path,
        ref_text: str = "",
        language: str = "English",
    ) -> Tuple[np.ndarray, int]:
        """Generate speech cloned from a reference audio file."""
        clean_text = (text or "").strip()
        if not clean_text:
            raise ValueError("Input text must not be empty.")

        wav, sr = load_reference_audio(ref_audio_path)
        clean_ref_text = (ref_text or "").strip()
        x_vector_only = len(clean_ref_text) == 0

        with self._lock:
            model = self._ensure_model()
            kwargs = {
                "text": clean_text,
                "language": language or "English",
                "ref_audio": (wav, sr),
                "x_vector_only_mode": x_vector_only,
            }
            if not x_vector_only:
                kwargs["ref_text"] = clean_ref_text

            wavs, out_sr = model.generate_voice_clone(**kwargs)

        if not wavs or len(wavs) == 0:
            raise RuntimeError("Qwen3-TTS returned empty audio during voice cloning.")

        out_wav = np.asarray(wavs[0], dtype=np.float32)
        return out_wav, int(out_sr)

    def synthesize_profile(
        self,
        text: str,
        voice_id: str,
        language: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        """Generate speech using a previously saved cloned voice profile."""
        profile = self.get_profile(voice_id)
        if profile is None:
            raise ValueError(f"Cloned voice profile '{voice_id}' not found.")

        return self.synthesize_from_reference(
            text=text,
            ref_audio_path=profile.ref_audio_path,
            ref_text=profile.ref_text,
            language=language or profile.language,
        )