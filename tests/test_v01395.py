import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis/app/static/css/base.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationOverviewShortcutReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.131"', CONFIG)
        self.assertIn('version="0.13.131"', MAIN)
        self.assertIn("HUD 0.13.131", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.131")

    def test_overview_metrics_are_accessible_navigation_controls(self):
        self.assertIn('data-automation-overview-target="drafts"', HTML)
        self.assertIn('data-automation-overview-target="suggestions"', HTML)
        self.assertIn('id="autonomy-suggestion-inbox"', HTML)
        self.assertIn("function openOverviewShortcut(target)", WORKSPACE)
        self.assertIn('showView("library")', WORKSPACE)
        self.assertIn('$("automation-library-filter").value="disabled"', WORKSPACE)
        self.assertIn('showView("overview");destination=$("autonomy-suggestion-inbox")', WORKSPACE)
        self.assertIn(".autonomy-metric-link:hover", CSS)
        self.assertIn(".autonomy-metric-link:focus-visible", CSS)

    def test_metric_counts_match_their_destinations(self):
        self.assertIn("filter(item=>!item.enabled).length", WORKSPACE)
        self.assertIn('["pending","approval_required"].includes(item.status)', WORKSPACE)
        self.assertIn("delivery_notification_center!==false", WORKSPACE)

    def test_release_history_includes_v01394(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.130")


if __name__ == "__main__":
    unittest.main()
