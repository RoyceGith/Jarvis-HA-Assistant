from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
RELEASE_SYNC = (APP / "domains/release_sync.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ReleaseSyncDomainBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.23"', CONFIG)
        self.assertIn('version="0.13.23"', MAIN)
        self.assertIn("HUD 0.13.23", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.23")

    def test_release_worker_is_outside_composition_root(self):
        self.assertNotIn("async def synchronize_release_to_workshop_memory_once(", MAIN)
        self.assertNotIn("def persist_release_sync_status(", MAIN)
        self.assertIn("async def synchronize_release_to_workshop_memory_once(", RELEASE_SYNC)
        self.assertIn("def persist_release_sync_status(", RELEASE_SYNC)
        self.assertIn('RELEASE_SYNC_STATE_PATH = Path("/data/zbrano_release_sync.json")', RELEASE_SYNC)

    def test_eleven_note_contract_and_verification_are_preserved(self):
        for note in (
            "Project Overview.md", "Requirements.md", "Deployment and Operations.md",
            "Release and Change Log.md", "Session Handoff.md", "Architecture.md",
            "Design Decisions.md", "API and Integrations.md", "Data and Storage.md",
            "Security and Permissions.md", "Test Log.md",
        ):
            self.assertIn(f'"{note}"', RELEASE_SYNC)
        self.assertIn("release_sync_content_matches(verified.get(\"content\"), expected_content)", RELEASE_SYNC)

    def test_lifecycle_and_settings_use_domain_api(self):
        self.assertIn("configure_release_sync_domain(", MAIN)
        self.assertIn("schedule_release_sync()", MAIN)
        self.assertIn("await stop_release_sync()", MAIN)
        self.assertIn("cancel_release_sync()", MAIN)
        self.assertNotIn("global RELEASE_SYNC_TASK", MAIN)


if __name__ == "__main__":
    unittest.main()
