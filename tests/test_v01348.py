import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "jarvis/tests/test_app_integration.py").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class MigrationCoverageReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.51"', CONFIG)
        self.assertIn('version="0.13.51"', MAIN)
        self.assertIn("HUD 0.13.51", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.51")

    def test_image_build_gates_legacy_migration_coverage(self):
        self.assertIn('python3 -m unittest discover -s ./tests -p "test_*.py"', DOCKERFILE)
        for marker in (
            "test_legacy_minimal_backup_restores_without_newer_optional_sections",
            "test_malformed_migration_backup_is_rejected_before_any_write",
            '"format": "jarvis-backup-v1"',
            '"entity_policy"',
            '"legacy-chat"',
        ):
            self.assertIn(marker, INTEGRATION)

    def test_release_history_includes_previous_release(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.50")


if __name__ == "__main__":
    unittest.main()
