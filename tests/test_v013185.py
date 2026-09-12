import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
CONTRACT = (ROOT / "zbrano/validate_release_contract.py").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/build.yaml").read_text(encoding="utf-8")
PUBLIC = (ROOT / "distribution/public-repository/README.md").read_text(encoding="utf-8")
APP_GUIDE = (ROOT / "distribution/public-repository/zbrano/README.md").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "distribution/public-repository/zbrano/CHANGELOG.md").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class MultiArchitectureReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.234"', CONFIG)
        self.assertIn('version="0.13.234"', MAIN)
        self.assertIn("HUD 0.13.234", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.234")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.233")
        self.assertTrue(CHANGELOG.startswith("# Change log\n\n## 0.13.234"))

    def test_metadata_supports_both_modern_home_assistant_architectures(self):
        arch_block = re.search(r"^arch:\s*\n((?:  - .+\n?)+)", CONFIG, re.MULTILINE)
        self.assertIsNotNone(arch_block)
        self.assertEqual(
            re.findall(r"^  -\s+([a-z0-9_]+)\s*$", arch_block.group(1), re.MULTILINE),
            ["aarch64", "amd64"],
        )

    def test_release_contract_requires_exact_multi_architecture_list(self):
        self.assertIn('architectures != ["aarch64", "amd64"]', CONTRACT)
        self.assertIn("', '.join(architectures)", CONTRACT)

    def test_official_workflow_builds_and_publishes_the_architecture_matrix(self):
        for marker in (
            "prepare-multi-arch-matrix@2026.06.0",
            "arch: ${{ matrix.arch }}",
            "publish-multi-arch-manifest@2026.06.0",
            "architectures: ${{ steps.info.outputs.architectures }}",
        ):
            self.assertIn(marker, WORKFLOW)

    def test_public_guides_name_both_supported_platforms(self):
        self.assertIn("Platforms: **Home Assistant · aarch64 · amd64**", PUBLIC)
        self.assertIn("64-bit PCs, servers, and virtual machines", PUBLIC)
        self.assertIn("supports `aarch64` and `amd64`", APP_GUIDE)


if __name__ == "__main__":
    unittest.main()
