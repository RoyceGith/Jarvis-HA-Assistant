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


class ReliableComposerPluginIconReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.246"', CONFIG)
        self.assertIn('version="0.13.246"', MAIN)
        self.assertIn("HUD 0.13.246", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.246")

    def test_icon_handlers_precede_image_loading(self):
        self.assertIn('data-plugin-icon-src=', CONTEXT)
        self.assertIn('image.addEventListener("error"', CONTEXT)
        self.assertIn('image.src=image.dataset.pluginIconSrc', CONTEXT)
        self.assertIn('.composer-plugin-inline-icon', STYLE)


if __name__ == "__main__":
    unittest.main()
