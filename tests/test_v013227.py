import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CONTEXT = (ROOT / "zbrano/app/static/js/chat/composer-context.js").read_text(encoding="utf-8")
STYLE = (ROOT / "zbrano/app/static/css/composer-controls.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))

class InlineGithubComposerIconReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.243"', CONFIG)
        self.assertIn('version="0.13.243"', MAIN)
        self.assertIn("HUD 0.13.243", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.243")

    def test_github_icon_has_no_runtime_asset_dependency(self):
        self.assertIn('endsWith("plugin-icons/github.svg")', CONTEXT)
        self.assertIn('<svg class="composer-plugin-inline-icon"', CONTEXT)
        self.assertIn('fill:currentColor', STYLE)

if __name__ == "__main__":
    unittest.main()
