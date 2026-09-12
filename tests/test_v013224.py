import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CONTEXT = (ROOT / "zbrano/app/static/js/chat/composer-context.js").read_text(encoding="utf-8")
PREFERENCES = (ROOT / "zbrano/app/static/js/chat/composer-preferences.js").read_text(encoding="utf-8")
STYLE = (ROOT / "zbrano/app/static/css/composer-controls.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class CompactComposerControlsReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.234"', CONFIG)
        self.assertIn('version="0.13.234"', MAIN)
        self.assertIn("HUD 0.13.234", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.234")

    def test_ai_and_voice_controls_use_an_accessible_popover(self):
        self.assertIn('id="composer-preferences-toggle"', INDEX)
        self.assertIn('id="composer-preferences-popover"', INDEX)
        self.assertIn('aria-controls="composer-preferences-popover"', INDEX)
        self.assertIn("event.key !== \"Escape\"", PREFERENCES)
        self.assertIn('toggle.setAttribute("aria-expanded"', PREFERENCES)
        self.assertIn(".composer-preferences-toolbar", STYLE)

    def test_plugin_context_is_compact_and_keeps_status_information(self):
        self.assertNotIn('id="composer-plugin-count"', INDEX)
        self.assertIn('installed.map(iconButton).join("")', CONTEXT)
        self.assertIn("stateLabel(plugin)", CONTEXT)
        self.assertIn('aria-label="Installed plugins"', INDEX)
        self.assertIn(".composer-plugin-overflow", STYLE)


if __name__ == "__main__":
    unittest.main()
