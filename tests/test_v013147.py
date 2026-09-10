import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis" / "app" / "static" / "index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
STYLES = (ROOT / "jarvis" / "app" / "static" / "css" / "automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis" / "tests" / "browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013147PerAutomationAuthorityTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.204")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.203")

    def test_setup_owns_safety_while_task_paths_own_authority(self):
        details = WORKSPACE.split('details:{title:"1. Setup & safety"', 1)[1].split("trigger:{", 1)[0]
        self.assertNotIn("automation-execution-policy", details)
        for field in ("automation-risk", "automation-max-actions", "automation-reversible-only", "automation-notify-action"):
            self.assertIn(field, details)
        self.assertIn("Authority for this path", WORKSPACE)
        self.assertIn("data-branch-policy", WORKSPACE)

    def test_global_authority_screen_is_not_part_of_normal_navigation(self):
        self.assertIn('data-auto-view="safety" role="tab" aria-selected="false" hidden', HTML)
        self.assertIn(".autonomy-tabs button[hidden]", STYLES)
        self.assertIn("Authority model", HTML)
        self.assertIn('textContent="Per automation"', WORKSPACE)

    def test_browser_exercises_safety_in_setup_and_authority_in_branches(self):
        self.assertIn('"1. Setup & safety"', BROWSER)
        self.assertIn('data-branch-policy', BROWSER)
        self.assertIn('#studio-automation-risk', BROWSER)
        self.assertIn('#studio-automation-max-actions', BROWSER)


if __name__ == "__main__":
    unittest.main()
