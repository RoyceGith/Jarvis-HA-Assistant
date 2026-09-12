import json
from pathlib import Path
import tempfile
import unittest

from fastapi import HTTPException

from zbrano.app.domains import files


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
SHARED_JS = (ROOT / "zbrano/app/static/js/files/shared-files-recovery.js").read_text(encoding="utf-8")
CONTROLLER = (ROOT / "zbrano/app/static/js/files/shared-files.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class SharedFileFoldersReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.223"', CONFIG)
        self.assertIn('version="0.13.223"', MAIN)
        self.assertIn("HUD 0.13.223", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.223")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.222")

    def test_folder_service_creates_lists_moves_and_safely_deletes(self):
        original = files.SHARED_FILE_ROOT
        with tempfile.TemporaryDirectory() as temporary:
            try:
                files.SHARED_FILE_ROOT = Path(temporary)
                files.create_shared_folder("", "Documents")
                files.create_shared_folder("Documents", "Receipts")
                file_id = "a" * 24
                directory = files.SHARED_FILE_ROOT / file_id
                directory.mkdir()
                (directory / "metadata.json").write_text(json.dumps({"file_id":file_id,"name":"bill.pdf","folder":""}), encoding="utf-8")
                self.assertEqual(files.list_shared_folder_records("")[0]["path"], "Documents")
                self.assertEqual(files.move_shared_files([file_id], "Documents/Receipts"), [file_id])
                self.assertEqual(files.shared_files_in_folder("Documents/Receipts")[0]["name"], "bill.pdf")
                with self.assertRaises(HTTPException):
                    files.delete_shared_folder("Documents/Receipts")
                files.move_shared_files([file_id], "")
                self.assertEqual(files.delete_shared_folder("Documents/Receipts"), "Documents/Receipts")
                self.assertEqual(files.delete_shared_folder("Documents"), "Documents")
            finally:
                files.SHARED_FILE_ROOT = original

    def test_folder_paths_are_bounded(self):
        for invalid in ("../Private", "One//Two", "A/../B", "x" * 81):
            with self.assertRaises(HTTPException):
                files.normalize_shared_folder(invalid)

    def test_shared_files_interface_exposes_folder_workflow(self):
        for marker in ('id="shared-breadcrumbs"', 'id="shared-new-folder"', 'id="shared-upload-here"', 'id="shared-move-target"'):
            self.assertIn(marker, INDEX)
        self.assertIn('body.append("folder", currentFolder)', SHARED_JS)
        self.assertIn('data-shared-folder=', SHARED_JS)
        self.assertIn('method:"PATCH"', CONTROLLER)


if __name__ == "__main__":
    unittest.main()
