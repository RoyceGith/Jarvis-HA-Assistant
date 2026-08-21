FROM zbrano-openwakeword-training:latest

COPY tools/wakeword_training/patch_training_image.py /tmp/patch_training_image.py

RUN python3 /tmp/patch_training_image.py \
    && rm -f /tmp/patch_training_image.py \
    && python3 -m py_compile /app/piper-sample-generator/generate_samples.py

# The smoke run exposed that the upstream helper moves these assets into its
# disposable container. Bundle authoritative openWakeWord release copies so
# retries do not require another 20 GB extraction.
RUN wget -q -O /app/openWakeWord/openwakeword/resources/models/embedding_model.onnx \
      https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx \
    && wget -q -O /app/openWakeWord/openwakeword/resources/models/embedding_model.tflite \
      https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.tflite \
    && wget -q -O /app/openWakeWord/openwakeword/resources/models/melspectrogram.onnx \
      https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx \
    && wget -q -O /app/openWakeWord/openwakeword/resources/models/melspectrogram.tflite \
      https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.tflite \
    && test -s /app/openWakeWord/openwakeword/resources/models/embedding_model.onnx \
    && test -s /app/openWakeWord/openwakeword/resources/models/melspectrogram.onnx

RUN grep -q 'ZBRANO_POSITIVE_PHONEMES' /app/piper-sample-generator/generate_samples.py \
    && grep -q 'cp .*piper_tts_model' /app/container-entrypoint.sh
