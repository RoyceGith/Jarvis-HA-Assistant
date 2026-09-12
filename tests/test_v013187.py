import json
from pathlib import Path
import re
import unittest

from zbrano.validate_i18n_catalog import MINIMUM_PHRASES, object_literal


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
I18N = (ROOT / "zbrano/app/static/js/i18n.js").read_text(encoding="utf-8")
ADVANCED = (ROOT / "zbrano/app/static/js/i18n/catalog-advanced.js").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "zbrano/Dockerfile").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "distribution/public-repository/zbrano/CHANGELOG.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class ExpandedInterfaceLocalizationReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.223"', CONFIG)
        self.assertIn('version="0.13.223"', MAIN)
        self.assertIn("HUD 0.13.223", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.223")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.222")
        self.assertTrue(CHANGELOG.startswith("# Change log\n\n## 0.13.223"))

    def test_advanced_catalog_is_large_complete_and_loaded_early(self):
        base = object_literal(I18N, r"const rows = (\{.*?^  \});", "base")
        advanced = object_literal(ADVANCED, r"register\((\{.*?^\})\);", "advanced")
        self.assertFalse(set(base) & set(advanced))
        self.assertGreaterEqual(len(base) + len(advanced), MINIMUM_PHRASES)
        for phrase in ("Automation Studio", "Run required checks", "Notification Center", "Visual automations"):
            self.assertIn(phrase, {**base, **advanced})
        self.assertLess(HTML.index('src="js/i18n/catalog-advanced.js"'), HTML.index('src="js/about.js"'))

    def test_dynamic_content_and_attributes_are_relocalized(self):
        for marker in (
            "function register(entries)",
            'record.type === "attributes"',
            'attributeFilter: ["aria-label", "title", "placeholder"]',
            "const count = source.match",
            "const step = source.match",
        ):
            self.assertIn(marker, I18N)

    def test_dates_follow_selected_interface_locale(self):
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "zbrano/app/static/js").rglob("*.js")
        )
        self.assertIn("toLocaleDateString(window.ZbranoI18n?.locale || undefined", sources)
        self.assertIn("toLocaleTimeString(window.ZbranoI18n?.locale || undefined", sources)
        self.assertNotRegex(sources, r"toLocale(?:Date|Time)?String\(\[\]")
        self.assertNotIn(".toLocaleString()", sources)

    def test_container_build_gates_catalog_integrity(self):
        self.assertIn("COPY validate_i18n_catalog.py ./validate_i18n_catalog.py", DOCKERFILE)
        self.assertIn("python3 ./validate_i18n_catalog.py", DOCKERFILE)
        self.assertIn("rm ./validate_release_manifest.py ./validate_i18n_catalog.py", DOCKERFILE)

    def test_browser_checks_advanced_surfaces_and_protected_content(self):
        for marker in (
            'window.ZbranoI18n.t("Automation Studio")',
            "Όλα λειτουργούν ως ένας βοηθός",
            "Εκτέλεση διαγνωστικών",
            "User and assistant messages must not be translated",
        ):
            self.assertIn(marker, BROWSER)


if __name__ == "__main__":
    unittest.main()
