from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
from typing import Any

from fastapi import HTTPException, UploadFile


CHAT_UPLOAD_ROOT = Path("/data/uploads")
SHARED_FILE_ROOT = Path("/data/shared_files")
FILE_UPLOAD_MAX_BYTES = 25 * 1024 * 1024
FILE_TEXT_MAX_CHARS = 200000
FILE_ID_RE = re.compile(r"^[a-f0-9]{24}$")
TEXT_FILE_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".tsv", ".yaml", ".yml", ".xml",
    ".log", ".py", ".js", ".ts", ".css", ".html", ".ini", ".cfg",
}


def sanitize_session_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)[:128] or "default"


def new_file_id() -> str:
    seed = f"{time.time_ns()}:{os.urandom(16).hex()}"
    return hashlib.sha256(seed.encode()).hexdigest()[:24]


def file_metadata(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads((path / "metadata.json").read_text())
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


async def store_upload(
    upload: UploadFile,
    root: Path,
    scope: str,
    session_id: str = "",
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    name = Path(upload.filename or "upload.bin").name[:240] or "upload.bin"
    extension = Path(name).suffix.lower()[:20]
    file_id = new_file_id()
    directory = root / file_id
    directory.mkdir()
    destination = directory / ("original" + extension)
    size = 0
    digest = hashlib.sha256()
    try:
        with destination.open("wb") as stored:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > FILE_UPLOAD_MAX_BYTES:
                    raise HTTPException(413, "File exceeds 25 MB upload limit")
                digest.update(chunk)
                stored.write(chunk)
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    finally:
        await upload.close()
    if not size:
        shutil.rmtree(directory, ignore_errors=True)
        raise HTTPException(400, "Uploaded file is empty")
    mime_type = (upload.content_type or "application/octet-stream").lower()[:160]
    text_available = False
    if mime_type.startswith("text/") or extension in TEXT_FILE_EXTENSIONS:
        try:
            extracted = destination.read_text(errors="replace")[:FILE_TEXT_MAX_CHARS]
            (directory / "extracted.txt").write_text(extracted)
            text_available = True
        except OSError:
            pass
    metadata = {
        "file_id": file_id,
        "name": name,
        "scope": scope,
        "session_id": session_id if scope == "chat" else None,
        "mime_type": mime_type,
        "size": size,
        "sha256": digest.hexdigest(),
        "created_at": time.time(),
        "stored_name": destination.name,
        "text_available": text_available,
    }
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def list_files(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    return [
        metadata
        for path in root.iterdir()
        if path.is_dir() and (metadata := file_metadata(path))
    ]


def attachment_context(session_id: str, file_ids: list[str]) -> str:
    attached = []
    for file_id in file_ids[:20]:
        if not FILE_ID_RE.fullmatch(file_id):
            continue
        directory = next((
            path
            for path in (
                SHARED_FILE_ROOT / file_id,
                CHAT_UPLOAD_ROOT / sanitize_session_id(session_id) / file_id,
            )
            if path.is_dir()
        ), None)
        if not directory or not (metadata := file_metadata(directory)):
            continue
        header = (
            f"File: {metadata.get('name')} (id={file_id}, scope={metadata.get('scope')}, "
            f"type={metadata.get('mime_type')}, bytes={metadata.get('size')})"
        )
        extracted = directory / "extracted.txt"
        body = (
            extracted.read_text(errors="replace")[:FILE_TEXT_MAX_CHARS]
            if extracted.exists()
            else "[Stored safely; text extraction is not available for this file type yet.]"
        )
        attached.append(header + "\n" + body)
    return "\n\n--- Attached file context ---\n" + "\n\n".join(attached) if attached else ""


def chat_upload_path(session_id: str) -> Path:
    return CHAT_UPLOAD_ROOT / sanitize_session_id(session_id)


def clear_chat_files(session_id: str | None = None) -> None:
    target = chat_upload_path(session_id) if session_id is not None else CHAT_UPLOAD_ROOT
    shutil.rmtree(target, ignore_errors=True)


def list_shared_files(sort: str = "date", order: str = "desc") -> list[dict[str, Any]]:
    files = list_files(SHARED_FILE_ROOT)
    reverse = order.lower() != "asc"
    key = (
        (lambda item: str(item.get("name") or "").lower())
        if sort.lower() == "name"
        else (lambda item: float(item.get("created_at") or 0))
    )
    files.sort(key=key, reverse=reverse)
    return files


def delete_shared_files(file_ids: list[str]) -> list[str]:
    deleted = []
    for file_id in file_ids:
        path = SHARED_FILE_ROOT / file_id
        if FILE_ID_RE.fullmatch(file_id) and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            deleted.append(file_id)
    return deleted
