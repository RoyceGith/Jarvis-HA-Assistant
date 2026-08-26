import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_public_repo", ROOT / "validate_public_repo.py")
BOUNDARY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BOUNDARY)


class PublicRepositoryBoundaryTests(unittest.TestCase):
    def test_current_tracked_tree_respects_boundary(self):
        self.assertEqual(BOUNDARY.validate(), [])

    def test_private_and_secret_paths_are_rejected(self):
        errors = BOUNDARY.validate([
            "private-services/billing.py",
            "Workshop-Memory-HA-App/config.yaml",
            ".env",
            "certificates/production.key",
        ])
        self.assertTrue(any("private path" in item for item in errors))
        self.assertTrue(any("secret-bearing filename" in item for item in errors))

    def test_documented_boundary_keeps_public_core_independent(self):
        text = (ROOT / "docs/REPOSITORY_BOUNDARIES.md").read_text(encoding="utf-8")
        self.assertIn("clean checkout must build without access to any private", text)
        self.assertIn("must not import private source code", text)


if __name__ == "__main__":
    unittest.main()
