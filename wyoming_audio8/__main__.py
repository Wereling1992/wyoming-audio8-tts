#!/usr/bin/env python3
"""Wyoming protocol server for Audio8-TTS-Realistic-Air (CPU, simple version)."""

import argparse
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import torch
from transformers import AutoModel, AutoProcessor

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Attribution, Describe, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.tts import Synthesize

from . import __version__

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model loader (singleton)
# ---------------------------------------------------------------------------

_model = None
_processor = None
_sample_rate = 44100


def load_model(model_id: str, device: str = "cpu"):
    global _model, _processor, _sample_rate

    if _model is not None:
        return

    _LOGGER.info("Loading model %s on %s ...", model_id, device)
    dtype = torch.float32  # CPU only

    _processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    _model = AutoModel.from_pretrained(
        model_id,
        trust_remote_code=True,
        torch_dtype=dtype,
    ).eval().to(device)

    _sample_rate = getattr(_model.config, "codec_sample_rate", 44100)
    _LOGGER.info("Model loaded. Sample rate = %d", _sample_rate)


def synthesize(
    text: str,
    reference_audio: Optional[str] = None,
    reference_text: Optional[str] = None,
    device: str = "cpu",
) -> np.ndarray:
    """Generate waveform (float32 mono)."""
    global _model, _processor, _sample_rate

    if not text or not text.strip():
        return np.zeros(0, dtype=np.float32)

    kwargs = {
        "text": [text.strip()],
        "return_tensors": "pt",
    }

    if reference_audio and Path(reference_audio).is_file():
        kwargs["reference_audio"] = [reference_audio]
        if reference_text:
            kwargs["reference_text"] = [reference_text]
        _LOGGER.debug("Using reference voice: %s", reference_audio)
    else:
        _LOGGER.debug("Generating without reference voice")

    inputs = _processor(**kwargs)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.inference_mode():
        output = _model.generate(
            **inputs,
            max_new_tokens=2048,
            temperature=0.8,
            top_p=0.95,
            top_k=50,
            do_sample=True,
            return_dict_in_generate=True,
        )
        waveforms, waveform_lengths = _model.decode_audio(output.codes)

    audio = waveforms[0, : int(waveform_lengths[0])].float().cpu().numpy()
    return audio


# ---------------------------------------------------------------------------
# Event handler
# ---------------------------------------------------------------------------

class Audio8EventHandler(AsyncEventHandler):
    def __init__(
        self,
        wyoming_info: Info,
        cli_args: argparse.Namespace,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.wyoming_info_event = wyoming_info.event()
        self.cli_args = cli_args

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            _LOGGER.debug("Sent info")
            return True

        if Synthesize.is_type(event.type):
            synth_event = Synthesize.from_event(event)
            text = synth_event.text
            _LOGGER.info("Synthesize: %s", text[:80] + ("..." if len(text) > 80 else ""))

            try:
                # Run blocking inference in executor
                loop = asyncio.get_running_loop()
                audio = await loop.run_in_executor(
                    None,
                    lambda: synthesize(
                        text=text,
                        reference_audio=self.cli_args.reference_audio,
                        reference_text=self.cli_args.reference_text or None,
                        device=self.cli_args.device,
                    ),
                )

                if audio is None or len(audio) == 0:
                    _LOGGER.warning("Empty audio generated")
                    return True

                # Convert float32 [-1,1] → int16
                audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
                rate = _sample_rate
                width = 2  # 16-bit
                channels = 1

                await self.write_event(
                    AudioStart(rate=rate, width=width, channels=channels).event()
                )

                # Send in chunks (optional, but good practice)
                chunk_samples = rate // 4  # ~250ms
                for i in range(0, len(audio_int16), chunk_samples):
                    chunk = audio_int16[i : i + chunk_samples]
                    await self.write_event(
                        AudioChunk(
                            rate=rate,
                            width=width,
                            channels=channels,
                            audio=chunk.tobytes(),
                        ).event()
                    )

                await self.write_event(AudioStop().event())
                _LOGGER.info("Sent %d samples (%.1f s)", len(audio_int16), len(audio_int16) / rate)

            except Exception as e:
                _LOGGER.exception("Synthesis failed: %s", e)

            return True

        return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default="tcp://0.0.0.0:10200", help="unix:// or tcp://")
    parser.add_argument("--model-id", default="Edge0/Audio8-TTS-Realistic-Air")
    parser.add_argument("--language", default="yue", help="Language code (yue = Cantonese)")
    parser.add_argument("--voice-name", default="cantonese", help="Voice name shown in HA")
    parser.add_argument("--reference-audio", default="/voices/reference.wav")
    parser.add_argument("--reference-text", default="", help="Exact transcript of reference audio")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    _LOGGER.info("Audio8 Wyoming TTS %s", __version__)

    # Pre-load model
    load_model(args.model_id, args.device)

    # Build Wyoming info
    voice = TtsVoice(
        name=args.voice_name,
        description=f"Audio8-TTS-Realistic-Air ({args.language})",
        attribution=Attribution(
            name="Edge0",
            url="https://huggingface.co/Edge0/Audio8-TTS-Realistic-Air",
        ),
        installed=True,
        version=__version__,
        languages=[args.language],
    )

    wyoming_info = Info(
        tts=[
            TtsProgram(
                name="audio8",
                description="Audio8-TTS-Realistic-Air (CPU)",
                attribution=Attribution(
                    name="Edge0",
                    url="https://github.com/Edge0-AI/Audio8_TTS",
                ),
                installed=True,
                version=__version__,
                voices=[voice],
            )
        ]
    )

    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info("Ready on %s", args.uri)

    await server.run(
        lambda reader, writer: Audio8EventHandler(wyoming_info, args, reader, writer)
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass