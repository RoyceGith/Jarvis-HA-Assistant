"""Harden the pinned openWakeWord trainer for ZBRANO production training."""

from pathlib import Path


GENERATOR = Path("/app/piper-sample-generator/generate_samples.py")
ENTRYPOINT = Path("/app/container-entrypoint.sh")


def replace_once(text: str, old: str, new: str, description: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {description} marker, found {count}")
    return text.replace(old, new, 1)


generator = GENERATOR.read_text(encoding="utf-8")
generator = replace_once(
    generator,
    "            phoneme_ids = [get_phonemes(phonemizer, config, next(texts), verbose) for i in range(batch_size)]\n",
    """            explicit_phonemes = os.environ.get(\"ZBRANO_POSITIVE_PHONEMES\", \"\").strip()
            if explicit_phonemes and \"positive_\" in str(output_dir):
                phoneme_ids = [get_explicit_phonemes(config, explicit_phonemes) for i in range(batch_size)]
            else:
                phoneme_ids = [get_phonemes(phonemizer, config, next(texts), verbose) for i in range(batch_size)]
""",
    "positive phoneme generation",
)
generator = replace_once(
    generator,
    "def remove_silence(x, frame_duration=.030, sample_rate=16000, min_start = 2000):\n",
    """def get_explicit_phonemes(config, phonemes_str):
    \"\"\"Convert an explicit eSpeak phoneme string using the Piper model map.\"\"\"
    phonemes = list(unicodedata.normalize(\"NFD\", phonemes_str))
    id_map = config[\"phoneme_id_map\"]
    phoneme_ids = list(id_map[\"^\"])
    for phoneme in phonemes:
        mapped = id_map.get(phoneme)
        if mapped:
            phoneme_ids.extend(mapped)
            phoneme_ids.extend(id_map[\"_\"])
    phoneme_ids.extend(id_map[\"$\"])
    return phoneme_ids


def remove_silence(x, frame_duration=.030, sample_rate=16000, min_start = 2000):
""",
    "explicit phoneme helper",
)
GENERATOR.write_text(generator, encoding="utf-8", newline="\n")

entrypoint = ENTRYPOINT.read_text(encoding="utf-8")
entrypoint = entrypoint.replace(
    'mv "$WORKSPACE/embedding_models/$model_file" "$MODELS_DIR/$model_file"',
    'cp "$WORKSPACE/embedding_models/$model_file" "$MODELS_DIR/$model_file"',
)
entrypoint = entrypoint.replace(
    'mv "$WORKSPACE/piper_tts_model/en-us-libritts-high.pt" "$TTS_DIR/en-us-libritts-high.pt"',
    'cp "$WORKSPACE/piper_tts_model/en-us-libritts-high.pt" "$TTS_DIR/en-us-libritts-high.pt"',
)
ENTRYPOINT.write_text(entrypoint, encoding="utf-8", newline="\n")

print("Applied explicit-positive-phoneme and persistent-asset patches")
