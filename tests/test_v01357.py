import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
EXPORTER = (ROOT / "tools/export_public_repository.py").read_text(encoding="utf-8")
BOUNDARY = (ROOT / "docs/REPOSITORY_BOUNDARIES.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class PublicHistoryBridgeReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.239"', CONFIG)
        self.assertIn('version="0.13.239"', MAIN)
        self.assertIn("HUD 0.13.239", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.239")

    def test_both_public_transition_heads_are_recorded(self):
        self.assertIn('PUBLIC_HISTORY_BASE = "7036f4f0d89929b1db9f7ab5a64aabee2244908b"', EXPORTER)
        self.assertIn('PUBLIC_TRANSITION_HEAD = "ab43e37032bf59318005dadf5c33f18ef1c59aaf"', EXPORTER)
        self.assertIn("cached on either side of the transition", BOUNDARY)

    def test_public_tree_remains_thin(self):
        self.assertIn("explicitly allowlisted distribution files", BOUNDARY)
        self.assertIn("configuration translations are presentation metadata", BOUNDARY)

    def test_release_history_includes_v01356(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.238")


if __name__ == "__main__":
    unittest.main()
