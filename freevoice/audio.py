"""Audio encoding, format conversion, and normalization utilities."""

from __future__ import annotations

import io
import shutil
from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf
from pydub import AudioSegment

SUPPORTED_FORMATS = {"mp3", "wav", "ogg", "flac"}

MIME_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
}


def ensure_ffmpeg_available() -> None:
    """Verify ffmpeg binary is present on PATH before MP3/OGG encoding."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg was not found on your system PATH. "
            "Install FFmpeg (e.g., `apt install ffmpeg` or `brew install ffmpeg`) to export MP3 files."
        )


def normalize_waveform(audio: np.ndarray) -> np.ndarray:
    """Convert waveform to mono float32 in [-1.0, 1.0]."""
    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim > 1:
        arr = np.mean(arr, axis=-1)
    peak = float(np.max(np.abs(arr))) if arr.size > 0 else 0.0
    if peak > 1.0:
        arr = arr / peak
    return arr


def encode_audio(
    waveform: np.ndarray,
    sample_rate: int,
    response_format: str = "mp3",
    bitrate: str = "192k",
) -> Tuple[bytes, str]:
    """Encode a float32 numpy waveform into MP3, WAV, OGG, or FLAC bytes."""
    fmt = response_format.lower().strip()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported audio format '{response_format}'. Supported: {sorted(SUPPORTED_FORMATS)}")

    wav_float = normalize_waveform(waveform)

    if fmt == "wav":
        buf = io.BytesIO()
        sf.write(buf, wav_float, sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue(), MIME_TYPES["wav"]

    if fmt == "flac":
        buf = io.BytesIO()
        sf.write(buf, wav_float, sample_rate, format="FLAC")
        return buf.getvalue(), MIME_TYPES["flac"]

    ensure_ffmpeg_available()

    wav_buf = io.BytesIO()
    sf.write(wav_buf, wav_float, sample_rate, format="WAV", subtype="PCM_16")
    wav_buf.seek(0)

    segment = AudioSegment.from_wav(wav_buf)
    out_buf = io.BytesIO()
    if fmt == "mp3":
        segment.export(out_buf, format="mp3", bitrate=bitrate)
    elif fmt == "ogg":
        segment.export(out_buf, format="ogg")

    return out_buf.getvalue(), MIME_TYPES[fmt]


def load_reference_audio(file_path: str | Path) -> Tuple[np.ndarray, int]:
    """Load any common audio file (WAV, MP3, M4A, OGG, FLAC) as mono float32 + sample rate."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Reference audio not found: {path}")

    try:
        data, sr = sf.read(str(path), always_2d=False)
        return normalize_waveform(data), int(sr)
    except Exception:
        ensure_ffmpeg_available()
        seg = AudioSegment.from_file(str(path))
        seg = seg.set_channels(1)
        sr = seg.frame_rate
        samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
        max_val = float(1 << (8 * seg.sample_width - 1))
        return normalize_waveform(samples / max_val), int(sr)