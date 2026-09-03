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


class AutomationStudioReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.134"', CONFIG)
        self.assertIn('version="0.13.134"', MAIN)
        self.assertIn("HUD 0.13.134", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.134")

    def test_visual_renderer_is_safe_and_schema_neutral(self):
        for label in ("WHEN ANY OF THESE CHANGE", "DO THIS", "AND THESE TASKS"):
            self.assertIn(f'"{label}"', FLOW)
        self.assertIn("textContent", FLOW)
        self.assertNotIn("innerHTML", FLOW)
        self.assertNotIn("fetch(", FLOW)

    def test_create_preview_and_saved_library_use_the_same_renderer(self):
        self.assertIn('id="automation-flow-preview"', HTML)
        self.assertIn('src="js/automations/flow.js"', HTML)
        self.assertLess(HTML.index('src="js/automations/flow.js"'), HTML.index('src="js/automations/workspace.js"'))
        self.assertIn("flowElement(item)", WORKSPACE)
        self.assertIn("renderEditorFlow", WORKSPACE)
        self.assertIn('addEventListener("input",()=>{renderEditorFlow();scheduleEditorHistory()})', WORKSPACE)

    def test_flow_is_responsive_and_grinder_is_excluded(self):
        self.assertIn("grid-template-columns", STYLES)
        self.assertIn("@media (max-width:", STYLES)
        self.assertNotIn("grinder", FLOW.lower())

    def test_release_history_includes_v01362(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.133")


if __name__ == "__main__":
    unittest.main()
