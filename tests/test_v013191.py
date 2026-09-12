import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
VOICE = (ROOT / "zbrano/app/static/js/voice/proactive.js").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano/app/static/css/entity-columns.css").read_text(encoding="utf-8")
I18N = (ROOT / "zbrano/app/static/js/i18n.js").read_text(encoding="utf-8")
WAKE_README = (ROOT / "zbrano/models/wakeword/README.md").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "distribution/public-repository/zbrano/CHANGELOG.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class PortableWakeMethodReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.242"', CONFIG)
        self.assertIn('version="0.13.242"', MAIN)
        self.assertIn("HUD 0.13.242", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.242")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.241")
        self.assertTrue(CHANGELOG.startswith("# Change log\n\n## 0.13.242"))

    def test_browser_recognition_is_the_default_method(self):
        self.assertIn('id="wake-browser-activate" name="wake-detection-method" type="radio" checked', HTML)
        self.assertIn('id="wake-local-activate" name="wake-detection-method" type="radio"', HTML)
        self.assertIn("Recommended for every user", HTML)
        self.assertIn("Owner-tuned", HTML)
        self.assertIn(".wake-method-card:has(input:checked)", CSS)

    def test_existing_local_choice_is_preserved_and_both_methods_persist(self):
        self.assertIn('wakeLocalActivate.checked=localStorage.getItem("zbrano_wake_local_activate")==="true"', VOICE)
        self.assertIn("wakeBrowserActivate.checked=!wakeLocalActivate.checked", VOICE)
        self.assertIn("function selectWakeDetectionMethod(useLocal)", VOICE)
        self.assertIn('localStorage.setItem("zbrano_wake_local_activate",String(useLocal))', VOICE)

    def test_guidance_is_localized_and_licensing_boundary_is_explicit(self):
        self.assertIn('"Browser recognition":', I18N)
        self.assertIn('"Experimental local model":', I18N)
        self.assertIn("cannot retrain the experimental model", HTML)
        self.assertIn("It must not be", WAKE_README)
        self.assertIn("included in a commercial or premium package", WAKE_README)


if __name__ == "__main__":
    unittest.main()
