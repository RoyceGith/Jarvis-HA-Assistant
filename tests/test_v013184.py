import json
from pathlib import Path
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
PUBLIC = (ROOT / "distribution/public-repository/README.md").read_text(encoding="utf-8")
APP_GUIDE = (ROOT / "distribution/public-repository/jarvis/README.md").read_text(encoding="utf-8")
BOUNDARY = (ROOT / "validate_public_repo.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def png_metadata(path: Path) -> tuple[int, int, int]:
    payload = path.read_bytes()
    if payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise AssertionError(f"{path.name} is not a valid PNG")
    width, height = struct.unpack(">II", payload[16:24])
    return width, height, payload[25]


class PublicPresentationAssetsReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.208"', CONFIG)
        self.assertIn('version="0.13.208"', MAIN)
        self.assertIn("HUD 0.13.208", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.208")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.207")

    def test_home_assistant_icon_is_bounded_transparent_png(self):
        path = ROOT / "jarvis/icon.png"
        self.assertEqual(png_metadata(path), (128, 128, 6))
        self.assertLess(path.stat().st_size, 100_000)

    def test_horizontal_logo_is_bounded_transparent_png(self):
        path = ROOT / "jarvis/logo.png"
        self.assertEqual(png_metadata(path), (511, 120, 6))
        self.assertLess(path.stat().st_size, 100_000)

    def test_public_guides_display_the_logo(self):
        self.assertIn("![ZBRANO](jarvis/logo.png)", PUBLIC)
        self.assertIn("![ZBRANO](logo.png)", APP_GUIDE)

    def test_public_boundary_requires_only_the_two_presentation_assets(self):
        for marker in (
            '"jarvis/icon.png": (128, 128)',
            '"jarvis/logo.png": (511, 120)',
            "public presentation asset must preserve transparency",
            "public presentation asset is too large",
        ):
            self.assertIn(marker, BOUNDARY)


if __name__ == "__main__":
    unittest.main()
