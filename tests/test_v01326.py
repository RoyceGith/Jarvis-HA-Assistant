import asyncio
import io
from pathlib import Path
import json
import sys
import tempfile
import types
import unittest

try:
    import fastapi  # noqa: F401
except ModuleNotFoundError:
    fastapi_stub = types.ModuleType("fastapi")
    fastapi_stub.HTTPException = RuntimeError
    fastapi_stub.UploadFile = object
    sys.modules["fastapi"] = fastapi_stub

from jarvis.app.domains import files


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
FILES = (APP / "domains/files.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class FakeUpload:
    def __init__(self, filename: str, content: bytes, content_type: str):
        self.filename = filename
        self.content_type = content_type
        self._content = io.BytesIO(content)

    async def read(self, size: int) -> bytes:
        return self._content.read(size)

    async def close(self) -> None:
        self._content.close()


class FilesDomainBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.48"', CONFIG)
        self.assertIn('version="0.13.48"', MAIN)
        self.assertIn("HUD 0.13.48", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.48")

    def test_file_storage_is_outside_composition_root(self):
        self.assertNotIn("async def _store(", MAIN)
        self.assertNotIn("def attachment_context(", MAIN)
        self.assertIn("async def store_upload(", FILES)
        self.assertIn("def attachment_context(", FILES)
        self.assertIn('CHAT_UPLOAD_ROOT = Path("/data/uploads")', FILES)
        self.assertIn('SHARED_FILE_ROOT = Path("/data/shared_files")', FILES)

    def test_upload_context_list_and_delete_contract(self):
        original_chat_root = files.CHAT_UPLOAD_ROOT
        original_shared_root = files.SHARED_FILE_ROOT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files.CHAT_UPLOAD_ROOT = root / "uploads"
            files.SHARED_FILE_ROOT = root / "shared_files"
            try:
                chat_upload = FakeUpload("note.txt", b"hello ZBRANO", "text/plain")
                metadata = asyncio.run(files.store_upload(
                    chat_upload,
                    files.chat_upload_path("session/one"),
                    "chat",
                    "session/one",
                ))
                context = files.attachment_context("session/one", [metadata["file_id"]])
                self.assertIn("hello ZBRANO", context)
                self.assertEqual(files.list_files(files.chat_upload_path("session/one"))[0]["name"], "note.txt")

                shared_upload = FakeUpload("shared.md", b"shared", "text/markdown")
                shared = asyncio.run(files.store_upload(shared_upload, files.SHARED_FILE_ROOT, "shared"))
                self.assertEqual(files.delete_shared_files([shared["file_id"]]), [shared["file_id"]])
                self.assertFalse((files.SHARED_FILE_ROOT / shared["file_id"]).exists())
            finally:
                files.CHAT_UPLOAD_ROOT = original_chat_root
                files.SHARED_FILE_ROOT = original_shared_root

    def test_conversation_cleanup_is_explicitly_wired(self):
        self.assertIn("clear_chat_files_fn=clear_chat_files", MAIN)
        self.assertIn("clear_chat_files(session_id)", (APP / "domains/conversations.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
