import json
from pathlib import Path
import unittest

from zbrano.app.services.entity_policy import normalize_entity_policy_enabled


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "zbrano/app/static/js/core.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "zbrano/tests/test_app_integration.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class ConsistentEntityPermissionReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.243"', CONFIG)
        self.assertIn('version="0.13.243"', MAIN)
        self.assertIn("HUD 0.13.243", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.243")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.242")

    def test_do_not_allow_revokes_the_browser_permission(self):
        self.assertIn('if (review.access === "restricted")', CORE)
        self.assertIn("review.selected = false", CORE)
        self.assertIn("checkbox.checked = false", CORE)
        self.assertIn('item.selected && item.access !== "restricted"', CORE)
        self.assertIn('review.selected && review.access !== "restricted"', CORE)

    def test_checking_a_blocked_entity_chooses_a_safe_read_level(self):
        self.assertIn("function defaultAllowedEntityAccess(entity)", CORE)
        self.assertIn("review.access = defaultAllowedEntityAccess(entity)", CORE)
        self.assertIn("accessSelect.value = review.access", CORE)
        self.assertIn("selectOption('restricted')", BROWSER)
        self.assertIn("inputValue(), 'state_only'", BROWSER)

    def test_api_normalizes_restricted_access_to_disabled(self):
        self.assertFalse(normalize_entity_policy_enabled(True, "restricted"))
        self.assertFalse(normalize_entity_policy_enabled(False, "read_only"))
        self.assertTrue(normalize_entity_policy_enabled(True, "read_only"))
        self.assertIn("enabled = normalize_entity_policy_enabled(request.enabled, request.access)", MAIN)
        self.assertIn('"enabled": enabled', MAIN)
        self.assertIn("test_do_not_allow_cannot_remain_enabled_in_entity_policy", INTEGRATION)
        self.assertIn('self.assertIsNone(blocked.json()["effective_access"])', INTEGRATION)


if __name__ == "__main__":
    unittest.main()
