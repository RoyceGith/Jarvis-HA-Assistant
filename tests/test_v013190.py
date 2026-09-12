import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "distribution/public-repository/zbrano/CHANGELOG.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class ActionableEntityMatchingReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.225"', CONFIG)
        self.assertIn('version="0.13.225"', MAIN)
        self.assertIn("HUD 0.13.225", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.225")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.224")
        self.assertTrue(CHANGELOG.startswith("# Change log\n\n## 0.13.225"))

    def test_direct_power_matching_uses_safe_domains_and_semantic_priority(self):
        route = MAIN[MAIN.index("async def try_local_ha_route("):MAIN.index("async def run_zbrano(")]
        self.assertIn('safe_control_domains = {"light", "switch", "fan", "input_boolean", "climate"}', route)
        self.assertIn('preferred_domain = "climate"', route)
        self.assertIn('(100 if domain == preferred_domain else 0)', route)
        self.assertIn("max(control_rank(candidate) for candidate in control_matches)", route)


if __name__ == "__main__":
    unittest.main()
