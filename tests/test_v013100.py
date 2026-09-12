import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano/app/static/js/automations/flow.js").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class DenseAutomationStageReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.225"', CONFIG)
        self.assertIn('version="0.13.225"', MAIN)
        self.assertIn("HUD 0.13.225", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.225")

    def test_more_than_two_cards_enable_dense_layout(self):
        self.assertIn('nodes.length>2?" is-dense":""', FLOW)
        self.assertIn("e.dataset.flowCount=nodes.length", FLOW)
        self.assertIn(".automation-flow-stage.is-dense .automation-flow-node", CSS)
        self.assertIn(".automation-flow-stage.is-trigger.is-dense", BROWSER)

    def test_logic_selection_has_readable_width_and_full_options(self):
        self.assertIn("width: 72px; min-width: 72px", CSS)
        self.assertIn('[["any","OR"],["all","AND"]]', FLOW)
        self.assertIn('["OR", "AND"]', BROWSER)

    def test_release_history_includes_v01399(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.224")


if __name__ == "__main__":
    unittest.main()
