from __future__ import annotations

import contextlib
import hashlib
import logging
from typing import Any, Callable

import httpx
from fastapi import HTTPException

from ..schemas import ContactRequest, ContactUpdateRequest


LOGGER = logging.getLogger(__name__)


GOOGLE_CONTACTS_RESOURCE_URL = "https://people.googleapis.com/v1"
GOOGLE_CONTACTS_OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
)

_oauth_records: Callable[[], dict[str, Any]] = lambda: {}
_plugin_secrets: Callable[[], dict[str, Any]] = lambda: {}
_plugin_registry: Callable[[], dict[str, Any]] = lambda: {}
_oauth_scope_set: Callable[[str], set[str]] = lambda raw: set()
_refresh_oauth_token: Callable[..., Any] = lambda plugin_id, force=False: False
_list_contacts: Callable[..., dict[str, Any]] = lambda query="", include_sensitive=True: {"contacts": []}
_create_contact: Callable[..., dict[str, Any]] = lambda request, source="google": {}
_update_contact: Callable[..., dict[str, Any]] = lambda contact_id, request, source="google": {}


def configure_google_contacts_domain(*, oauth_records_fn, plugin_secrets_fn, plugin_registry_fn, oauth_scope_set_fn, refresh_oauth_token_fn, list_contacts_fn, create_contact_fn, update_contact_fn) -> None:
    global _oauth_records, _plugin_secrets, _plugin_registry, _oauth_scope_set, _refresh_oauth_token, _list_contacts, _create_contact, _update_contact
    _oauth_records = oauth_records_fn
    _plugin_secrets = plugin_secrets_fn
    _plugin_registry = plugin_registry_fn
    _oauth_scope_set = oauth_scope_set_fn
    _refresh_oauth_token = refresh_oauth_token_fn
    _list_contacts = list_contacts_fn
    _create_contact = create_contact_fn
    _update_contact = update_contact_fn


def google_contacts_plugin_id() -> str:
    return hashlib.sha256(GOOGLE_CONTACTS_RESOURCE_URL.encode()).hexdigest()[:16]


def google_contacts_status() -> dict[str, Any]:
    plugin_id = google_contacts_plugin_id()
    record = _oauth_records().get(plugin_id) or {}
    connected = bool(_plugin_secrets().get(plugin_id) and set(GOOGLE_CONTACTS_OAUTH_SCOPES).issubset(_oauth_scope_set(record.get("scope"))))
    plugin = _plugin_registry().get(plugin_id) or {}
    return {"connected": connected, "account": str(plugin.get("oauth_account") or "")}


async def _access_token() -> str:
    plugin_id = google_contacts_plugin_id()
    await _refresh_oauth_token(plugin_id)
    token = str(_plugin_secrets().get(plugin_id) or "")
    record = _oauth_records().get(plugin_id) or {}
    if not token or not set(GOOGLE_CONTACTS_OAUTH_SCOPES).issubset(_oauth_scope_set(record.get("scope"))):
        raise PermissionError("Google Contacts is not connected with read-only Contacts permission")
    return token


def _primary(items: list[dict[str, Any]] | None) -> dict[str, Any]:
    values = [item for item in items or [] if isinstance(item, dict)]
    return next((item for item in values if (item.get("metadata") or {}).get("primary")), values[0] if values else {})


def _google_contact(person: dict[str, Any]) -> dict[str, Any]:
    name = _primary(person.get("names"))
    organization = _primary(person.get("organizations"))
    birthday_item = _primary(person.get("birthdays"))
    birthday_date = birthday_item.get("date") or {}
    address = _primary(person.get("addresses"))
    url = _primary(person.get("urls"))
    bio = _primary(person.get("biographies"))
    company = str(organization.get("name") or "")
    given = str(name.get("givenName") or "")
    family = str(name.get("familyName") or "")
    display = str(name.get("displayName") or company or " ".join(filter(None, (given, family))))
    month = day = 0
    try:
        month, day = int(birthday_date.get("month") or 0), int(birthday_date.get("day") or 0)
    except (TypeError, ValueError):
        pass
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        month = day = 0
    birth_year = None
    with contextlib.suppress(TypeError, ValueError):
        candidate_year = int(birthday_date.get("year") or 0)
        birth_year = candidate_year if 1800 <= candidate_year <= 2200 else None
    return {
        "kind": "company" if company and not (given or family) else "person",
        "display_name": display,
        "given_name": given,
        "family_name": family,
        "company_name": company,
        "job_title": str(organization.get("title") or ""),
        "phone_numbers": [str(item.get("value") or "") for item in person.get("phoneNumbers") or []],
        "emails": [str(item.get("value") or "") for item in person.get("emailAddresses") or []],
        "birthday": f"{month:02d}-{day:02d}" if month and day else "",
        "birth_year": birth_year,
        "relationship": "",
        "address": str(address.get("formattedValue") or ""),
        "website": str(url.get("value") or ""),
        "notes": str(bio.get("value") or ""),
        "bank_accounts": [],
    }


async def import_google_contacts() -> dict[str, Any]:
    plugin_id = google_contacts_plugin_id()
    token = await _access_token()
    people: list[dict[str, Any]] = []
    page_token = ""
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=8.0), follow_redirects=False) as client:
        for _ in range(20):
            params = {"personFields": "names,emailAddresses,phoneNumbers,birthdays,organizations,addresses,urls,biographies", "pageSize": 1000}
            if page_token:
                params["pageToken"] = page_token
            response = await client.get("https://people.googleapis.com/v1/people/me/connections", params=params, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 401 and await _refresh_oauth_token(plugin_id, force=True):
                token = str(_plugin_secrets().get(plugin_id) or "")
                response = await client.get("https://people.googleapis.com/v1/people/me/connections", params=params, headers={"Authorization": f"Bearer {token}"})
            if response.is_redirect:
                raise RuntimeError("Google People API redirects are blocked")
            if response.is_error:
                detail = ""
                with contextlib.suppress(ValueError, TypeError):
                    detail = str((response.json().get("error") or {}).get("message") or "")
                normalized_detail = detail.casefold()
                if response.status_code == 403 and any(marker in normalized_detail for marker in ("has not been used", "is disabled", "access_not_configured", "service_disabled")):
                    raise RuntimeError("Google People API is disabled. Enable People API in the same Google Cloud project as ZBRANO's OAuth client, wait a minute, then retry the import.")
                if response.status_code == 403:
                    raise RuntimeError(detail or "Google denied Contacts access. Reconnect Google Contacts and approve the read-only Contacts permission.")
                raise RuntimeError(detail or f"Google People API returned HTTP {response.status_code}")
            payload = response.json()
            people.extend(item for item in payload.get("connections") or [] if isinstance(item, dict))
            page_token = str(payload.get("nextPageToken") or "")
            if not page_token or len(people) >= 2000:
                break
    created = updated = skipped = 0
    skipped_reasons: list[str] = []
    for person in people[:2000]:
        try:
            raw = _google_contact(person)
            if not raw["display_name"]:
                raise ValueError("missing display name")
            exact = next((item for item in _list_contacts(raw["display_name"], True).get("contacts", []) if str(item.get("display_name") or "").casefold() == raw["display_name"].casefold()), None)
            if exact:
                for key in ("given_name", "family_name", "company_name", "job_title", "birthday", "relationship", "address", "website", "notes"):
                    if not raw.get(key):
                        raw[key] = exact.get(key) or ""
                if raw.get("birth_year") is None:
                    raw["birth_year"] = exact.get("birth_year")
                raw["phone_numbers"] = list(dict.fromkeys([*(exact.get("phone_numbers") or []), *raw["phone_numbers"]]))
                raw["emails"] = list(dict.fromkeys([*(exact.get("emails") or []), *raw["emails"]]))
                raw["bank_accounts"] = exact.get("bank_accounts") or []
                _update_contact(exact["id"], ContactUpdateRequest(**raw), source="google_contacts")
                updated += 1
            else:
                _create_contact(ContactRequest(**raw), source="google_contacts")
                created += 1
        except (HTTPException, TypeError, ValueError) as exc:
            skipped += 1
            reason = str(exc).replace("\n", " ")[:180]
            if reason and reason not in skipped_reasons and len(skipped_reasons) < 3:
                skipped_reasons.append(reason)
            LOGGER.warning("Skipped invalid Google contact during import: %s", reason)
    return {"imported": created + updated, "created": created, "updated": updated, "skipped": skipped, "skipped_reasons": skipped_reasons}
