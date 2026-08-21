"""Generate Piper samples with explicit phonemes for the ZBRANO brand name."""

import json
from pathlib import Path
import sys
import unicodedata


PIPER_GENERATOR = Path("/app/piper-sample-generator")
sys.path.insert(0, str(PIPER_GENERATOR))

import generate_samples as piper  # noqa: E402


PHONEME_VARIANTS = {
    "exact_zbrahno": "hˈeɪ zbɹˈɑːnoʊ",
    "exact_zbrano": "hˈeɪ zbɹˈænoʊ",
    "exact_zbruhno": "hˈeɪ zbɹˈʌnoʊ",
    "exact_zbrahno_unstressed": "heɪ zbɹɑːnoʊ",
}

MODEL_PATH = PIPER_GENERATOR / "models" / "en-us-libritts-high.pt"
CONFIG_PATH = Path(f"{MODEL_PATH}.json")
OUTPUT_ROOT = Path("/output/exact_pronunciation_candidates")
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
    MODEL_CONFIG = json.load(config_file)


def phoneme_ids(phonemes: str) -> list[int]:
    """Translate an explicit eSpeak phoneme string using the Piper model map."""
    id_map = MODEL_CONFIG["phoneme_id_map"]
    result = list(id_map["^"])
    for phoneme in unicodedata.normalize("NFD", phonemes):
        mapped = id_map.get(phoneme)
        if mapped:
            result.extend(mapped)
            result.extend(id_map["_"])
    result.extend(id_map["$"])
    return result


for name, phonemes in PHONEME_VARIANTS.items():
    output_dir = OUTPUT_ROOT / name
    output_dir.mkdir(parents=True, exist_ok=True)
    exact_ids = phoneme_ids(phonemes)
    original_get_phonemes = piper.get_phonemes
    try:
        piper.get_phonemes = lambda _phonemizer, _config, _text, _verbose: exact_ids
        piper.generate_samples(
            text="hey zbrano",
            output_dir=str(output_dir),
            max_samples=3,
            batch_size=1,
            length_scales=[0.9, 1.0, 1.1],
            file_names=[f"{name}_{index}.wav" for index in range(1, 4)],
        )
    finally:
        piper.get_phonemes = original_get_phonemes

generated = sum(1 for path in OUTPUT_ROOT.rglob("*.wav") if path.is_file())
print(f"Generated {generated} exact-phoneme candidates in {OUTPUT_ROOT}")
