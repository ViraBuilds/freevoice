"""Configuration and voice catalog definitions for FreeVoice."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

DEFAULT_HOST = os.getenv("FREEVOICE_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("FREEVOICE_PORT", "8000"))
DEFAULT_DEVICE = os.getenv("FREEVOICE_DEVICE", "auto")
DATA_DIR = Path(os.getenv("FREEVOICE_DATA_DIR", Path.home() / ".freevoice")).expanduser()
CLONES_DIR = DATA_DIR / "clones"

KOKORO_REPO_ID = os.getenv("FREEVOICE_KOKORO_REPO", "hexgrad/Kokoro-82M")
QWEN_CLONE_REPO_ID = os.getenv("FREEVOICE_QWEN_REPO", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")

DEFAULT_VOICE = "af_heart"


@dataclass(frozen=True)
class VoiceInfo:
    id: str
    name: str
    language: str
    lang_code: str
    gender: str
    provider: str = "kokoro"
    description: str = ""


# Complete 54-voice catalog for Kokoro-82M v1.0 across 8 languages
KOKORO_VOICES: List[VoiceInfo] = [
    # American English (lang_code = "a") — 11 Female, 9 Male
    VoiceInfo("af_heart", "Heart", "American English", "a", "Female", description="Warm, expressive flagship voice"),
    VoiceInfo("af_alloy", "Alloy", "American English", "a", "Female", description="Balanced, neutral narration"),
    VoiceInfo("af_aoede", "Aoede", "American English", "a", "Female", description="Clear, melodic tone"),
    VoiceInfo("af_bella", "Bella", "American English", "a", "Female", description="Natural, conversational female voice"),
    VoiceInfo("af_jessica", "Jessica", "American English", "a", "Female", description="Engaging, upbeat tone"),
    VoiceInfo("af_kore", "Kore", "American English", "a", "Female", description="Bright and energetic"),
    VoiceInfo("af_nicole", "Nicole", "American English", "a", "Female", description="Soft, calm delivery"),
    VoiceInfo("af_nova", "Nova", "American English", "a", "Female", description="Crisp, modern voice"),
    VoiceInfo("af_river", "River", "American English", "a", "Female", description="Smooth, steady cadence"),
    VoiceInfo("af_sarah", "Sarah", "American English", "a", "Female", description="Friendly, articulate"),
    VoiceInfo("af_sky", "Sky", "American English", "a", "Female", description="Light, airy delivery"),
    VoiceInfo("am_adam", "Adam", "American English", "a", "Male", description="Deep, steady male narration"),
    VoiceInfo("am_echo", "Echo", "American English", "a", "Male", description="Resonant, clear male voice"),
    VoiceInfo("am_eric", "Eric", "American English", "a", "Male", description="Conversational American male"),
    VoiceInfo("am_fenrir", "Fenrir", "American English", "a", "Male", description="Rich, authoritative tone"),
    VoiceInfo("am_liam", "Liam", "American English", "a", "Male", description="Warm, approachable male voice"),
    VoiceInfo("am_michael", "Michael", "American English", "a", "Male", description="Versatile, clear male voice"),
    VoiceInfo("am_onyx", "Onyx", "American English", "a", "Male", description="Low-pitched, grounded tone"),
    VoiceInfo("am_puck", "Puck", "American English", "a", "Male", description="Lively, expressive delivery"),
    VoiceInfo("am_santa", "Santa", "American English", "a", "Male", description="Jovial, theatrical character voice"),
    # British English (lang_code = "b") — 4 Female, 4 Male
    VoiceInfo("bf_alice", "Alice", "British English", "b", "Female", description="Refined British female voice"),
    VoiceInfo("bf_emma", "Emma", "British English", "b", "Female", description="Warm, professional British voice"),
    VoiceInfo("bf_isabella", "Isabella", "British English", "b", "Female", description="Sophisticated, articulate"),
    VoiceInfo("bf_lily", "Lily", "British English", "b", "Female", description="Gentle British narration"),
    VoiceInfo("bm_daniel", "Daniel", "British English", "b", "Male", description="Clear British male voice"),
    VoiceInfo("bm_fable", "Fable", "British English", "b", "Male", description="Storytelling British male tone"),
    VoiceInfo("bm_george", "George", "British English", "b", "Male", description="Classic British narration"),
    VoiceInfo("bm_lewis", "Lewis", "British English", "b", "Male", description="Measured, formal British male"),
    # Spanish (lang_code = "e") — 1 Female, 2 Male
    VoiceInfo("ef_dora", "Dora", "Spanish", "e", "Female", description="Spanish female voice"),
    VoiceInfo("em_alex", "Alex", "Spanish", "e", "Male", description="Spanish male voice"),
    VoiceInfo("em_santa", "Santa (ES)", "Spanish", "e", "Male", description="Spanish character male voice"),
    # French (lang_code = "f") — 1 Female
    VoiceInfo("ff_siwis", "Siwis", "French", "f", "Female", description="French female voice"),
    # Hindi (lang_code = "h") — 2 Female, 2 Male
    VoiceInfo("hf_alpha", "Alpha", "Hindi", "h", "Female", description="Hindi female voice"),
    VoiceInfo("hf_beta", "Beta", "Hindi", "h", "Female", description="Hindi female voice"),
    VoiceInfo("hm_omega", "Omega", "Hindi", "h", "Male", description="Hindi male voice"),
    VoiceInfo("hm_psi", "Psi", "Hindi", "h", "Male", description="Hindi male voice"),
    # Italian (lang_code = "i") — 1 Female, 1 Male
    VoiceInfo("if_sara", "Sara", "Italian", "i", "Female", description="Italian female voice"),
    VoiceInfo("im_nicola", "Nicola", "Italian", "i", "Male", description="Italian male voice"),
    # Japanese (lang_code = "j") — 4 Female, 1 Male
    VoiceInfo("jf_alpha", "Alpha (JA)", "Japanese", "j", "Female", description="Japanese female voice"),
    VoiceInfo("jf_gongitsune", "Gongitsune", "Japanese", "j", "Female", description="Japanese narrative female voice"),
    VoiceInfo("jf_nezumi", "Nezumi", "Japanese", "j", "Female", description="Japanese female voice"),
    VoiceInfo("jf_tebukuro", "Tebukuro", "Japanese", "j", "Female", description="Japanese female voice"),
    VoiceInfo("jm_kumo", "Kumo", "Japanese", "j", "Male", description="Japanese male voice"),
    # Brazilian Portuguese (lang_code = "p") — 1 Female, 2 Male
    VoiceInfo("pf_dora", "Dora (PT)", "Portuguese", "p", "Female", description="Brazilian Portuguese female voice"),
    VoiceInfo("pm_alex", "Alex (PT)", "Portuguese", "p", "Male", description="Brazilian Portuguese male voice"),
    VoiceInfo("pm_santa", "Santa (PT)", "Portuguese", "p", "Male", description="Brazilian Portuguese character voice"),
    # Mandarin Chinese (lang_code = "z") — 4 Female, 4 Male
    VoiceInfo("zf_xiaobei", "Xiaobei", "Mandarin Chinese", "z", "Female", description="Mandarin female voice"),
    VoiceInfo("zf_xiaoni", "Xiaoni", "Mandarin Chinese", "z", "Female", description="Mandarin female voice"),
    VoiceInfo("zf_xiaoxiao", "Xiaoxiao", "Mandarin Chinese", "z", "Female", description="Mandarin female voice"),
    VoiceInfo("zf_xiaoyi", "Xiaoyi", "Mandarin Chinese", "z", "Female", description="Mandarin female voice"),
    VoiceInfo("zm_yunjian", "Yunjian", "Mandarin Chinese", "z", "Male", description="Mandarin male voice"),
    VoiceInfo("zm_yunxi", "Yunxi", "Mandarin Chinese", "z", "Male", description="Mandarin male voice"),
    VoiceInfo("zm_yunxia", "Yunxia", "Mandarin Chinese", "z", "Male", description="Mandarin male voice"),
    VoiceInfo("zm_yunyang", "Yunyang", "Mandarin Chinese", "z", "Male", description="Mandarin male voice"),
]

KOKORO_VOICE_MAP: Dict[str, VoiceInfo] = {v.id: v for v in KOKORO_VOICES}

# OpenAI voice alias compatibility so existing OpenAI scripts work unchanged
OPENAI_VOICE_ALIASES: Dict[str, str] = {
    "alloy": "af_alloy",
    "echo": "am_echo",
    "fable": "bm_fable",
    "onyx": "am_onyx",
    "nova": "af_nova",
    "shimmer": "af_heart",
}

LANGUAGE_NAMES: Dict[str, str] = {
    "a": "English",
    "b": "English",
    "e": "Spanish",
    "f": "French",
    "h": "Hindi",
    "i": "Italian",
    "j": "Japanese",
    "p": "Portuguese",
    "z": "Chinese",
}


def resolve_device(preferred: str = DEFAULT_DEVICE) -> str:
    """Resolve 'auto' to cuda, mps, or cpu."""
    if preferred and preferred.lower() != "auto":
        return preferred
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"