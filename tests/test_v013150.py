import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class PresenceAndElseIfReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.151")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.150")

    def test_setup_has_per_automation_presence_and_clear_enable_wording(self):
        self.assertIn('id="automation-require-presence"', HTML)
        self.assertIn("Require presence", HTML)
        self.assertIn("Enable automation on saving", WORKSPACE)
        self.assertIn("function presenceEntity()", WORKSPACE)
        self.assertIn("Choose who must be present", WORKSPACE)

    def test_else_if_converts_existing_checks_and_tasks_into_connected_paths(self):
        self.assertIn("function startElseIfFlow()", WORKSPACE)
        self.assertIn('name:"IF"', WORKSPACE)
        self.assertIn('name:"ELSE IF"', WORKSPACE)
        self.assertIn('writeFlowSequence("action",[])', WORKSPACE)
        self.assertIn("IF / ELSE IF — FIRST MATCH RUNS", FLOW)
        self.assertIn(".automation-flow-branch-grid::before", CSS)
        self.assertIn(".automation-flow-branch-lane::before", CSS)

    def test_selected_branch_blocks_get_only_their_own_settings(self):
        self.assertIn('selectedFlowCard.kind==="branch-condition"', WORKSPACE)
        self.assertIn('selectedFlowCard.kind==="branch-action"', WORKSPACE)
        self.assertIn('[data-flow-kind="branch-condition"][data-flow-branch-index="1"]', BROWSER)
        self.assertIn('[data-flow-kind="branch-action"][data-flow-branch-index="1"]', BROWSER)

    def test_browser_covers_the_twenty_minute_open_window_example(self):
        self.assertIn("for_seconds\"]').fill(\"1200\")", BROWSER)
        self.assertIn("Check whether a window is open.", BROWSER)
        self.assertIn("20 min|1200 sec", BROWSER)
        self.assertIn("count(), 0", BROWSER)


if __name__ == "__main__":
    unittest.main()
