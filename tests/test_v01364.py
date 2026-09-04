import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
STYLES = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
READMES = [
    (ROOT / "README.md").read_text(encoding="utf-8"),
    (ROOT / "jarvis/README.md").read_text(encoding="utf-8"),
    (ROOT / "distribution/public-repository/README.md").read_text(encoding="utf-8"),
    (ROOT / "distribution/public-repository/jarvis/README.md").read_text(encoding="utf-8"),
]


class VisualAutomationBuilderReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.149"', CONFIG)
        self.assertIn('version="0.13.149"', MAIN)
        self.assertIn("HUD 0.13.149", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.149")

    def test_three_panel_builder_is_present(self):
        for marker in ("automation-studio-toolbox", "automation-studio-canvas", "automation-studio-inspector"):
            self.assertIn(marker, HTML)
            self.assertIn(marker, STYLES)
        for block in ("details", "trigger", "context", "decision", "action"):
            self.assertIn(f'data-studio-node="{block}"', HTML)

    def test_inspector_synchronizes_with_canonical_form(self):
        self.assertIn("const studioPanels=", WORKSPACE)
        self.assertIn("cloneNode(true)", WORKSPACE)
        self.assertIn('source.dispatchEvent(new Event("input"', WORKSPACE)
        self.assertIn('requestSubmit()', WORKSPACE)
        self.assertIn("dataset.flowKind", FLOW)

    def test_builder_supports_drag_keyboard_and_advanced_fallback(self):
        self.assertIn('draggable="true"', HTML)
        self.assertIn('setData("text/studio-node"', WORKSPACE)
        self.assertIn('getData("text/studio-node"', WORKSPACE)
        self.assertIn('["Enter"," "]', WORKSPACE)
        self.assertIn('class="automation-advanced"', HTML)

    def test_all_product_readmes_are_current(self):
        for readme in READMES:
            self.assertIn("0.13.149", readme)
            self.assertIn("Automation Studio", readme)

    def test_release_history_includes_v01363(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.148")


if __name__ == "__main__":
    unittest.main()
