import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano/app/static/js/automations/flow.js").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class CategorizedTopBlockBarReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.231")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.230")

    def test_categories_replace_the_left_step_column(self):
        for label in ("WHEN · Events", "IF · Conditions", "THEN · Actions", "ELSE IF"):
            self.assertIn(label, HTML)
        self.assertIn("grid-column:1 / -1", CSS)
        self.assertIn("overflow-x:auto", CSS)
        self.assertIn("grid-template-columns: minmax(0,1fr) minmax(250px,310px)", CSS)

    def test_top_bar_contains_typed_block_shortcuts(self):
        for attribute in ("data-tool-trigger", "data-tool-condition", "data-tool-action"):
            self.assertIn(attribute, HTML)
        for helper in ("addToolbarTrigger", "addToolbarCondition", "addToolbarAction"):
            self.assertIn(f"function {helper}", WORKSPACE)

    def test_if_starts_conditions_and_and_or_connects_more(self):
        self.assertIn('const label=i?"CHECK":"IF"', FLOW)
        self.assertIn("The first is IF; additional conditions connect with AND or OR", WORKSPACE)

    def test_browser_verifies_layout_and_direct_insertion(self):
        self.assertIn("blockBarBox.y < flowCanvasBox.y", BROWSER)
        self.assertIn('[data-tool-condition="entity"]', BROWSER)
        self.assertIn('[data-tool-action="turn_on"]', BROWSER)


if __name__ == "__main__":
    unittest.main()
