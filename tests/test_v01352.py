import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/build.yaml").read_text(encoding="utf-8")
BOUNDARY = (ROOT / "docs/REPOSITORY_BOUNDARIES.md").read_text(encoding="utf-8")
VALIDATOR = (ROOT / "validate_public_repo.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class RepositoryBoundaryReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.53"', CONFIG)
        self.assertIn('version="0.13.53"', MAIN)
        self.assertIn("HUD 0.13.53", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.53")

    def test_public_and_private_responsibilities_are_explicit(self):
        self.assertIn("public, independently runnable ZBRANO Home Assistant app", BOUNDARY)
        self.assertIn("Future hosted capabilities belong in a separate private repository", BOUNDARY)
        self.assertIn("must not import private source code", BOUNDARY)

    def test_public_boundary_is_build_gated(self):
        self.assertIn("validate_public_repo.py", WORKFLOW)
        self.assertIn("FORBIDDEN_PREFIXES", VALIDATOR)
        self.assertIn("PERSONAL_DEFAULTS", VALIDATOR)

    def test_release_history_includes_v01351(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.52")


if __name__ == "__main__":
    unittest.main()
