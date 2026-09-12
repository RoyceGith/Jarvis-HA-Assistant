import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "zbrano/app/schemas.py").read_text(encoding="utf-8")
AGENT = (ROOT / "zbrano/app/services/agent_runtime.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano/app/static/css/interface-refresh.css").read_text(encoding="utf-8")
CORE = (ROOT / "zbrano/app/static/js/core.js").read_text(encoding="utf-8")
VOICE = (ROOT / "zbrano/app/static/js/voice/proactive.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class InterfaceLanguagePickerReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.222"', CONFIG)
        self.assertIn('version="0.13.222"', MAIN)
        self.assertIn("HUD 0.13.222", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.222")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.221")

    def test_flag_selector_is_in_the_top_right_runtime_header(self):
        runtime = HTML[HTML.index('<div class="runtime-status-stack">'):HTML.index("</header>")]
        self.assertIn('class="interface-language-picker"', runtime)
        self.assertLess(runtime.index('id="preferred-language"'), runtime.index('id="notification-inbox-shell"'))
        for marker in ("🌐", "🇬🇧", "🇬🇷", "🇮🇹", "🇫🇷"):
            self.assertIn(marker, runtime)
        responses = HTML[HTML.index('data-settings-category="responses"'):HTML.index('data-settings-category="search"')]
        self.assertNotIn('id="preferred-language"', responses)
        self.assertIn(".interface-language-picker select", CSS)
        self.assertIn("opacity: 0", CSS)

    def test_selection_changes_the_interface_and_persists_immediately(self):
        self.assertIn('window.ZbranoI18n?.setPreference(interfaceLanguage)', CORE)
        self.assertIn('fetch("api/settings/interface-language"', CORE)
        self.assertIn("class InterfaceLanguageUpdate", SCHEMAS)
        self.assertIn('@app.put("/api/settings/interface-language")', MAIN)
        self.assertIn('preferences["preferred_language"] = request.interface_language', MAIN)

    def test_interface_choice_does_not_force_chat_or_voice_language(self):
        self.assertNotIn('preferences["preferred_language"]', AGENT)
        self.assertIn("Reply in the language used by the user", AGENT)
        self.assertIn('return navigator.language||navigator.languages?.[0]||"en-US"', VOICE)
        self.assertNotIn("zbranoPreferences?.preferred_language", VOICE)


if __name__ == "__main__":
    unittest.main()
