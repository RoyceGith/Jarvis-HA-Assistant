import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
STYLE = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationLibraryFilteringReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.125"', CONFIG)
        self.assertIn('version="0.13.125"', MAIN)
        self.assertIn("HUD 0.13.125", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.125")

    def test_library_has_compact_search_filter_and_count_controls(self):
        self.assertIn('id="automation-library-search"', HTML)
        self.assertIn('id="automation-library-filter"', HTML)
        self.assertIn('id="automation-library-count"', HTML)
        for value in ("active", "attention", "disabled", "autonomous", "watch"):
            self.assertIn(f'<option value="{value}">', HTML)
        self.assertIn(".automation-library-toolbar", STYLE)
        self.assertIn("width: min(100%,340px)", STYLE)

    def test_search_covers_rule_and_workflow_content(self):
        self.assertIn("const searchable=item=>", WORKSPACE)
        for field in ("item.name", "item.objective", "item.trigger_entity", "item.action_entity", "item.action_service"):
            self.assertIn(field, WORKSPACE)
        self.assertIn("branch.conditions", WORKSPACE)
        self.assertIn("branch.actions", WORKSPACE)

    def test_filters_cover_practical_runtime_states(self):
        self.assertIn('filter==="active"', WORKSPACE)
        self.assertIn('filter==="attention"', WORKSPACE)
        self.assertIn('filter==="disabled"', WORKSPACE)
        self.assertIn('filter==="autonomous"', WORKSPACE)
        self.assertIn('filter==="watch"', WORKSPACE)
        self.assertIn("recovery.circuit_open", WORKSPACE)
        self.assertIn("readiness.ready===false", WORKSPACE)

    def test_browser_exercises_search_filters_and_reset(self):
        self.assertIn('locator("#automation-library-search").fill("browser flow")', BROWSER)
        self.assertIn('locator("#automation-library-search").fill("missing automation")', BROWSER)
        self.assertIn('selectOption("active")', BROWSER)
        self.assertIn('selectOption("disabled")', BROWSER)
        self.assertIn('selectOption("all")', BROWSER)

    def test_release_history_includes_v01384(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.124")


if __name__ == "__main__":
    unittest.main()
