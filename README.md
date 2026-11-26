# FreeVoice

**Free, unlimited, self-hosted AI voiceover studio, CLI, and OpenAI-compatible TTS API.**

FreeVoice gives you local text-to-speech synthesis and 3-second zero-shot voice cloning with no account, no usage cap, and commercial use permitted under open-source licenses.

---

## Why FreeVoice vs. ElevenLabs Free Tier

| Feature | ElevenLabs (Free Plan) | FreeVoice (Self-Hosted) |
| :--- | :--- | :--- |
| **Monthly Allowance** | ~10,000 credits/month (~10 minutes of audio) | **Unlimited** (bound only by your hardware) |
| **Commercial Licence** | **Not included** on Free tier (paid plans start at $6/month) | **Allowed** (MIT code + Apache 2.0 model weights) |
| **Account / API Key** | Required | **None** |
| **Built-in Voices** | Limited library on free tier | **54 voices in 8 languages** (Kokoro-82M) |
| **Voice Cloning** | Paid tiers only | **Included** via Qwen3-TTS 0.6B (3-second reference clip) |
| **OpenAI SDK Compatibility** | Proprietary API | **Drop-in `/v1/audio/speech` endpoint** |

---

## Architecture & Models

1. **Main Voice Engine — [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (Apache 2.0):**
   82-million-parameter TTS model supporting 54 preset voices in 8 languages across 9 regional variants: American English, British English, Spanish, French, Hindi, Italian, Japanese, Brazilian Portuguese, and Mandarin Chinese. Fast enough to run comfortably on a modern CPU.
2. **3-Second Voice Cloning — [Qwen3-TTS-12Hz-0.6B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base) (Apache 2.0):**
   Zero-shot voice cloning from a clean ~3-second audio sample (with optional reference transcript for higher fidelity).
3. **Three Interfaces:**
   - **Web Studio:** Single-page browser UI with single-clip synthesis, voice previews, MP3 download, 3-second voice cloning upload, and multi-line batch export (ZIP of MP3s).
   - **CLI (`freevoice`):** Generate single MP3s or process `.txt` / `.json` batch scripts from the terminal.
   - **OpenAI-Compatible API:** `POST /v1/audio/speech` and `GET /v1/voices` so existing OpenAI SDK scripts work by changing `base_url`.

---

## Honest Limitations

Before deploying FreeVoice in production, keep these practical trade-offs in mind:

- **Expressiveness vs. ElevenLabs:** Kokoro-82M is remarkably clear and natural for narration, tutorials, articles, and dialogue, but it lacks fine-grained emotional directing (e.g., whispering, shouting, crying) compared to ElevenLabs' flagship models.
- **CPU vs. GPU Speed:** Kokoro-82M runs fast on CPU (often faster than real-time on modern multi-core CPUs). **Qwen3-TTS 0.6B** runs on CPU as well, but voice cloning is noticeably slower without an NVIDIA CUDA or Apple Silicon (MPS) GPU.
- **Voice Cloning Input Quality:** Qwen3-TTS 0.6B needs a **clean 3-to-10 second reference clip**—single speaker, minimal room echo, no background music, and an accurate transcript (`ref_text`) for best results. Noisy samples degrade speaker similarity.
- **First-Run Model Downloads:** Model weights are downloaded automatically from Hugging Face on first use (~350 MB for Kokoro-82M and ~1.2 GB for Qwen3-TTS 0.6B) and cached locally thereafter.
- **Language Extras:** English works out of the box. For Japanese (`j*`) or Mandarin (`z*`) Kokoro voices, install `misaki[ja]` / `misaki[zh]`, and ensure `espeak-ng` is installed on your OS for Spanish, French, Hindi, Italian, and Portuguese fallback G2P.

---

## Installation

### 1. System Prerequisites

- **Python 3.10 – 3.12**
- **FFmpeg** (required for MP3 encoding via `pydub`/FFmpeg)
  - Ubuntu/Debian: `sudo apt update && sudo apt install -y ffmpeg espeak-ng`
  - macOS: `brew install ffmpeg espeak-ng`
  - Windows: `winget install Gyan.FFmpeg`

### 2. Install FreeVoice

```bash
git clone https://github.com/ViraBuilds/freevoice.git
cd freevoice

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -e .
```

---

## Usage

### Web Studio

```bash
freevoice serve
```

Then open http://127.0.0.1:8000 in your browser. Type text, pick a voice, preview it, and download the MP3. The studio also supports uploading a 3-second reference clip to clone a voice, and batch mode (one line per clip) that exports a ZIP of MP3s.

### CLI

```bash
# List all 54 built-in voices (plus any voices you cloned)
freevoice voices

# One clip, default voice (af_heart)
freevoice "Hello world" -o hello.mp3

# Pick a voice, speed, and format
freevoice "Hello world" --voice bm_george --speed 0.95 -f wav -o hello.wav

# Clone a voice from a 3-second sample, one-off
freevoice "Hello from my cloned voice" --clone-audio ref.wav --clone-text "Hello, this is my voice" -o cloned.mp3

# Save the clone for reuse, then use it by ID
freevoice "Hello again" --clone-audio ref.wav --clone-text "Hello, this is my voice" --save-clone my_voice
freevoice "Hello again" --voice clone:my_voice -o again.mp3

# Batch mode: one line per clip (.txt) or a JSON list (see examples/)
freevoice --batch examples/batch_script.txt --out-dir ./clips
freevoice --batch examples/batch_script.json --out-dir ./clips
```

### API Server

```bash
freevoice serve --host 127.0.0.1 --port 8000
```

Endpoints:

| Method & Path | What it does |
| :--- | :--- |
| `GET /` | Web Studio UI |
| `GET /health` | `{"status": "ok", "version": ..., "device": ...}` |
| `GET /v1/voices` | List all voices (built-in + cloned) |
| `POST /v1/audio/speech` | OpenAI-compatible speech synthesis |
| `POST /v1/voices/clone` | Upload a 3-second sample, save a cloned voice |
| `DELETE /v1/voices/clone/{slug}` | Delete a cloned voice |
| `POST /v1/audio/batch` | Synthesize many clips at once, returns a ZIP |

`POST /v1/audio/speech` body (JSON):

```json
{
  "model": "kokoro-82m",
  "input": "Hello from FreeVoice!",
  "voice": "af_heart",
  "response_format": "mp3",
  "speed": 1.0
}
```

`voice` accepts a Kokoro voice ID (e.g. `af_heart`, `bm_george`), an OpenAI alias (`alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`), or a cloned voice (`clone:my_voice`). `response_format` is `mp3`, `wav`, `ogg`, or `flac`. `speed` is 0.5–2.0.

```bash
curl -X POST http://127.0.0.1:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model": "kokoro-82m", "input": "Hello from FreeVoice!", "voice": "af_heart", "response_format": "mp3"}' \
  --output hello.mp3
```

It is a drop-in for the OpenAI Python SDK — just point `base_url` at your server (see `examples/openai_client_example.py`):

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="not-needed")

with client.audio.speech.with_streaming_response.create(
    model="kokoro-82m",
    voice="af_heart",
    input="Hello from FreeVoice!",
    response_format="mp3",
) as response:
    response.stream_to_file("hello.mp3")
```

### Configuration

All settings have environment-variable overrides:

| Variable | Default | Meaning |
| :--- | :--- | :--- |
| `FREEVOICE_HOST` | `127.0.0.1` | Server bind host |
| `FREEVOICE_PORT` | `8000` | Server port |
| `FREEVOICE_DEVICE` | `auto` | `auto`, `cpu`, `cuda`, or `mps` |
| `FREEVOICE_DATA_DIR` | `~/.freevoice` | Where cloned voices are stored |
| `FREEVOICE_KOKORO_REPO` | `hexgrad/Kokoro-82M` | Kokoro model repo on Hugging Face |
| `FREEVOICE_QWEN_REPO` | `Qwen/Qwen3-TTS-12Hz-0.6B-Base` | Qwen cloning model repo |

---

## License

- **FreeVoice code:** MIT — see [LICENSE](LICENSE).
- **Kokoro-82M** and **Qwen3-TTS-12Hz-0.6B-Base** model weights: Apache 2.0.

---

## Donate

FreeVoice is free and unlimited — no account, no credits, no paywall. If it saves you a subscription, consider supporting its development:

- **TON:** `UQAdlJHWw-2wkhmYEQDVb-bfsNdwKEFfF5T4MtuBSw5GJrdD`
- **EVM (Ethereum / BSC / Polygon):** `0xf38cAF0757B611fD625cA2c392b24D79025D62c9`

Thank you — every donation keeps the project free for everyone.
