from __future__ import annotations

import csv
import io
import re
import secrets
import time
from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException

from ..schemas import ContactRequest, ContactUpdateRequest


CONTACTS_STORAGE_PATH = Path("/data/zbrano_contacts.json")
CONTACTS_MAX_RECORDS = 2000
CONTACT_IMPORT_MAX_BYTES = 5 * 1024 * 1024

_plugin_load: Callable[[Path], dict[str, Any]] = lambda path: {}
_plugin_save: Callable[[Path, dict[str, Any]], Any] = lambda path, data: None
_birthday_store: Callable[[], dict[str, Any]] = lambda: {"birthdays": []}
_birthday_save: Callable[[dict[str, Any]], Any] = lambda data: None


def configure_contacts_domain(*, plugin_load, plugin_save, birthday_store_fn, birthday_save_fn) -> None:
    global _plugin_load, _plugin_save, _birthday_store, _birthday_save
    _plugin_load = plugin_load
    _plugin_save = plugin_save
    _birthday_store = birthday_store_fn
    _birthday_save = birthday_save_fn


def contacts_store() -> dict[str, Any]:
    data = _plugin_load(CONTACTS_STORAGE_PATH) or {}
    contacts = data.get("contacts") if isinstance(data.get("contacts"), list) else []
    return {"version": 1, "contacts": contacts[:CONTACTS_MAX_RECORDS]}


def _contacts_save(data: dict[str, Any]) -> None:
    contacts = list(data.get("contacts") or [])[:CONTACTS_MAX_RECORDS]
    contacts.sort(key=lambda item: (str(item.get("display_name") or "").casefold(), str(item.get("id") or "")))
    _plugin_save(CONTACTS_STORAGE_PATH, {"version": 1, "contacts": contacts})


def _clean_list(values: list[str] | None, limit: int = 20) -> list[str]:
    result: list[str] = []
    for raw in values or []:
        value = " ".join(str(raw or "").split())[:500]
        if value and value.casefold() not in {item.casefold() for item in result}:
            result.append(value)
    return result[:limit]


def _normalize_contact(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    base = dict(existing or {})
    base.update(payload)
    kind = str(base.get("kind") or "person").strip().lower()
    if kind not in {"person", "company"}:
        raise HTTPException(status_code=400, detail="Contact type must be person or company")
    for key in ("display_name", "given_name", "family_name", "company_name", "job_title", "relationship", "address", "website", "notes"):
        base[key] = " ".join(str(base.get(key) or "").split())
    display = base["display_name"] or base["company_name"] or " ".join(filter(None, (base["given_name"], base["family_name"])))
    if not display:
        raise HTTPException(status_code=400, detail="Contact name is required")
    base["display_name"] = display[:160]
    base["kind"] = kind
    base["phone_numbers"] = _clean_list(base.get("phone_numbers"))
    base["emails"] = _clean_list(base.get("emails"))
    accounts = []
    for entry in base.get("bank_accounts") or []:
        if not isinstance(entry, dict):
            continue
        clean = {key: " ".join(str(entry.get(key) or "").split())[:200] for key in ("label", "bank_name", "account_name", "iban", "account_number", "swift")}
        if any(clean.values()):
            accounts.append(clean)
    base["bank_accounts"] = accounts[:10]
    birthday = str(base.get("birthday") or "").strip()
    if birthday and not re.fullmatch(r"(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", birthday):
        raise HTTPException(status_code=400, detail="Birthday must use MM-DD")
    base["birthday"] = birthday
    year = base.get("birth_year")
    base["birth_year"] = int(year) if year not in (None, "") else None
    return base


def _public_contact(item: dict[str, Any], include_sensitive: bool = False) -> dict[str, Any]:
    result = dict(item)
    if not include_sensitive:
        result.pop("bank_accounts", None)
        result["has_bank_details"] = bool(item.get("bank_accounts"))
    return result


def reconcile_birthday_contacts() -> None:
    data = contacts_store()
    birthday_data = _birthday_store()
    changed_contacts = changed_birthdays = False
    for birthday in birthday_data.get("birthdays") or []:
        linked = next((item for item in data["contacts"] if item.get("id") == birthday.get("contact_id")), None)
        if not linked:
            linked = next((item for item in data["contacts"] if str(item.get("display_name") or "").casefold() == str(birthday.get("name") or "").casefold()), None)
        if not linked:
            now = time.time()
            linked = _normalize_contact({"kind": "person", "display_name": birthday.get("name") or "", "birthday": birthday.get("birthday") or "", "birth_year": birthday.get("birth_year"), "relationship": birthday.get("relationship") or ""})
            linked.update({"id": secrets.token_hex(12), "birthday_id": birthday.get("id"), "source": "birthdays", "created_at": now, "updated_at": now})
            data["contacts"].append(linked)
            changed_contacts = True
        if birthday.get("contact_id") != linked["id"]:
            birthday["contact_id"] = linked["id"]
            changed_birthdays = True
        if linked.get("birthday_id") != birthday.get("id"):
            linked["birthday_id"] = birthday.get("id")
            changed_contacts = True
    for contact in data["contacts"]:
        if not contact.get("birthday"):
            continue
        linked = next((item for item in birthday_data.get("birthdays") or [] if item.get("id") == contact.get("birthday_id") or item.get("contact_id") == contact.get("id")), None)
        if not linked:
            linked = next((item for item in birthday_data.get("birthdays") or [] if str(item.get("name") or "").casefold() == str(contact.get("display_name") or "").casefold()), None)
        if linked:
            if contact.get("birthday_id") != linked.get("id"):
                contact["birthday_id"] = linked.get("id")
                changed_contacts = True
            if linked.get("contact_id") != contact.get("id"):
                linked["contact_id"] = contact.get("id")
                changed_birthdays = True
            continue
        now = time.time()
        birthday_id = str(contact.get("birthday_id") or secrets.token_hex(12))
        birthday_data.setdefault("birthdays", []).append({
            "id": birthday_id, "contact_id": contact.get("id"),
            "name": contact.get("display_name") or "", "birthday": contact.get("birthday") or "",
            "birth_year": contact.get("birth_year"), "relationship": contact.get("relationship") or "",
            "reminder_days_before": [], "destination": "", "notes": "", "gift_ideas": "",
            "source": "contacts_recovery", "created_at": now, "updated_at": now, "deliveries": {},
        })
        contact["birthday_id"] = birthday_id
        changed_contacts = changed_birthdays = True
    if changed_contacts:
        _contacts_save(data)
    if changed_birthdays:
        _birthday_save(birthday_data)


def list_contacts(query: str = "", include_sensitive: bool = False) -> dict[str, Any]:
    reconcile_birthday_contacts()
    normalized = " ".join(str(query or "").casefold().split())
    matches = []
    for item in contacts_store()["contacts"]:
        haystack = " ".join((str(item.get("display_name") or ""), str(item.get("given_name") or ""), str(item.get("family_name") or ""), str(item.get("company_name") or ""), str(item.get("relationship") or ""), " ".join(item.get("emails") or []), " ".join(item.get("phone_numbers") or []))).casefold()
        if not normalized or normalized in haystack:
            matches.append(_public_contact(item, include_sensitive))
    return {"contacts": matches, "count": len(matches), "query": query}


def _sync_contact_birthday(contact: dict[str, Any]) -> None:
    birthday_data = _birthday_store()
    birthdays = birthday_data.get("birthdays") or []
    linked = next((item for item in birthdays if item.get("contact_id") == contact["id"]), None)
    if not linked:
        linked = next((item for item in birthdays if str(item.get("name") or "").casefold() == contact["display_name"].casefold()), None)
    if not contact.get("birthday"):
        if linked and linked.get("contact_id") == contact["id"]:
            birthday_data["birthdays"] = [item for item in birthdays if item.get("id") != linked.get("id")]
            _birthday_save(birthday_data)
        contact.pop("birthday_id", None)
        return
    now = time.time()
    if linked:
        linked.update({"name": contact["display_name"], "birthday": contact["birthday"], "birth_year": contact.get("birth_year"), "relationship": contact.get("relationship") or linked.get("relationship", ""), "contact_id": contact["id"], "updated_at": now, "updated_by": "contacts"})
    else:
        linked = {"id": secrets.token_hex(12), "contact_id": contact["id"], "name": contact["display_name"], "birthday": contact["birthday"], "birth_year": contact.get("birth_year"), "relationship": contact.get("relationship", ""), "reminder_days_before": [], "destination": "", "notes": "", "gift_ideas": "", "source": "contacts", "created_at": now, "updated_at": now, "deliveries": {}}
        birthdays.append(linked)
    contact["birthday_id"] = linked["id"]
    _birthday_save(birthday_data)


def create_contact(request: ContactRequest, source: str = "interface") -> dict[str, Any]:
    data = contacts_store()
    item = _normalize_contact(request.model_dump())
    duplicate = next((entry for entry in data["contacts"] if str(entry.get("display_name") or "").casefold() == item["display_name"].casefold() and str(entry.get("kind") or "person") == item["kind"]), None)
    if duplicate:
        return {"created": False, "deduplicated": True, "contact": _public_contact(duplicate, True)}
    now = time.time()
    item.update({"id": secrets.token_hex(12), "source": source, "created_at": now, "updated_at": now})
    _sync_contact_birthday(item)
    data["contacts"].append(item)
    _contacts_save(data)
    return {"created": True, "deduplicated": False, "contact": _public_contact(item, True)}


def update_contact(contact_id: str, request: ContactUpdateRequest, source: str = "interface") -> dict[str, Any]:
    data = contacts_store()
    current = next((item for item in data["contacts"] if item.get("id") == contact_id), None)
    if not current:
        raise HTTPException(status_code=404, detail="Contact not found")
    updated = _normalize_contact(request.model_dump(exclude_unset=True), current)
    updated["updated_at"] = time.time()
    updated["updated_by"] = source
    _sync_contact_birthday(updated)
    current.clear()
    current.update(updated)
    _contacts_save(data)
    return {"updated": True, "contact": _public_contact(current, True)}


def delete_contact(contact_id: str) -> dict[str, Any]:
    data = contacts_store()
    item = next((entry for entry in data["contacts"] if entry.get("id") == contact_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Contact not found")
    data["contacts"] = [entry for entry in data["contacts"] if entry.get("id") != contact_id]
    _contacts_save(data)
    birthday_data = _birthday_store()
    birthday_data["birthdays"] = [entry for entry in birthday_data.get("birthdays") or [] if entry.get("contact_id") != contact_id]
    _birthday_save(birthday_data)
    return {"deleted": True, "contact": _public_contact(item)}


def _parse_vcard(text: str) -> list[dict[str, Any]]:
    unfolded = re.sub(r"\r?\n[ \t]", "", text)
    records = []
    for block in re.findall(r"BEGIN:VCARD(.*?)END:VCARD", unfolded, flags=re.I | re.S):
        values: dict[str, list[str]] = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            values.setdefault(key.split(";", 1)[0].upper(), []).append(value.replace("\\n", "\n").replace("\\,", ","))
        name_parts = (values.get("N") or [""])[0].split(";")
        birthday_raw = (values.get("BDAY") or [""])[0].replace("--", "")
        match = re.search(r"(?:(\d{4})-)?(\d{2})-(\d{2})", birthday_raw)
        records.append({"kind": "company" if values.get("ORG") and not values.get("FN") else "person", "display_name": (values.get("FN") or values.get("ORG") or [""])[0], "family_name": name_parts[0] if name_parts else "", "given_name": name_parts[1] if len(name_parts) > 1 else "", "company_name": (values.get("ORG") or [""])[0].split(";", 1)[0], "phone_numbers": values.get("TEL", []), "emails": values.get("EMAIL", []), "birthday": f"{match.group(2)}-{match.group(3)}" if match else "", "birth_year": int(match.group(1)) if match and match.group(1) else None, "address": ", ".join(filter(None, (values.get("ADR") or [""])[0].split(";"))), "website": (values.get("URL") or [""])[0], "notes": (values.get("NOTE") or [""])[0]})
    return records


def _parse_csv(text: str) -> list[dict[str, Any]]:
    rows = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    records = []
    for row in rows:
        lowered = {str(key or "").strip().casefold(): str(value or "").strip() for key, value in row.items()}
        pick = lambda *names: next((lowered[name] for name in names if lowered.get(name)), "")
        display = pick("name", "full name", "display name", "organization name", "company")
        birthday_raw = pick("birthday", "birth date", "date of birth")
        match = re.search(r"(?:(\d{4})[-/])?(\d{1,2})[-/](\d{1,2})", birthday_raw)
        emails = [value for key, value in lowered.items() if "email" in key and value]
        phones = [value for key, value in lowered.items() if "phone" in key and value]
        records.append({"kind": "company" if pick("organization name", "company") and not pick("first name", "given name") else "person", "display_name": display, "given_name": pick("first name", "given name"), "family_name": pick("last name", "family name"), "company_name": pick("organization name", "company"), "phone_numbers": phones, "emails": emails, "birthday": f"{int(match.group(2)):02d}-{int(match.group(3)):02d}" if match else "", "birth_year": int(match.group(1)) if match and match.group(1) else None, "address": pick("address", "address 1 - formatted"), "website": pick("website", "url"), "notes": pick("notes")})
    return records


def import_contacts(content: bytes, filename: str, source: str = "file_import") -> dict[str, Any]:
    if len(content) > CONTACT_IMPORT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Contact file exceeds the 5 MB limit")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Contact file must be UTF-8 CSV or vCard") from exc
    records = _parse_vcard(text) if filename.lower().endswith((".vcf", ".vcard")) or "BEGIN:VCARD" in text.upper() else _parse_csv(text)
    created = updated = skipped = 0
    for raw in records[:CONTACTS_MAX_RECORDS]:
        try:
            normalized = _normalize_contact(raw)
        except HTTPException:
            skipped += 1
            continue
        matches = list_contacts(normalized["display_name"], include_sensitive=True)["contacts"]
        exact = next((item for item in matches if item["display_name"].casefold() == normalized["display_name"].casefold()), None)
        if exact:
            update_contact(exact["id"], ContactUpdateRequest(**normalized), source=source)
            updated += 1
        else:
            create_contact(ContactRequest(**normalized), source=source)
            created += 1
    return {"imported": created + updated, "created": created, "updated": updated, "skipped": skipped, "source": source}


def sync_contact_from_birthday(item: dict[str, Any], deleted: bool = False) -> None:
    data = contacts_store()
    contact = next((entry for entry in data["contacts"] if entry.get("id") == item.get("contact_id")), None)
    if not contact:
        contact = next((entry for entry in data["contacts"] if str(entry.get("display_name") or "").casefold() == str(item.get("name") or "").casefold()), None)
    if deleted:
        if contact and contact.get("birthday_id") == item.get("id"):
            contact["birthday"] = ""
            contact["birth_year"] = None
            contact.pop("birthday_id", None)
            contact["updated_at"] = time.time()
            _contacts_save(data)
        return
    if contact:
        contact.update({"display_name": item.get("name") or contact["display_name"], "birthday": item.get("birthday") or "", "birth_year": item.get("birth_year"), "relationship": item.get("relationship") or contact.get("relationship", ""), "birthday_id": item.get("id"), "updated_at": time.time(), "updated_by": "birthdays"})
    else:
        now = time.time()
        contact = _normalize_contact({"kind": "person", "display_name": item.get("name") or "", "birthday": item.get("birthday") or "", "birth_year": item.get("birth_year"), "relationship": item.get("relationship") or ""})
        contact.update({"id": secrets.token_hex(12), "birthday_id": item.get("id"), "source": "birthdays", "created_at": now, "updated_at": now})
        data["contacts"].append(contact)
    item["contact_id"] = contact["id"]
    _contacts_save(data)
