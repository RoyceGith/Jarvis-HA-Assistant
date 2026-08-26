from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "jarvis/validate_release_contract.py"
WORKFLOW = (ROOT / ".github/workflows/build.yaml").read_text(encoding="utf-8")


class ReleaseContractTests(unittest.TestCase):
    def test_canonical_release_contract_passes(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("Release contract validated", result.stdout)

    def test_workflow_validates_contract_before_reading_build_metadata(self):
        validation = "python3 jarvis/validate_release_contract.py"
        metadata = "home-assistant/actions/helpers/info@master"
        self.assertIn(validation, WORKFLOW)
        self.assertIn(metadata, WORKFLOW)
        self.assertLess(WORKFLOW.index(validation), WORKFLOW.index(metadata))


if __name__ == "__main__":
    unittest.main()
