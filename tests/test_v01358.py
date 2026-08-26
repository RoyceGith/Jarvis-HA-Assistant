import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
ASGI_TEST = (ROOT / "jarvis/tests/test_app_integration.py").read_text(encoding="utf-8")
BROWSER_TEST = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ContainerBuildFixtureReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.68"', CONFIG)
        self.assertIn('version="0.13.68"', MAIN)
        self.assertIn("HUD 0.13.68", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.68")

    def test_docker_only_fixtures_match_runtime(self):
        self.assertNotIn("0.13.56", ASGI_TEST)
        self.assertNotIn("0.13.56", BROWSER_TEST)
        self.assertIn('"version"], "0.13.68"', ASGI_TEST)
        self.assertIn('version: "0.13.68"', BROWSER_TEST)

    def test_release_history_includes_v01357(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.67")


if __name__ == "__main__":
    unittest.main()
