import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
REPOSITORY = (ROOT / "repository.yaml").read_text(encoding="utf-8")
DEVELOPER = (ROOT / "jarvis/app/services/developer_support.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class RepositoryRenameReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.161"', CONFIG)
        self.assertIn('version="0.13.161"', MAIN)
        self.assertIn("HUD 0.13.161", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.161")

    def test_source_and_distribution_repositories_are_separate(self):
        canonical = "RoyceGith/ZBRANO_Core"
        distribution = "RoyceGith/ZBRANO_HA_Assistant"
        self.assertIn(canonical, MANIFEST["source"])
        self.assertIn(canonical, DOCKERFILE)
        self.assertIn(canonical, DEVELOPER)
        self.assertIn(distribution, REPOSITORY)

    def test_existing_home_assistant_image_path_is_preserved(self):
        image = "ghcr.io/roycegith/jarvis-ha-assistant"
        self.assertIn(image, CONFIG)
        self.assertNotIn("ghcr.io/roycegith/zbrano_ha_assistant", CONFIG.lower())

    def test_release_history_includes_v01352(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.160")


if __name__ == "__main__":
    unittest.main()
