import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class SimpleConditionValueReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.232")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.231")

    def test_ordinary_check_defaults_to_entity_state(self):
        self.assertIn("Device or sensor state", WORKSPACE)
        self.assertNotIn('labelled("Which value?"', WORKSPACE)
        self.assertNotIn('labelled("Its value"', WORKSPACE)

    def test_attributes_are_available_but_collapsed_by_default(self):
        self.assertIn('class="automation-condition-advanced automation-inspector-more"', WORKSPACE)
        self.assertIn('advanced("Use a specific device attribute",attribute,Boolean(item.attribute))', WORKSPACE)
        self.assertIn('advanced("Use specific device attributes",attributes,Boolean(item.attribute||item.compare_attribute))', WORKSPACE)

    def test_existing_attribute_values_are_preserved(self):
        self.assertIn('value="${esc(item.attribute||"")}"', WORKSPACE)
        self.assertIn('value="${esc(item.compare_attribute||"")}"', WORKSPACE)

    def test_browser_verifies_else_if_attribute_is_not_a_common_field(self):
        self.assertIn("elseIfAdvanced", BROWSER)
        self.assertIn('elseIfAttribute.isVisible(), false', BROWSER)
        self.assertIn("Which value\\?", BROWSER)


if __name__ == "__main__":
    unittest.main()
