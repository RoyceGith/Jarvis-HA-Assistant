import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
ONBOARDING_JS = (ROOT / "jarvis/app/static/js/onboarding.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ActionableOnboardingReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.76"', CONFIG)
        self.assertIn('version="0.13.76"', MAIN)
        self.assertIn("HUD 0.13.76", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.76")

    def test_backend_check_route_has_a_closed_step_allowlist(self):
        section = MAIN[MAIN.index('@app.post("/api/onboarding/check/{step_id}")'):MAIN.index('@app.put("/api/settings")')]
        for step in ("home_assistant", "model", "entities", "voice", "memory", "plugins", "notifications"):
            self.assertIn(f'step_id == "{step}"', section)
        self.assertIn('raise HTTPException(status_code=404, detail="Unknown onboarding step")', section)

    def test_external_model_check_is_explicit_only(self):
        check_section = ONBOARDING_JS[ONBOARDING_JS.index("async function requestCheck"):ONBOARDING_JS.index("function render")]
        load_section = ONBOARDING_JS[ONBOARDING_JS.index("async function load"):ONBOARDING_JS.index("async function update")]
        self.assertIn('api/onboarding/check/', check_section)
        self.assertNotIn('api/onboarding/check/', load_section)
        self.assertIn('method: "POST"', check_section)

    def test_guided_actions_cover_product_setup_without_grinder(self):
        for label in ("Choose entities", "Configuration help", "Open voice test", "Open memory", "Open plugins", "Open notification test"):
            self.assertIn(label, ONBOARDING_JS)
        self.assertNotIn("grinder", ONBOARDING_JS.lower())

    def test_release_history_includes_v01359(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.75")


if __name__ == "__main__":
    unittest.main()
