import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "zbrano/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "zbrano/Dockerfile").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
TESTING = (ROOT / "docs/TESTING.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class BrowserSmokeFoundationTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.239"', CONFIG)
        self.assertIn('version="0.13.239"', MAIN)
        self.assertIn("HUD 0.13.239", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.239")

    def test_image_build_runs_browser_smoke_after_asgi_tests(self):
        integration = 'python3 -m unittest discover -s ./tests -p "test_*.py"'
        browser = "node ./tests/browser_smoke.cjs"
        self.assertIn(integration, DOCKERFILE)
        self.assertIn(browser, DOCKERFILE)
        self.assertLess(DOCKERFILE.index(integration), DOCKERFILE.index(browser))

    def test_browser_covers_critical_interactions(self):
        for marker in (
            'locator("#new-chat-button").click()',
            'locator("#entities-tab").click()',
            '"Entity Inventory must scroll horizontally"',
            '"Entity Inventory must scroll vertically"',
            'locator("#automations-tab").click()',
            'data-auto-view="library"',
        ):
            self.assertIn(marker, BROWSER)
        self.assertIn("real frontend source", TESTING)
        self.assertIn("deterministic API responses", TESTING)

    def test_browser_reuses_pinned_runtime_dependencies(self):
        self.assertIn('@playwright", "mcp", "node_modules"', BROWSER)
        self.assertIn('"/usr/bin/chromium"', BROWSER)
        self.assertNotIn("npm install", BROWSER)
        self.assertIn("npm uninstall --global @playwright/mcp", DOCKERFILE)
        self.assertIn("apk del nodejs npm chromium", DOCKERFILE)


if __name__ == "__main__":
    unittest.main()
