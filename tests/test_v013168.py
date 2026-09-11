import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationObservabilityReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.214"', CONFIG)
        self.assertIn('version="0.13.214"', MAIN)
        self.assertIn("HUD 0.13.214", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.214")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.213")

    def test_activity_has_health_and_decision_controls(self):
        for marker in (
            'id="automation-activity-watching"',
            'id="automation-activity-attention"',
            'id="automation-activity-matched"',
            'id="automation-activity-actions"',
            'id="automation-activity-automation-filter"',
            'id="automation-activity-result-filter"',
            'id="automation-health-list"',
            'id="automation-decision-feed"',
        ):
            self.assertIn(marker, WORKSPACE)

    def test_decisions_are_translated_and_filterable(self):
        self.assertIn("const decisionLabels=", WORKSPACE)
        self.assertIn('suppressed_presence:"Required person is not present"', WORKSPACE)
        self.assertIn('approval_required:"Matched — waiting for approval"', WORKSPACE)
        self.assertIn('executed:"Action completed"', WORKSPACE)
        self.assertIn("function renderActivity()", WORKSPACE)
        self.assertIn("matchedDecisionOutcomes", WORKSPACE)
        self.assertIn("attentionDecisionOutcomes", WORKSPACE)

    def test_activity_is_responsive_and_browser_tested(self):
        self.assertIn(".automation-activity-grid", CSS)
        self.assertIn("#automation-activity-watching", BROWSER)
        self.assertIn('selectOption("no_action")', BROWSER)
        self.assertIn("/Action completed/i", BROWSER)
        self.assertIn("/Required person is not present/i", BROWSER)


if __name__ == "__main__":
    unittest.main()
