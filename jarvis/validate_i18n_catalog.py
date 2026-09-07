#!/usr/bin/env python3
"""Validate ZBRANO's checked-in browser localization catalogs."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "app" / "static"
BASE = STATIC / "js" / "i18n.js"
ADVANCED = STATIC / "js" / "i18n" / "catalog-advanced.js"
HTML = STATIC / "index.html"
LOCALES = ("el", "it", "fr")
MINIMUM_PHRASES = 430
REQUIRED_PHRASES = {
    "About ZBRANO",
    "Automation Studio",
    "Birthdays",
    "Calendar reminders",
    "Choose device access",
    "Contacts",
    "Developer",
    "Entities",
    "Everything works as one assistant",
    "Interface language",
    "My Automations",
    "Notification Center",
    "Plugins",
    "Rooms & Learning",
    "Run required checks",
    "Save automation",
    "Settings",
    "Setup & safety",
    "Suggestion Inbox",
    "Visual automations",
}


def object_literal(source: str, pattern: str, label: str) -> dict[str, list[str]]:
    match = re.search(pattern, source, re.DOTALL | re.MULTILINE)
    if not match:
        raise RuntimeError(f"Could not locate {label} localization object")
    value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} localization catalog must be an object")
    return value


def main() -> None:
    base_source = BASE.read_text(encoding="utf-8")
    advanced_source = ADVANCED.read_text(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    base = object_literal(base_source, r"const rows = (\{.*?^  \});", "base")
    advanced = object_literal(advanced_source, r"register\((\{.*?^\})\);", "advanced")
    duplicates = sorted(set(base) & set(advanced))
    if duplicates:
        raise RuntimeError(f"Duplicate localization phrases: {', '.join(duplicates)}")
    catalog = {**base, **advanced}
    if len(catalog) < MINIMUM_PHRASES:
        raise RuntimeError(f"Localization coverage fell to {len(catalog)} phrases; expected at least {MINIMUM_PHRASES}")
    missing = sorted(REQUIRED_PHRASES - set(catalog))
    if missing:
        raise RuntimeError(f"Required localized interface phrases are missing: {', '.join(missing)}")
    for english, translations in catalog.items():
        if not isinstance(translations, list) or len(translations) != len(LOCALES):
            raise RuntimeError(f"{english!r} must contain Greek, Italian, and French")
        if any(not isinstance(value, str) or not value.strip() for value in translations):
            raise RuntimeError(f"{english!r} has an empty translation")
    if html.index('src="js/i18n.js"') > html.index('src="js/i18n/catalog-advanced.js"'):
        raise RuntimeError("The base localization runtime must load before the advanced catalog")
    if html.index('src="js/i18n/catalog-advanced.js"') > html.index('src="js/about.js"'):
        raise RuntimeError("Localization catalogs must load before dynamic feature panels")
    for marker in (
        "#messages",
        "#chat-list",
        "#entity-rows",
        "[data-i18n-ignore]",
        'record.type === "attributes"',
        'attributeFilter: ["aria-label", "title", "placeholder"]',
    ):
        if marker not in base_source:
            raise RuntimeError(f"Localization runtime safety marker is missing: {marker}")
    print(f"Localization catalog validated ({len(catalog)} phrases; en, el, it, fr)")


if __name__ == "__main__":
    main()
