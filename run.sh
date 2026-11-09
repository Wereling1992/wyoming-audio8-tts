#!/bin/bash
set -e

echo "Starting wyoming-audio8-tts (CPU)..."
echo "Model: ${MODEL_ID}"
echo "Language: ${LANGUAGE}"
echo "URI: ${URI}"

exec python -m wyoming_audio8 \
  --uri "${URI}" \
  --model-id "${MODEL_ID}" \
  --language "${LANGUAGE}" \
  --voice-name "${VOICE_NAME}" \
  --reference-audio "${REFERENCE_AUDIO}" \
  --reference-text "${REFERENCE_TEXT}" \
  --device "${DEVICE}" \
  "$@"