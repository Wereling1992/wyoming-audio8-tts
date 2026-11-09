FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY wyoming_audio8/ ./wyoming_audio8/
COPY run.sh .

RUN chmod +x run.sh

# Default ports & volumes
EXPOSE 10200
VOLUME ["/voices", "/root/.cache/huggingface"]

ENV MODEL_ID=Edge0/Audio8-TTS-Realistic-Air
ENV URI=tcp://0.0.0.0:10200
ENV LANGUAGE=yue
ENV VOICE_NAME=cantonese
ENV REFERENCE_AUDIO=/voices/reference.wav
ENV REFERENCE_TEXT=""
ENV DEVICE=cpu

ENTRYPOINT ["./run.sh"]