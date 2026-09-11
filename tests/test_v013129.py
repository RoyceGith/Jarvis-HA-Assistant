import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "zbrano/app/static/js/core.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class TextboxFocusReleaseTests(unittest.TestCase):
    def test_placeholder_hides_only_while_field_is_focused(self):
        self.assertIn('document.addEventListener("focus"', CORE)
        self.assertIn('field.setAttribute("placeholder", "")', CORE)
        self.assertIn('document.addEventListener("blur"', CORE)
        self.assertIn('field.dataset.zbranoPlaceholder', CORE)
        self.assertNotIn('field.value = ""', CORE)

    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.220")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.219")


if __name__ == "__main__":
    unittest.main()
