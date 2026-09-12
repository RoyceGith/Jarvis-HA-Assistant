import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano/app/static/css/base.css").read_text(encoding="utf-8")
SHARED_JS = (ROOT / "zbrano/app/static/js/files/shared-files-recovery.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class RefinedSharedFilesReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.224"', CONFIG)
        self.assertIn('version="0.13.224"', MAIN)
        self.assertIn("HUD 0.13.224", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.224")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.223")

    def test_shared_files_has_refined_library_hierarchy(self):
        for marker in ('class="shared-files-header"', 'class="shared-files-commandbar"', 'class="shared-upload-primary"', 'class="table-wrap shared-files-table-wrap"'):
            self.assertIn(marker, INDEX)
        self.assertIn(".shared-files-panel { display:flex", CSS)
        self.assertIn(".shared-upload-primary {", CSS)
        self.assertIn(".shared-files-table tbody tr:hover", CSS)

    def test_file_rows_use_polished_type_and_size_metadata(self):
        self.assertIn("const formatBytes = value =>", SHARED_JS)
        self.assertIn("const fileKind = file =>", SHARED_JS)
        self.assertIn('class="shared-file-icon"', SHARED_JS)
        self.assertIn('class="shared-file-date"', SHARED_JS)

    def test_controls_regroup_responsively(self):
        self.assertIn("@media(max-width:900px){.shared-files-header,.shared-files-commandbar", CSS)


if __name__ == "__main__":
    unittest.main()
