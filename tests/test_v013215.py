import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "zbrano" / "app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
INDEX = (APP / "static" / "index.html").read_text(encoding="utf-8")
ABOUT = (APP / "static" / "js" / "about.js").read_text(encoding="utf-8")
STATE = (APP / "domains" / "developer_state.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano" / "config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano" / "release_manifest.json").read_text(encoding="utf-8"))


class CustomerDeveloperRemovalTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.224"', CONFIG)
        self.assertIn('version="0.13.224"', MAIN)
        self.assertIn("HUD 0.13.224", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.224")

    def test_developer_interface_and_routes_are_not_exposed(self):
        for marker in (
            'id="developer-tab"',
            'id="developer-panel"',
            "js/developer/",
            "css/diagnostics.css",
        ):
            self.assertNotIn(marker, INDEX)
        for method in ("get", "post", "put", "delete", "patch"):
            self.assertNotIn(f'@app.{method}("/api/developer/', MAIN)

    def test_old_developer_state_cannot_reactivate_customer_build(self):
        self.assertIn("return False", STATE)
        self.assertNotIn("def set_developer_mode", STATE)
        self.assertNotIn("DEVELOPER_STATE_PATH", MAIN)

    def test_about_and_safe_support_report_remain_available(self):
        self.assertIn('const settingsTab = document.getElementById("settings-tab")', ABOUT)
        self.assertIn("settingsTab.after(tab)", ABOUT)
        self.assertIn('"installation_report"', MAIN)
        self.assertIn("support_summary", MAIN)


if __name__ == "__main__":
    unittest.main()
