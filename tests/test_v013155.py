import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class CompactAutomationStudioChromeReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.202")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.201")

    def test_setup_and_progress_are_outside_the_block_palette(self):
        guide = HTML.split('<div class="automation-studio-guide-strip"', 1)[1].split('</div>\n            <nav', 1)[0]
        toolbox = HTML.split('<nav class="automation-studio-toolbox"', 1)[1].split('</nav>', 1)[0]
        self.assertIn('data-studio-node="details"', guide)
        self.assertIn('automation-studio-current-step', guide)
        self.assertNotIn('data-studio-node="details"', toolbox)
        self.assertNotIn('automation-studio-current-step', toolbox)

    def test_palette_contains_only_flow_categories(self):
        toolbox = HTML.split('<nav class="automation-studio-toolbox"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(toolbox.count('class="automation-block-category'), 4)
        for label in ("WHEN · Events", "IF · Conditions", "THEN · Actions", "ELSE IF"):
            self.assertIn(label, toolbox)

    def test_controls_and_progress_use_compact_styling(self):
        self.assertIn('.automation-studio-toolbar .autonomy-draft-actions > button', CSS)
        self.assertIn('padding:.34rem .52rem', CSS)
        self.assertIn('.automation-studio-guide-strip', CSS)
        self.assertIn('grid-template-columns:auto minmax(120px,1fr)', CSS)

    def test_setup_status_and_browser_geometry_follow_new_location(self):
        self.assertIn('.automation-studio-preview [data-studio-node]', WORKSPACE)
        self.assertIn('guideStripBox.y < blockBarBox.y', BROWSER)
        self.assertIn('.automation-studio-toolbox [data-studio-node="details"]', BROWSER)


if __name__ == "__main__":
    unittest.main()
