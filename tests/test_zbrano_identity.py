from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_LEGACY_NAME = "jar" + "vis"


class ZbranoIdentityTests(unittest.TestCase):
    def test_tracked_paths_and_text_use_only_zbrano_identity(self):
        tracked = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout.split(b"\0")
        paths = [item.decode("utf-8") for item in tracked if item]
        self.assertFalse([
            path for path in paths if FORBIDDEN_LEGACY_NAME in path.lower()
        ])

        offenders = []
        for relative in paths:
            path = ROOT / relative
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if FORBIDDEN_LEGACY_NAME in text.lower():
                offenders.append(relative)
        self.assertFalse(offenders, f"Legacy identity remains in: {offenders}")

    def test_home_assistant_and_container_identity_are_zbrano(self):
        config = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
        dockerfile = (ROOT / "zbrano/Dockerfile").read_text(encoding="utf-8")
        self.assertIn('slug: "zbrano"', config)
        self.assertIn('image: "ghcr.io/roycegith/zbrano-core"', config)
        self.assertIn("WORKDIR /opt/zbrano", dockerfile)


if __name__ == "__main__":
    unittest.main()
