"""Copy a few production-path smoke clips to the Windows output mount."""

from pathlib import Path
import shutil


source_root = Path(
    "/workspace/hey_zbrano_exact_smoke_model/hey_zbrano_exact_smoke/positive_train"
)
output_root = Path("/output/final_pronunciation_check")
output_root.mkdir(parents=True, exist_ok=True)

sources = sorted(path for path in source_root.glob("*.wav") if path.is_file())[:3]
if len(sources) != 3:
    raise RuntimeError(f"Expected at least three smoke clips, found {len(sources)}")

for index, source in enumerate(sources, start=1):
    shutil.copy2(source, output_root / f"sample_{index}.wav")

print(f"Copied {len(sources)} clips to {output_root}")
