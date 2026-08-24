import json
from pathlib import Path
import unittest
from tests.frontend_source import load_frontend_source
from tests.backend_source import load_backend_source


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis" / "app"
MAIN = load_backend_source()
INDEX = load_frontend_source()
CONFIG = (ROOT / "jarvis" / "config.yaml").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis" / "Dockerfile").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))
BASELINE = (ROOT / "docs" / "CANONICAL_BASELINE.md").read_text(encoding="utf-8")


class CanonicalSourceTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        version = MANIFEST["version"]
        self.assertIn(f'version: "{version}"', CONFIG)
        self.assertIn(f'version="{version}"', MAIN)
        self.assertIn(f"HUD {version}", INDEX)

    def test_docker_build_uses_canonical_source(self):
        self.assertIn("COPY app ./app", DOCKER)
        self.assertNotIn("COPY apply_", DOCKER)
        self.assertNotIn("python3 ./apply_", DOCKER)
        self.assertIn("validate_release_manifest.py", DOCKER)
        self.assertIn("validate_inline_js.py", DOCKER)
        self.assertIn("validate_new_chat_wiring.py", DOCKER)
        self.assertIn("sed -i 's/\\r$//' /run.sh", DOCKER)

    def test_promoted_source_retains_frozen_capability_surfaces(self):
        for marker in (
            '@app.get("/api/health")',
            '@app.get("/api/plugins")',
            '@app.get("/api/automations")',
            '@app.get("/api/calendar")',
            '@app.get("/api/ha/history")',
            '@app.post("/api/voice/transcribe")',
            '@app.get("/api/developer/diagnostics")',
        ):
            self.assertIn(marker, MAIN)
        for marker in (
            'id="chat-panel"',
            'id="files-panel"',
            'id="automations-panel"',
            'id="entities-panel"',
            'id="plugins-panel"',
            'id="calendar-panel"',
            'id="settings-panel"',
            'id="developer-panel"',
        ):
            self.assertIn(marker, INDEX)

    def test_baseline_is_documented(self):
        self.assertIn("`435ef91`", BASELINE)
        self.assertIn("1FCE3174411BAAC69980DA445E9EFCFED74B4315B6FD793F22DCC184A4B2FCBA", BASELINE)
        self.assertIn("8BEBB7A10ACF864AD65C83C5B9F667975BDB642E2E5BA2B7B356A7A03904E961", BASELINE)


if __name__ == "__main__":
    unittest.main()
