import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/build.yaml").read_text(encoding="utf-8")
VALIDATOR = (ROOT / "zbrano/validate_release_contract.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class ReleaseContractReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.228"', CONFIG)
        self.assertIn('version="0.13.228"', MAIN)
        self.assertIn("HUD 0.13.228", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.228")

    def test_release_contract_runs_before_build_metadata(self):
        command = "python3 zbrano/validate_release_contract.py"
        metadata = "home-assistant/actions/helpers/info@master"
        self.assertIn(command, WORKFLOW)
        self.assertLess(WORKFLOW.index(command), WORKFLOW.index(metadata))
        for marker in (
            "options/schema mismatch",
            "ARG BUILD_VERSION",
            "ingress_port",
            "publish-multi-arch-manifest@2026.06.0",
            "github.event_name == 'push' && github.ref == 'refs/heads/main'",
        ):
            self.assertIn(marker, VALIDATOR)

    def test_release_history_includes_previous_release(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.227")


if __name__ == "__main__":
    unittest.main()
