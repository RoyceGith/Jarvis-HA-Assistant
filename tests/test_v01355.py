import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class DistributionFolderCompatibilityReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.233"', CONFIG)
        self.assertIn('version="0.13.233"', MAIN)
        self.assertIn("HUD 0.13.233", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.233")

    def test_public_export_uses_only_the_zbrano_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            subprocess.run(
                [sys.executable, str(ROOT / "tools/export_public_repository.py"), temporary],
                check=True,
                capture_output=True,
                text=True,
            )
            destination = Path(temporary)
            self.assertTrue((destination / "zbrano/config.yaml").is_file())
            self.assertEqual(
                sorted(path.name for path in destination.iterdir() if path.is_dir()),
                ["zbrano"],
            )
            exported_config = (destination / "zbrano/config.yaml").read_text(encoding="utf-8")
        self.assertIn('slug: "zbrano"', exported_config)
        self.assertIn('image: "ghcr.io/roycegith/zbrano-core"', exported_config)

    def test_release_history_includes_v01354(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.232")


if __name__ == "__main__":
    unittest.main()
