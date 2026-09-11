import json
from pathlib import Path
import re
import unittest

from jarvis.validate_release_contract import yaml_section_keys


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
TRANSLATIONS = (ROOT / "jarvis/translations/en.yaml").read_text(encoding="utf-8")
CONTRACT = (ROOT / "jarvis/validate_release_contract.py").read_text(encoding="utf-8")
BOUNDARY = (ROOT / "validate_public_repo.py").read_text(encoding="utf-8")
PUBLIC_README = (ROOT / "distribution/public-repository/README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class FriendlyHomeAssistantConfigurationReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.214"', CONFIG)
        self.assertIn('version="0.13.214"', MAIN)
        self.assertIn("HUD 0.13.214", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.214")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.213")

    def test_every_home_assistant_option_has_friendly_copy(self):
        option_keys = yaml_section_keys(CONFIG, "schema")
        translated_keys = yaml_section_keys(TRANSLATIONS, "configuration")
        self.assertEqual(translated_keys, option_keys)
        self.assertEqual(len(option_keys), 20)
        for key in option_keys:
            self.assertRegex(
                TRANSLATIONS,
                rf"(?m)^  {re.escape(key)}:\n    name: \S.+\n    description: \S.+$",
            )

    def test_sensitive_and_legacy_options_are_explained(self):
        for marker in (
            "The key stays in protected Home Assistant app configuration",
            "Choose OpenAI for the simplest setup",
            "Legacy sensor device IDs",
            "choose Sensor devices from Device Access inside ZBRANO",
            "Legacy control device IDs",
            "choose Control devices from Device Access inside ZBRANO",
        ):
            self.assertIn(marker, TRANSLATIONS)

    def test_release_checks_protect_the_shipped_translation_file(self):
        self.assertIn('ENGLISH_TRANSLATIONS = APP_ROOT / "translations" / "en.yaml"', CONTRACT)
        self.assertIn('translation_keys != schema_keys', CONTRACT)
        self.assertIn('"jarvis/translations/en.yaml"', BOUNDARY)
        self.assertIn("Path(sys.argv[1]).resolve()", BOUNDARY)
        self.assertIn("unexpected file in thin public distribution", BOUNDARY)

    def test_public_installation_steps_use_device_access_language(self):
        self.assertIn("add your OpenAI or OpenRouter API key", PUBLIC_README)
        self.assertIn("choose Sensor or Control access", PUBLIC_README)


if __name__ == "__main__":
    unittest.main()
