import ast
import json
from pathlib import Path
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_failure_circuit():
    tree = ast.parse(AUTOMATIONS)
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_automation_failure_circuit")
    namespace = {"Any": Any}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace["_automation_failure_circuit"]


class AutomationRecoveryCenterReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.189"', CONFIG)
        self.assertIn('version="0.13.189"', MAIN)
        self.assertIn("HUD 0.13.189", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.189")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.188")

    def test_failure_circuit_reports_recovery_timing_and_error(self):
        circuit = load_failure_circuit()
        item = {
            "failure_limit": 3,
            "failure_window_minutes": 60,
            "last_error": "Home Assistant service timed out",
            "feedback_memory": {"failure_timestamps": [600, 700, 800, 900], "recovery_resets": 2},
        }
        opened, _, count = circuit(item, 1000)
        recovery = item["recovery_state"]
        self.assertTrue(opened)
        self.assertEqual(count, 4)
        self.assertEqual(recovery["retry_available_at"], 4300)
        self.assertEqual(recovery["last_failure_at"], 900)
        self.assertEqual(recovery["remaining_before_pause"], 0)
        self.assertEqual(recovery["recovery_resets"], 2)
        self.assertEqual(recovery["last_error"], "Home Assistant service timed out")

    def test_runtime_stores_failure_and_reconciles_elapsed_pause(self):
        self.assertIn('item["last_error"] = str(exc)[:500]', AUTOMATIONS)
        route = MAIN[MAIN.index("async def read_autonomous_automations"):MAIN.index('@app.post("/api/automations/test-flow")')]
        self.assertIn('item.get("status") == "paused_failure"', route)
        self.assertIn('item["status"] = "armed" if item.get("enabled") else "draft"', route)
        self.assertIn("Automation failure pause elapsed", route)
        self.assertIn("if expired or recovered:", route)

    def test_recovery_center_is_plain_language_and_guarded(self):
        for marker in (
            'id="automation-recovery-paused"', 'id="automation-recovery-list"',
            "function renderRecovery()", "retry_available_at", "remaining_before_pause",
            "Reset and resume watching", "Previous failures remain in the audit history",
        ):
            self.assertIn(marker, WORKSPACE)
        self.assertIn(".automation-recovery-list", CSS)
        self.assertIn("#automation-recovery-paused", BROWSER)
        self.assertIn("/Home Assistant service timed out/i", BROWSER)


if __name__ == "__main__":
    unittest.main()
