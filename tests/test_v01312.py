from pathlib import Path
import json
import unittest
from tests.frontend_source import load_frontend_source
from tests.backend_source import load_backend_source


ROOT = Path(__file__).resolve().parents[1]
INDEX = load_frontend_source()
MAIN = load_backend_source()
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class InterfaceRefreshTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.21"', CONFIG)
        self.assertIn('version="0.13.21"', MAIN)
        self.assertIn("HUD 0.13.21", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.21")

    def test_refresh_is_a_final_scoped_style_layer(self):
        marker = '<style id="zbrano-v01312-interface-refresh-style">'
        self.assertEqual(INDEX.count(marker), 1)
        refresh = INDEX[INDEX.index(marker) : INDEX.index("</style>", INDEX.index(marker))]
        self.assertIn("body > main > nav", refresh)
        self.assertIn(".panel:not(#chat-panel)", refresh)
        self.assertIn(".settings-category-tabs", refresh)
        self.assertIn(".automation-library-tabs", refresh)
        self.assertIn("overflow-x: auto", refresh)
        self.assertIn("prefers-reduced-motion: reduce", refresh)

    def test_existing_navigation_and_chat_controls_remain_present(self):
        for control_id in (
            "chat-tab",
            "files-tab",
            "automations-tab",
            "entities-tab",
            "plugins-tab",
            "calendar-tab",
            "settings-tab",
            "developer-tab",
            "chat-form",
            "message",
            "mic-button",
            "send-button",
        ):
            self.assertIn(f'id="{control_id}"', INDEX)


if __name__ == "__main__":
    unittest.main()
