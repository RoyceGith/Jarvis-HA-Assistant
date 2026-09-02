import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
DOMAIN = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationPauseResumeReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.126"', CONFIG)
        self.assertIn('version="0.13.126"', MAIN)
        self.assertIn("HUD 0.13.126", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.126")

    def test_pause_domain_preserves_definition_and_records_state(self):
        self.assertIn("def _pause_automation(automation_id: str, source: str)", DOMAIN)
        self.assertIn('automation["enabled"] = False', DOMAIN)
        self.assertIn('automation["status"] = "paused"', DOMAIN)
        self.assertIn('"configuration", f"Automation paused:', DOMAIN)
        self.assertIn('_automation_save(data)', DOMAIN)

    def test_pause_route_is_narrow_and_activate_route_is_retained(self):
        self.assertIn("_pause_automation,", MAIN)
        self.assertIn('@app.post("/api/automations/{automation_id}/pause")', MAIN)
        self.assertIn('return _pause_automation(automation_id, "interface_confirmation")', MAIN)
        self.assertIn('@app.post("/api/automations/{automation_id}/activate")', MAIN)

    def test_library_exposes_pause_and_resume_by_current_state(self):
        self.assertIn('data-auto-pause="${esc(item.id)}">Pause', WORKSPACE)
        self.assertIn('data-auto-activation-label="Resume">Resume', WORKSPACE)
        self.assertIn('Live evaluation and new actions will stop immediately', WORKSPACE)
        self.assertIn('/pause`,{method:"POST"}', WORKSPACE)
        self.assertIn('verb=activateDraft.dataset.autoActivationLabel||"Enable"', WORKSPACE)

    def test_browser_exercises_confirmed_pause_and_resume(self):
        self.assertIn('/api/automations/active-flow/pause', BROWSER)
        self.assertIn('{enabled: false, status: "paused"', BROWSER)
        self.assertIn('data-auto-pause="active-flow"', BROWSER)
        self.assertIn('data-auto-activation-label="Resume"', BROWSER)
        self.assertIn("pauseDialog.accept()", BROWSER)
        self.assertIn("resumeDialog.accept()", BROWSER)

    def test_release_history_includes_v01389(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.125")


if __name__ == "__main__":
    unittest.main()
