import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "jarvis/tests/test_app_integration.py").read_text(encoding="utf-8")
TESTING = (ROOT / "docs/TESTING.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class IntegrationTestFoundationTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.53"', CONFIG)
        self.assertIn('version="0.13.53"', MAIN)
        self.assertIn("HUD 0.13.53", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.53")

    def test_image_build_runs_real_application_integration_suite(self):
        self.assertIn("COPY tests ./tests", DOCKERFILE)
        self.assertIn('python3 -m unittest discover -s ./tests -p "test_*.py"', DOCKERFILE)
        self.assertIn("from app import main", INTEGRATION)
        self.assertIn("httpx.ASGITransport(app=main.app)", INTEGRATION)

    def test_integration_boundaries_are_isolated_and_critical(self):
        for marker in (
            "TemporaryDirectory()",
            "settings.SETTINGS_STORAGE_PATH = temporary_root",
            "conversations.CHAT_STORAGE_PATH = temporary_root",
            'self.client.get("/api/health")',
            'self.client.get("/api/settings")',
            'self.client.post("/api/chats"',
            "AsyncMock(return_value=approved)",
        ):
            self.assertIn(marker, INTEGRATION)
        self.assertIn("temporary persistence paths", TESTING)
        self.assertIn("Assistant, Workshop Memory, OpenAI", TESTING)
        self.assertIn("build runs this suite", TESTING)


if __name__ == "__main__":
    unittest.main()
