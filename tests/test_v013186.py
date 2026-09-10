import json
from pathlib import Path
import re
import unittest

from jarvis.validate_release_contract import yaml_section_keys


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
I18N = (ROOT / "jarvis/app/static/js/i18n.js").read_text(encoding="utf-8")
VOICE = (ROOT / "jarvis/app/static/js/voice/proactive.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "jarvis/validate_release_contract.py").read_text(encoding="utf-8")
BOUNDARY = (ROOT / "validate_public_repo.py").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "distribution/public-repository/jarvis/CHANGELOG.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class MultilingualFoundationReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.200"', CONFIG)
        self.assertIn('version="0.13.200"', MAIN)
        self.assertIn("HUD 0.13.200", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.200")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.199")
        self.assertTrue(CHANGELOG.startswith("# Change log\n\n## 0.13.200"))

    def test_language_selector_has_supported_choices(self):
        select = re.search(r'<select id="preferred-language"[^>]*>(.*?)</select>', HTML, re.DOTALL)
        self.assertIsNotNone(select)
        self.assertEqual(
            re.findall(r'<option value="([^"]+)"', select.group(1)),
            ["auto", "English", "Greek", "Italian", "French"],
        )
        self.assertIn("Ελληνικά", select.group(1))
        self.assertIn("Italiano", select.group(1))
        self.assertIn("Français", select.group(1))

    def test_localization_runs_before_feature_scripts(self):
        self.assertLess(HTML.index('src="js/i18n.js"'), HTML.index('src="js/about.js"'))
        self.assertLess(HTML.index('src="js/i18n.js"'), HTML.index('src="js/core.js"'))

    def test_runtime_supports_detection_switching_and_english_fallback(self):
        for marker in (
            'Object.freeze({en: "English", el: "Greek", it: "Italian", fr: "French"})',
            "function browserLocale()",
            'localStorage.setItem("zbrano_interface_language_v1", preference)',
            "new MutationObserver",
            'return supported[candidate] ? candidate : "en"',
            'window.ZbranoI18n = Object.freeze',
        ):
            self.assertIn(marker, I18N)

    def test_runtime_protects_user_and_home_assistant_content(self):
        self.assertIn("#messages", I18N)
        self.assertIn("#chat-list", I18N)
        self.assertIn("#entity-rows", I18N)
        self.assertIn("[data-i18n-ignore]", I18N)

    def test_voice_recognition_is_independent_from_interface_locale(self):
        self.assertIn('return navigator.language||navigator.languages?.[0]||"en-US"', VOICE)
        self.assertNotIn("jarvisPreferences?.preferred_language", VOICE)

    def test_every_home_assistant_translation_matches_the_configuration(self):
        schema_keys = yaml_section_keys(CONFIG, "schema")
        self.assertEqual(len(schema_keys), 20)
        for language in ("en", "el", "it", "fr"):
            translation = (ROOT / f"jarvis/translations/{language}.yaml").read_text(encoding="utf-8")
            self.assertEqual(yaml_section_keys(translation, "configuration"), schema_keys)
            for key in schema_keys:
                self.assertRegex(
                    translation,
                    rf"(?m)^  {re.escape(key)}:\n    name: \S.+\n    description: \S.+$",
                )

    def test_release_validators_ship_all_four_translation_files(self):
        self.assertIn('TRANSLATION_LANGUAGES = ("en", "el", "it", "fr")', CONTRACT)
        for language in ("en", "el", "it", "fr"):
            self.assertIn(f'"jarvis/translations/{language}.yaml"', BOUNDARY)


if __name__ == "__main__":
    unittest.main()
