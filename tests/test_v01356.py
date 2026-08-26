import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
EXPORTER = (ROOT / "tools/export_public_repository.py").read_text(encoding="utf-8")
BOUNDARY = (ROOT / "docs/REPOSITORY_BOUNDARIES.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class PublicHistoryContinuityReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.70"', CONFIG)
        self.assertIn('version="0.13.70"', MAIN)
        self.assertIn("HUD 0.13.70", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.70")

    def test_last_pre_split_public_commit_is_the_compatibility_base(self):
        self.assertIn('PUBLIC_HISTORY_BASE = "7036f4f0d89929b1db9f7ab5a64aabee2244908b"', EXPORTER)
        self.assertIn("Supervisor clones cached", BOUNDARY)
        self.assertIn("fast-forward across the split", BOUNDARY)

    def test_post_split_source_remains_private(self):
        self.assertIn("Source commits made after the split exist only in `ZBRANO_Core`", BOUNDARY)

    def test_release_history_includes_v01356(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.69")


if __name__ == "__main__":
    unittest.main()
