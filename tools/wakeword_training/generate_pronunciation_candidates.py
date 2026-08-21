"""Generate small Piper pronunciation sets before expensive wake-word training."""

from pathlib import Path
import sys


PIPER_GENERATOR = Path("/app/piper-sample-generator")
sys.path.insert(0, str(PIPER_GENERATOR))

from generate_samples import generate_samples  # noqa: E402


VARIANTS = {
    "zbrahno": "hey zbrahno",
    "sbrahno": "hey sbrahno",
    "zbranno": "hey zbranno",
    "zbrawno": "hey zbrawno",
}

OUTPUT_ROOT = Path("/output/pronunciation_candidates")
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

for name, phrase in VARIANTS.items():
    output_dir = OUTPUT_ROOT / name
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_samples(
        text=phrase,
        output_dir=str(output_dir),
        max_samples=3,
        batch_size=1,
        length_scales=[0.9, 1.0, 1.1],
        file_names=[f"{name}_{index}.wav" for index in range(1, 4)],
    )

generated = sum(1 for path in OUTPUT_ROOT.rglob("*.wav") if path.is_file())
print(f"Generated {generated} pronunciation candidates in {OUTPUT_ROOT}")
