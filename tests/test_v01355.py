import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class DistributionFolderCompatibilityReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.188"', CONFIG)
        self.assertIn('version="0.13.188"', MAIN)
        self.assertIn("HUD 0.13.188", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.188")

    def test_public_export_restores_original_jarvis_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            subprocess.run(
                [sys.executable, str(ROOT / "tools/export_public_repository.py"), temporary],
                check=True,
                capture_output=True,
                text=True,
            )
            destination = Path(temporary)
            self.assertTrue((destination / "jarvis/config.yaml").is_file())
            self.assertFalse((destination / "zbrano").exists())
            exported_config = (destination / "jarvis/config.yaml").read_text(encoding="utf-8")
        self.assertIn('slug: "jarvis_workshop_assistant"', exported_config)
        self.assertIn('image: "ghcr.io/roycegith/jarvis-ha-assistant"', exported_config)

    def test_release_history_includes_v01354(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.187")


if __name__ == "__main__":
    unittest.main()
