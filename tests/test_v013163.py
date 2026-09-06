import ast
import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "jarvis/app/schemas.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_policy_helpers():
    tree = ast.parse(AUTOMATIONS)
    names = {"_automation_effective_policy", "_automation_branch_policy", "_automation_branches"}
    constants = {"AUTOMATION_POLICY_ORDER", "AUTOMATION_GLOBAL_POLICIES"}
    selected = [node for node in tree.body if (
        isinstance(node, ast.FunctionDef) and node.name in names
    ) or (
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id in constants for target in node.targets)
    )]
    namespace = {"Any": Any}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace


class BranchAuthorityReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.165")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.164")

    def test_every_branch_can_choose_its_own_authority(self):
        helpers = load_policy_helpers()
        item = {
            "execution_policy": "approval_required",
            "branches": [
                {"name": "IF", "execution_policy": "approval_required"},
                {"name": "ELSE IF", "execution_policy": "autonomous"},
            ],
        }
        self.assertEqual(helpers["_automation_branch_policy"](item, "IF"), "approval_required")
        self.assertEqual(helpers["_automation_branch_policy"](item, "ELSE IF"), "autonomous")
        self.assertEqual(helpers["_automation_effective_policy"]({**item, "execution_policy": "autonomous"}, {"operating_mode": "suggest_only"})[0], "autonomous")

    def test_setup_no_longer_shows_an_automation_wide_response_choice(self):
        self.assertNotIn("How should ZBRANO respond?", HTML)
        details = WORKSPACE.split('details:{title:"1. Setup & safety"', 1)[1].split("trigger:{", 1)[0]
        self.assertNotIn("automation-execution-policy", details)

    def test_message_only_paths_need_no_authority_but_task_paths_show_it(self):
        self.assertIn("execution_policy: str | None", SCHEMAS)
        self.assertIn("Before running this path's tasks", WORKSPACE)
        self.assertIn("RUN AUTOMATICALLY", FLOW)
        self.assertIn("ASK BEFORE RUNNING", FLOW)
        self.assertIn('data-branch-policy][data-branch-index="1"', BROWSER)


if __name__ == "__main__":
    unittest.main()
