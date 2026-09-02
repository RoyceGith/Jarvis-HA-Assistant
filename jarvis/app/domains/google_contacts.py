from __future__ import annotations

import contextlib
import hashlib
from typing import Any, Callable

import httpx

from ..schemas import ContactRequest, ContactUpdateRequest


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
    month, day = int(birthday_date.get("month") or 0), int(birthday_date.get("day") or 0)
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
        "birth_year": int(birthday_date["year"]) if birthday_date.get("year") else None,
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
                raise RuntimeError(detail or f"Google People API returned HTTP {response.status_code}")
            payload = response.json()
            people.extend(item for item in payload.get("connections") or [] if isinstance(item, dict))
            page_token = str(payload.get("nextPageToken") or "")
            if not page_token or len(people) >= 2000:
                break
    created = updated = skipped = 0
    for person in people[:2000]:
        raw = _google_contact(person)
        if not raw["display_name"]:
            skipped += 1
            continue
        exact = next((item for item in _list_contacts(raw["display_name"], True).get("contacts", []) if str(item.get("display_name") or "").casefold() == raw["display_name"].casefold()), None)
        if exact:
            preserved_accounts = exact.get("bank_accounts") or []
            raw["bank_accounts"] = preserved_accounts
            _update_contact(exact["id"], ContactUpdateRequest(**raw), source="google_contacts")
            updated += 1
        else:
            _create_contact(ContactRequest(**raw), source="google_contacts")
            created += 1
    return {"imported": created + updated, "created": created, "updated": updated, "skipped": skipped}
