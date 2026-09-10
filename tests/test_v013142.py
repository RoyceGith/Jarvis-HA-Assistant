import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis" / "app" / "static" / "index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis" / "app" / "static" / "css" / "automation-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013142AutomationStudioNavigationTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.202")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.201")

    def test_five_steps_have_guided_navigation(self):
        for element_id in (
            "automation-studio-current-step",
            "automation-studio-required-progress",
            "automation-studio-progressbar",
            "automation-studio-step-back",
            "automation-studio-step-next",
        ):
            self.assertIn(f'id="{element_id}"', HTML)
        for phrase in ("studioStepOrder", "moveThroughStudio", "Review and finish", "Complete this step first"):
            self.assertIn(phrase, WORKSPACE)

    def test_new_drafts_begin_with_name_and_flow_remains(self):
        self.assertIn('selectedStudioNode="details"', WORKSPACE)
        self.assertIn('id="automation-studio-canvas"', HTML)
        self.assertIn('draggable="true" data-studio-node="trigger"', HTML)
        self.assertIn("automation-studio-step-navigation", CSS)

    def test_final_step_hands_off_to_safe_actions(self):
        self.assertIn("Everything required is ready. Try it safely, or save the automation.", WORKSPACE)
        self.assertIn('id="automation-studio-test" type="button">Try it safely</button>', HTML)
        self.assertIn('id="automation-studio-save" type="button">Save automation</button>', HTML)


if __name__ == "__main__":
    unittest.main()
