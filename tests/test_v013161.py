import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = (ROOT / "zbrano/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "zbrano/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano/app/static/js/automations/flow.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class OptionalBranchMessageTaskReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.247")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.246")

    def test_message_presence_is_persisted_and_legacy_messages_remain_enabled(self):
        self.assertIn("message_enabled: bool | None = None", SCHEMAS)
        self.assertIn('if branch.get("message_enabled") is None', AUTOMATIONS)
        self.assertIn('branch.get("message_enabled", bool(branch.get("suggestion")))', AUTOMATIONS)

    def test_new_else_if_paths_do_not_include_a_message(self):
        self.assertIn('suggestion:"",message_enabled:false', WORKSPACE)
        self.assertIn('if(showMessages&&!messageEnabled)choices.push(["message","Message"])', FLOW)
        self.assertIn('data-flow-kind="branch-message"', BROWSER)

    def test_message_is_an_optional_branch_task_with_its_own_inspector(self):
        self.assertIn('template==="message"', WORKSPACE)
        self.assertIn('kind:"branch-message"', WORKSPACE)
        self.assertIn("function branchMessageEditor", WORKSPACE)
        self.assertIn('node("branch-message"', FLOW)

    def test_message_only_paths_do_not_request_action_approval(self):
        self.assertIn("has_executable_action = bool(selected_actions)", AUTOMATIONS)
        self.assertIn('"approval_required" if has_executable_action and policy', AUTOMATIONS)

    def test_browser_covers_adding_and_configuring_a_message_task(self):
        self.assertIn('data-flow-branch-task-template="message"', BROWSER)
        self.assertIn("messageMenu.locator", BROWSER)
        self.assertIn("[data-branch-delivery]').count(), 3", BROWSER)


if __name__ == "__main__":
    unittest.main()
