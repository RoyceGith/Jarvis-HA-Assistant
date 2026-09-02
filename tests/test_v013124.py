import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ClearAutomationFlowReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.130")
        self.assertIn("HUD 0.13.130", HTML)

    def test_visible_context_block_is_condition(self):
        self.assertIn('data-studio-node="context"><strong>Condition</strong>', HTML)
        self.assertIn('context:{title:"Shared condition"', WORKSPACE)

    def test_flow_uses_plain_task_language(self):
        for label in ("WHEN ANY OF THESE CHANGE", "DO THIS", "AND THESE TASKS"):
            self.assertIn(f'"{label}"', FLOW)
        self.assertNotIn("% confidence", FLOW)

    def test_flow_entity_labels_include_name_and_id(self):
        self.assertIn('`${name} · ${id}`', WORKSPACE)

    def test_previous_release_is_in_history(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.129")


if __name__ == "__main__":
    unittest.main()
