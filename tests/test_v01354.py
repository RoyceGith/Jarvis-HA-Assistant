import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "zbrano/Dockerfile").read_text(encoding="utf-8")
REPOSITORY = (ROOT / "repository.yaml").read_text(encoding="utf-8")
BOUNDARY = (ROOT / "docs/REPOSITORY_BOUNDARIES.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class RepositorySplitReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.235"', CONFIG)
        self.assertIn('version="0.13.235"', MAIN)
        self.assertIn("HUD 0.13.235", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.235")

    def test_private_core_and_public_distribution_are_distinct(self):
        self.assertIn("RoyceGith/ZBRANO_Core", MANIFEST["source"])
        self.assertIn("github.com/RoyceGith/ZBRANO_Core", DOCKERFILE)
        self.assertIn("github.com/ZBRANO-HOME/ZBRANO_HA_Assistant", REPOSITORY)
        self.assertIn("thin public update repository", BOUNDARY)

    def test_home_assistant_compatibility_image_is_unchanged(self):
        self.assertIn("ghcr.io/roycegith/zbrano-core", CONFIG)

    def test_public_repository_export_is_an_explicit_five_file_allowlist(self):
        with tempfile.TemporaryDirectory() as temporary:
            subprocess.run(
                [sys.executable, str(ROOT / "tools/export_public_repository.py"), temporary],
                check=True,
                capture_output=True,
                text=True,
            )
            exported = {
                path.relative_to(temporary).as_posix()
                for path in Path(temporary).rglob("*")
                if path.is_file()
            }
        self.assertEqual(exported, {
            "README.md",
            "repository.yaml",
            "zbrano/CHANGELOG.md",
            "zbrano/README.md",
            "zbrano/config.yaml",
        })

    def test_release_history_includes_v01353(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.234")


if __name__ == "__main__":
    unittest.main()
