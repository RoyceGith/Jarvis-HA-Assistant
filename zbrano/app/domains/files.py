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
SHARED_FOLDER_INDEX = ".folders.json"
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
    folder: str = "",
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    shared_folder = normalize_shared_folder(folder) if scope == "shared" else ""
    if shared_folder and shared_folder not in load_shared_folders():
        raise HTTPException(404, "Shared Files folder was not found")
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
        "folder": shared_folder,
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


def normalize_shared_folder(value: str) -> str:
    raw = str(value or "").replace("\\", "/").strip().strip("/")
    if not raw:
        return ""
    parts = [part.strip() for part in raw.split("/")]
    if (
        len(parts) > 8
        or any(not part or part in {".", ".."} or len(part) > 80 for part in parts)
        or any(any(ord(character) < 32 for character in part) for part in parts)
    ):
        raise HTTPException(400, "Choose a valid folder name")
    return "/".join(parts)


def _shared_folder_index_path() -> Path:
    return SHARED_FILE_ROOT / SHARED_FOLDER_INDEX


def load_shared_folders() -> set[str]:
    folders: set[str] = set()
    try:
        stored = json.loads(_shared_folder_index_path().read_text(encoding="utf-8"))
        if isinstance(stored, list):
            for item in stored:
                try:
                    normalized = normalize_shared_folder(str(item))
                    if normalized:
                        folders.add(normalized)
                except HTTPException:
                    continue
    except (OSError, json.JSONDecodeError):
        pass
    for metadata in list_files(SHARED_FILE_ROOT):
        try:
            folder = normalize_shared_folder(str(metadata.get("folder") or ""))
        except HTTPException:
            continue
        while folder:
            folders.add(folder)
            folder = folder.rsplit("/", 1)[0] if "/" in folder else ""
    return folders


def _save_shared_folders(folders: set[str]) -> None:
    SHARED_FILE_ROOT.mkdir(parents=True, exist_ok=True)
    _shared_folder_index_path().write_text(
        json.dumps(sorted(folders, key=str.casefold), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def create_shared_folder(parent: str, name: str) -> dict[str, Any]:
    parent_path = normalize_shared_folder(parent)
    folder_name = normalize_shared_folder(name)
    if "/" in folder_name:
        raise HTTPException(400, "Folder name cannot contain a slash")
    folders = load_shared_folders()
    if parent_path and parent_path not in folders:
        raise HTTPException(404, "Parent folder was not found")
    path = normalize_shared_folder(f"{parent_path}/{folder_name}" if parent_path else folder_name)
    if path in folders:
        raise HTTPException(409, "A folder with this name already exists here")
    folders.add(path)
    _save_shared_folders(folders)
    return {"name": folder_name, "path": path, "parent": parent_path}


def list_shared_folder_records(parent: str = "") -> list[dict[str, Any]]:
    parent_path = normalize_shared_folder(parent)
    prefix = f"{parent_path}/" if parent_path else ""
    records = []
    files = list_files(SHARED_FILE_ROOT)
    for path in load_shared_folders():
        if not path.startswith(prefix):
            continue
        remainder = path[len(prefix):]
        if not remainder or "/" in remainder:
            continue
        records.append({
            "name": remainder,
            "path": path,
            "file_count": sum(1 for item in files if str(item.get("folder") or "") == path),
        })
    return sorted(records, key=lambda item: item["name"].casefold())


def all_shared_folder_records() -> list[dict[str, Any]]:
    return [
        {"name": path.rsplit("/", 1)[-1], "path": path}
        for path in sorted(load_shared_folders(), key=str.casefold)
    ]


def shared_files_in_folder(folder: str, sort: str = "date", order: str = "desc") -> list[dict[str, Any]]:
    current = normalize_shared_folder(folder)
    return [item for item in list_shared_files(sort, order) if str(item.get("folder") or "") == current]


def move_shared_files(file_ids: list[str], folder: str) -> list[str]:
    target = normalize_shared_folder(folder)
    if target and target not in load_shared_folders():
        raise HTTPException(404, "Destination folder was not found")
    moved = []
    for file_id in file_ids:
        directory = SHARED_FILE_ROOT / file_id
        if not FILE_ID_RE.fullmatch(file_id) or not directory.is_dir():
            continue
        metadata = file_metadata(directory)
        if not metadata:
            continue
        metadata["folder"] = target
        (directory / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        moved.append(file_id)
    return moved


def delete_shared_folder(folder: str) -> str:
    target = normalize_shared_folder(folder)
    if not target:
        raise HTTPException(400, "The main Shared Files area cannot be deleted")
    folders = load_shared_folders()
    if target not in folders:
        raise HTTPException(404, "Folder was not found")
    if any(str(item.get("folder") or "") == target for item in list_files(SHARED_FILE_ROOT)):
        raise HTTPException(409, "Move or delete the files in this folder first")
    if any(path.startswith(target + "/") for path in folders):
        raise HTTPException(409, "Delete the folders inside this folder first")
    folders.remove(target)
    _save_shared_folders(folders)
    return target


def delete_shared_files(file_ids: list[str]) -> list[str]:
    deleted = []
    for file_id in file_ids:
        path = SHARED_FILE_ROOT / file_id
        if FILE_ID_RE.fullmatch(file_id) and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            deleted.append(file_id)
    return deleted
