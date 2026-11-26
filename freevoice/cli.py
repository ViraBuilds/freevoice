"""Command-line interface for FreeVoice (single TTS, voice cloning, batch mode, and server)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import uvicorn

from freevoice import __version__
from freevoice.audio import encode_audio
from freevoice.config import DEFAULT_DEVICE, DEFAULT_HOST, DEFAULT_PORT, DEFAULT_VOICE
from freevoice.registry import VoiceRegistry
from freevoice.server import create_app


def _load_batch_entries(batch_path: Path, default_voice: str, default_speed: float) -> List[Dict[str, Any]]:
    if not batch_path.exists():
        raise FileNotFoundError(f"Batch file not found: {batch_path}")

    raw_text = batch_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        raise ValueError("Batch file is empty.")

    if batch_path.suffix.lower() == ".json" or raw_text.startswith("["):
        parsed = json.loads(raw_text)
        if not isinstance(parsed, list):
            raise ValueError("JSON batch file must contain a top-level list of objects or strings.")
        entries: List[Dict[str, Any]] = []
        for idx, entry in enumerate(parsed, start=1):
            if isinstance(entry, str):
                entries.append(
                    {
                        "filename": f"line_{idx:03d}.mp3",
                        "text": entry,
                        "voice": default_voice,
                        "speed": default_speed,
                    }
                )
            elif isinstance(entry, dict):
                if "text" not in entry or not str(entry["text"]).strip():
                    raise ValueError(f"Batch item #{idx} is missing a non-empty 'text' field.")
                entries.append(
                    {
                        "filename": entry.get("filename") or f"line_{idx:03d}.mp3",
                        "text": str(entry["text"]).strip(),
                        "voice": entry.get("voice") or default_voice,
                        "speed": float(entry.get("speed", default_speed)),
                    }
                )
            else:
                raise ValueError(f"Unsupported item type at index {idx} in JSON batch file.")
        return entries

    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return [
        {
            "filename": f"line_{idx:03d}.mp3",
            "text": line,
            "voice": default_voice,
            "speed": default_speed,
        }
        for idx, line in enumerate(lines, start=1)
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="freevoice",
        description="FreeVoice — Free, unlimited local TTS, 3-second voice cloning, and OpenAI-compatible server.",
    )
    parser.add_argument("--version", action="version", version=f"freevoice {__version__}")

    # Direct synthesis flags (supports `freevoice "Hello world" --voice af_heart -o hello.mp3`)
    parser.add_argument("text", nargs="?", help="Text to synthesize, or 'serve' / 'voices' subcommand")
    parser.add_argument("-v", "--voice", default=DEFAULT_VOICE, help=f"Voice ID (default: {DEFAULT_VOICE})")
    parser.add_argument("-o", "--output", default="output.mp3", help="Output audio file path (default: output.mp3)")
    parser.add_argument("-f", "--format", default=None, help="Audio format: mp3, wav, ogg, flac (inferred from -o if omitted)")
    parser.add_argument("--speed", type=float, default=1.0, help="Speaking speed multiplier (0.5 to 2.0)")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="Compute device: auto, cpu, cuda, mps")

    # Voice cloning flags
    parser.add_argument("--clone-audio", help="Path to a 3-second reference audio clip for zero-shot voice cloning")
    parser.add_argument("--clone-text", default="", help="Transcript of the reference audio clip")
    parser.add_argument("--clone-lang", default="English", help="Language of the reference/target speech")
    parser.add_argument("--save-clone", help="Optional name to save the cloned voice for future reuse")

    # Batch synthesis flags
    parser.add_argument("--batch", help="Path to a .txt (one line per clip) or .json batch script")
    parser.add_argument("--out-dir", default="output_clips", help="Output directory for --batch mode (default: output_clips)")

    # Web server flags (when positional argument is `serve`)
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Server host when running `freevoice serve` (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server port when running `freevoice serve` (default: {DEFAULT_PORT})")

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Subcommand: `freevoice serve`
    if args.text == "serve":
        app = create_app(device=args.device)
        uvicorn.run(app, host=args.host, port=args.port)
        return

    registry = VoiceRegistry(device=args.device)

    # Subcommand: `freevoice voices`
    if args.text == "voices":
        for v in registry.list_all_voices():
            print(f"{v['id']:16s} | {v['language']:18s} | {v['gender']:6s} | {v['description']}")
        return

    # Mode: Batch synthesis (`freevoice --batch script.txt --out-dir ./clips`)
    if args.batch:
        batch_path = Path(args.batch)
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        entries = _load_batch_entries(batch_path, default_voice=args.voice, default_speed=args.speed)

        print(f"Synthesizing {len(entries)} clips into {out_dir}...")
        for idx, item in enumerate(entries, start=1):
            target_path = out_dir / item["filename"]
            ext = (args.format or target_path.suffix.lstrip(".") or "mp3").lower()
            target_path = target_path.with_suffix(f".{ext}")

            waveform, sr = registry.synthesize(
                text=item["text"],
                voice=item["voice"],
                speed=item["speed"],
            )
            audio_bytes, _ = encode_audio(waveform, sr, response_format=ext)
            target_path.write_bytes(audio_bytes)
            print(f"[{idx}/{len(entries)}] Saved {target_path} ({item['voice']})")
        return

    # Mode: Single text synthesis (Kokoro or 3-second Qwen3-TTS clone)
    if not args.text:
        parser.print_help()
        sys.exit(1)

    out_path = Path(args.output)
    fmt = (args.format or out_path.suffix.lstrip(".") or "mp3").lower()
    out_path = out_path.with_suffix(f".{fmt}")

    if args.clone_audio:
        if args.save_clone:
            profile = registry.cloner.save_profile(
                name=args.save_clone,
                source_audio_path=args.clone_audio,
                ref_text=args.clone_text,
                language=args.clone_lang,
            )
            print(f"Saved cloned voice profile: {profile.id}")
        waveform, sr = registry.cloner.synthesize_from_reference(
            text=args.text,
            ref_audio_path=args.clone_audio,
            ref_text=args.clone_text,
            language=args.clone_lang,
        )
    else:
        waveform, sr = registry.synthesize(
            text=args.text,
            voice=args.voice,
            speed=args.speed,
            language=args.clone_lang,
        )

    audio_bytes, _ = encode_audio(waveform, sr, response_format=fmt)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio_bytes)
    print(f"Wrote {out_path} ({len(audio_bytes) / 1024:.1f} KB)")