# wyoming-audio8-tts

Wyoming Protocol server for **[Audio8-TTS-Realistic-Air](https://huggingface.co/Edge0/Audio8-TTS-Realistic-Air)** — a compact 0.6B zero-shot text-to-speech model.

Easy integration with **Home Assistant**.

> **Note**: This is a CPU-only build focused on Cantonese (`yue`). Inference is relatively slow.

## Features

- Zero-shot voice cloning (just provide a reference `.wav`)
- Optimized for **Cantonese (粵語)**
- Pure CPU (no GPU required)
- Wyoming Protocol compatible
- Simple single-voice design
- Automatic model download on first run

## Quick Start

### 1. Prepare a reference voice (recommended)

```bash
mkdir -p voices
# Put a clean 5–15 second Cantonese recording
cp /path/to/your/sample.wav voices/reference.wav
```

### 2. Run with Docker

**Option A – Pull from Docker Hub** (recommended)

```bash
docker run -d \
  --name wyoming-audio8 \
  -p 10200:10200 \
  -v ./voices:/voices \
  wereling1992/wyoming-audio8-tts:latest
```

**Option B – Build locally**

```bash
git clone https://github.com/wereling1992/wyoming-audio8-tts.git
cd wyoming-audio8-tts
docker compose up -d --build
```

### 3. Add to Home Assistant

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Wyoming Protocol**
3. Enter:
   - Host: IP of the machine running the container
   - Port: `10200`
4. In **Settings → Voice assistants**, select the `audio8` / `cantonese` voice

## Docker Compose Example

```yaml
services:
  wyoming-audio8:
    image: wereling1992/wyoming-audio8-tts:latest
    container_name: wyoming-audio8
    restart: unless-stopped
    ports:
      - "10200:10200"
    volumes:
      - ./voices:/voices
      - huggingface_cache:/root/.cache/huggingface
    environment:
      - LANGUAGE=yue
      - VOICE_NAME=cantonese
      - REFERENCE_AUDIO=/voices/reference.wav
      - REFERENCE_TEXT=          # optional but recommended
      - DEVICE=cpu

volumes:
  huggingface_cache:
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_ID` | `Edge0/Audio8-TTS-Realistic-Air` | Hugging Face model ID |
| `LANGUAGE` | `yue` | Language code (Cantonese) |
| `VOICE_NAME` | `cantonese` | Voice name shown in Home Assistant |
| `REFERENCE_AUDIO` | `/voices/reference.wav` | Path to reference audio inside container |
| `REFERENCE_TEXT` | *(empty)* | Exact transcript of the reference audio (improves cloning quality) |
| `DEVICE` | `cpu` | Fixed to CPU in this build |
| `URI` | `tcp://0.0.0.0:10200` | Wyoming server listen address |

## Tips for better voice cloning

- Use a clean 5–15 second recording
- Single speaker, no background music/noise
- Provide the exact transcript via `REFERENCE_TEXT`
- Avoid heavy reverb or extreme emotion in the reference

## Limitations

- CPU-only → relatively slow (several seconds per sentence)
- Single voice only (this is the minimal version)
- Model is downloaded on first start (~2.5 GB)

## Future ideas

- Multi-voice support (scan `/voices` directory)
- GPU version
- Streaming support
- SGLang Omni acceleration

## Credits

- Model: [Audio8-TTS-Realistic-Air](https://huggingface.co/Edge0/Audio8-TTS-Realistic-Air) by Edge0
- Wyoming Protocol: [OHF-Voice/wyoming](https://github.com/OHF-Voice/wyoming)

## License

This project is licensed under the **Apache License 2.0**.  
The underlying model is also released under Apache-2.0.
