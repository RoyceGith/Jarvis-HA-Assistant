import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationLibraryPreferencesReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.98"', CONFIG)
        self.assertIn('version="0.13.98"', MAIN)
        self.assertIn("HUD 0.13.98", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.98")

    def test_library_exposes_practical_sort_options(self):
        self.assertIn('id="automation-library-sort"', HTML)
        for value in ("recent", "name_asc", "name_desc", "active", "attention"):
            self.assertIn(f'<option value="{value}">', HTML)

    def test_sorting_is_stable_and_does_not_mutate_api_state(self):
        self.assertIn(".filter(item=>", WORKSPACE)
        self.assertIn(".slice()", WORKSPACE)
        self.assertIn("visible.sort((left,right)=>", WORKSPACE)
        self.assertIn("right.updated_at||right.created_at", WORKSPACE)
        self.assertIn("localeCompare", WORKSPACE)
        self.assertIn("attentionScore(right)-attentionScore(left)", WORKSPACE)

    def test_library_preferences_are_local_and_validated(self):
        self.assertIn('libraryPrefsKey="zbrano.automation-studio.library.v1"', WORKSPACE)
        self.assertIn("function readLibraryPrefs()", WORKSPACE)
        self.assertIn("function persistLibraryPrefs()", WORKSPACE)
        self.assertIn("localStorage.setItem(libraryPrefsKey", WORKSPACE)
        self.assertIn('showLibraryView(libraryPrefs.view,false)', WORKSPACE)
        self.assertIn('["create","saved"].includes(value.view)', WORKSPACE)

    def test_browser_exercises_ordering_and_preference_storage(self):
        self.assertIn('selectOption("name_desc")', BROWSER)
        self.assertIn('selectOption("active")', BROWSER)
        self.assertIn('zbrano.automation-studio.library.v1', BROWSER)
        self.assertIn('{view: "saved", filter: "all", sort: "active", layout: "compact"}', BROWSER)

    def test_release_history_includes_v01385(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.97")


if __name__ == "__main__":
    unittest.main()
