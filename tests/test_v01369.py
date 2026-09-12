import ast
import json
from pathlib import Path
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "zbrano/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "zbrano/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
STUDIO_CSS = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
VOICE = (ROOT / "zbrano/app/static/js/voice/proactive.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


def load_policy_function():
    tree = ast.parse(AUTOMATIONS)
    selected = [node for node in tree.body if (
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id in {"AUTOMATION_POLICY_ORDER", "AUTOMATION_GLOBAL_POLICIES"} for target in node.targets)
    ) or (isinstance(node, ast.FunctionDef) and node.name == "_automation_effective_policy")]
    namespace = {"Any": Any}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace["_automation_effective_policy"]


class PerAutomationOperatingModeReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.225"', CONFIG)
        self.assertIn('version="0.13.225"', MAIN)
        self.assertIn("HUD 0.13.225", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.225")

    def test_explicit_path_authority_replaces_the_legacy_global_ceiling(self):
        effective = load_policy_function()
        self.assertEqual(effective({"execution_policy": "autonomous"}, {"operating_mode": "suggest_only"})[0], "autonomous")
        self.assertEqual(effective({"execution_policy": "inherit"}, {"operating_mode": "approval_gated"})[0], "approval_required")
        self.assertEqual(effective({"execution_policy": "suggest"}, {"operating_mode": "selective_autonomy"})[0], "suggest")
        self.assertEqual(effective({"execution_policy": "autonomous"}, {"operating_mode": "selective_autonomy"})[0], "autonomous")

    def test_schema_and_engine_route_delivery_per_automation(self):
        self.assertIn('default="inherit", pattern="^(inherit|observe|suggest|approval_required|autonomous)$"', SCHEMAS)
        for field in ("delivery_voice", "delivery_notification_center", "delivery_ha_push"):
            self.assertIn(f"{field}: bool = True", SCHEMAS)
            self.assertIn(f'"{field}"', AUTOMATIONS)
        self.assertIn("suggestion-only and cannot execute from approval", MAIN)
        self.assertIn("This path no longer permits approval", MAIN)
        self.assertIn('item.delivery_voice!==false', VOICE)

    def test_automation_studio_is_a_full_window_tab(self):
        self.assertIn('data-auto-view="studio"', HTML)
        self.assertIn('data-auto-panel="studio"', HTML)
        self.assertIn("My Automations", HTML)
        self.assertNotIn(">Automation Library<", HTML)
        self.assertIn('panel.classList.toggle("studio-active",name==="studio")', WORKSPACE)
        self.assertIn("#automations-panel.studio-active", STUDIO_CSS)

    def test_release_history_includes_v01368(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.224")


if __name__ == "__main__":
    unittest.main()
